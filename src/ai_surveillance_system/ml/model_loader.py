import torch
import torch.nn as nn
import torch.nn.functional as F
import pathlib as Path
from threading import Lock
from typing import Optional

from torchvision import models

from ai_surveillance_system.core.config import get_settings
from ai_surveillance_system.core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Index 0 -> Violence, Index 1 -> NonViolence
EXPECTED_CLASS_NAMES: list[str] = ["Violence", "NonViolence"]

# Model Architecture
class TemporalAttention(nn.Module):
    """
    Bahdanau-style additive attention over BiLSTM outputs.

    Input : (B, T, hidden_dim)
    Output: (B, hidden_dim)  — context vector
    """

    def __init__(self, hidden_dim: int) -> None:
        super().__init__()
        self.attn = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.Tanh(),
            nn.Linear(hidden_dim // 2, 1, bias=False),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        scores = self.attn(x).squeeze(-1)                            # (B, T)
        weights = F.softmax(scores, dim=-1)                           # (B, T)
        context = torch.bmm(weights.unsqueeze(1), x).squeeze(1)      # (B, H)
        return context


class ViolenceDetector(nn.Module):
    """
    ResNet50 (per-frame CNN) → BiLSTM → Temporal Attention → FC classifier.

    Input : (B, T, 3, H, W)   ← time dim is axis 1
    Output: (B, num_classes)
    """

    LSTM_HIDDEN: int = 256
    LSTM_LAYERS: int = 2
    DROPOUT: float = 0.4

    def __init__(self, num_classes: int = 2) -> None:
        super().__init__()

        backbone = models.resnet50(weights=None)

        # Drop FC head; keep through AdaptiveAvgPool → (B*T, 2048, 1, 1)
        self.cnn = nn.Sequential(
            backbone.conv1, backbone.bn1, backbone.relu, backbone.maxpool,
            backbone.layer1, backbone.layer2, backbone.layer3, backbone.layer4,
            backbone.avgpool,
        )
        cnn_out_dim = 2048

        self.bn_cnn = nn.BatchNorm1d(cnn_out_dim)
        self.drop_cnn = nn.Dropout(self.DROPOUT)

        self.bilstm = nn.LSTM(
            input_size=cnn_out_dim,
            hidden_size=self.LSTM_HIDDEN,
            num_layers=self.LSTM_LAYERS,
            batch_first=True,
            bidirectional=True,
            dropout=self.DROPOUT if self.LSTM_LAYERS > 1 else 0.0,
        )
        lstm_out_dim = self.LSTM_HIDDEN * 2   # 512

        self.attention = TemporalAttention(lstm_out_dim)

        self.classifier = nn.Sequential(
            nn.Linear(lstm_out_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(self.DROPOUT),

            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.Dropout(self.DROPOUT),

            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C, H, W = x.shape

        x_flat = x.view(B * T, C, H, W)
        feats = self.cnn(x_flat)           # (B*T, 2048, 1, 1)
        feats = feats.view(B * T, -1)      # (B*T, 2048)
        feats = self.bn_cnn(feats)
        feats = self.drop_cnn(feats)
        feats = feats.view(B, T, -1)       # (B, T, 2048)

        lstm_out, _ = self.bilstm(feats)    # (B, T, 512)
        context = self.attention(lstm_out)   # (B, 512)
        return self.classifier(context)     # (B, num_classes)


# Singleton loader
class ModelLoader:
    """
    Thread-safe singleton.  Loads ViolenceDetector weights exactly once.
    """

    _instance: Optional["ModelLoader"] = None
    _lock:     Lock = Lock()

    def __new__(cls) -> "ModelLoader":
        # Lock only protects instance creation
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._model = None
                inst._device = None
                cls._instance = inst
        return cls._instance

    @property
    def device(self) -> torch.device:
        if self._device is None:
            self._device = torch.device(
                "cuda" if torch.cuda.is_available() else "cpu"
            )
        return self._device

    def load(self) -> nn.Module:
        """
        Load weights and put the model in eval mode.
        """
        with self._lock:                     
            if self._model is not None:
                return self._model

            model = ViolenceDetector(num_classes=len(EXPECTED_CLASS_NAMES))
            model_path = Path(settings.MODEL_PATH)

            if model_path.exists():
                try:
                    checkpoint = torch.load(
                        model_path,
                        map_location=self.device,
                        weights_only=False,
                    )

                    # Detect checkpoint format
                    if isinstance(checkpoint, dict) and "model_state" in checkpoint:
                        state_dict = checkpoint["model_state"]
                        epoch = checkpoint.get("epoch",   "?")
                        val_acc = checkpoint.get("val_acc", "?")

                        # validate class order if stored in checkpoint
                        stored_names = checkpoint.get("class_names")
                        if stored_names is not None:
                            self._validate_class_names(stored_names)
                        else:
                            logger.warning(
                                "Checkpoint does not contain 'class_names'. "
                                "Assuming order matches EXPECTED_CLASS_NAMES: "
                                f"{EXPECTED_CLASS_NAMES}. "
                                "Re-export the checkpoint with class_names to "
                                "eliminate this assumption."
                            )

                        logger.info(
                            f"Checkpoint loaded — epoch={epoch}, "
                            f"val_acc={val_acc}"
                        )
                    else:
                        # Raw state_dict (exported with torch.save(model.state_dict(), ...))
                        state_dict = checkpoint
                        logger.warning(
                            "Raw state_dict loaded — no class_names embedded. "
                            f"Assuming label order {EXPECTED_CLASS_NAMES}."
                        )

                    model.load_state_dict(state_dict)
                    logger.info(
                        f"Weights loaded from {model_path} on {self.device}"
                    )

                except ValueError:
                    # Re-raise class-name validation errors immediately 
                    raise
                except Exception as exc:
                    logger.error(
                        f"Failed to load weights from {model_path}: {exc}. "
                        "Running with random weights — predictions meaningless."
                    )
            else:
                logger.warning(
                    f"Model weights not found at {model_path}. "
                    "Set MODEL_PATH in .env to point at "
                    "violence_detector_weights.pt or best_model.pt."
                )

            model.to(self.device)
            model.eval()  # BatchNorm uses running stats, Dropout disabled
            self._model = model
            return self._model

    def get_model(self) -> nn.Module:
        """Return cached model; raises if load() was never called."""
        if self._model is None:
            raise RuntimeError(
                "Model not loaded. Call model_loader.load() during app startup "
            )
        return self._model

    @staticmethod
    def _validate_class_names(stored: list[str]) -> None:
        """
        Raise ValueError if checkpoint class order differs from what
        inference.py and postprocessing.py expect.
        """
        if list(stored) != EXPECTED_CLASS_NAMES:
            raise ValueError(
                f"Checkpoint class_names {stored} do not match "
                f"expected {EXPECTED_CLASS_NAMES}. "
            )
        logger.info(f"Class names validated: {stored}")


# Module-level singleton
model_loader = ModelLoader()

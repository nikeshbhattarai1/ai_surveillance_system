from __future__ import annotations

import torch
import torch.nn.functional as F
from dataclasses import dataclass, field

from ai_surveillance_system.ml.model_loader import model_loader
from ai_surveillance_system.core.logger import get_logger

logger = get_logger(__name__)


CLASS_LABELS: dict[int, str] = {
    0: "violence",
    1: "nonviolence",
}

# Indices that represent an actionable threat
THREAT_INDICES: frozenset[int] = frozenset({0})   # "violence" only


# Result dataclass
@dataclass
class InferenceResult:
    predicted_class: int
    label: str
    confidence: float  # probability of predicted class
    all_probabilities: dict[str, float]  # full softmax distribution
    is_threat: bool
    frame_indices: list[int] = field(default_factory=list)
    # frame_indices lets postprocessing know which frames to save as evidence


# Single-clip inference
def run_inference(
    clip_tensor: torch.Tensor,
    frame_indices: list[int] | None = None,
) -> InferenceResult:
    """
    Single forward pass.

    Args:
        clip_tensor:   Shape (1, T, 3, H, W).
                       T must equal SEQUENCE_LENGTH (32).
                       Produced by preprocessing.frames_to_tensor() or
                       StreamFrameBuffer.push().
        frame_indices: Optional list of original frame numbers in this clip,
                       forwarded to InferenceResult for evidence saving.

    Returns:
        InferenceResult with label, confidence, probabilities, is_threat.
    """
    if clip_tensor.ndim != 5:
        raise ValueError(
            f"clip_tensor must be 5-D (B, T, C, H, W), got shape "
            f"{tuple(clip_tensor.shape)}"
        )

    model = model_loader.get_model()
    device = model_loader.device

    clip_tensor = clip_tensor.to(device)

    with torch.no_grad():
        logits = model(clip_tensor)  # (1, num_classes)
        probabilities = F.softmax(logits, dim=-1)  # (1, num_classes)
        confidence, predicted_idx = probabilities.max(dim=-1)

    predicted_idx = predicted_idx.item()
    confidence_val = confidence.item()
    label = CLASS_LABELS.get(predicted_idx, "unknown")

    all_probs = {
        CLASS_LABELS.get(i, f"class_{i}"): probabilities[0, i].item()
        for i in range(probabilities.shape[-1])
    }

    result = InferenceResult(
        predicted_class=predicted_idx,
        label=label,
        confidence=confidence_val,
        all_probabilities=all_probs,
        is_threat=predicted_idx in THREAT_INDICES,
        frame_indices=frame_indices or [],
    )

    logger.debug(
        f"Inference → {label} ({confidence_val:.3f}) | "
        f"all_probs={all_probs}"
    )
    return result


# Batched inference
def run_batch_inference(
    clip_tensors: list[torch.Tensor],
    frame_indices_list: list[list[int]] | None = None,
) -> list[InferenceResult]:
    """
    Batched forward pass over multiple (1, T, 3, H, W) clips.

    Concatenates along batch dim → (N, T, 3, H, W) for a single GPU
    forward pass which is more efficient than N separate calls.

    Args:
        clip_tensors:       List of (1, T, 3, H, W) tensors from
                            preprocessing.extract_clips().
        frame_indices_list: Optional parallel list of frame-index lists,
                            one per clip.  Forwarded to InferenceResult.

    Returns:
        List of InferenceResult, one per input clip, in the same order.
    """
    if not clip_tensors:
        return []

    model = model_loader.get_model()
    device = model_loader.device

    # (N, 1, T, 3, H, W) → squeeze → (N, T, 3, H, W)
    batch = torch.cat(clip_tensors, dim=0).to(device)  # (N, T, 3, H, W)

    with torch.no_grad():
        logits = model(batch)  # (N, num_classes)
        probabilities = F.softmax(logits, dim=-1)  # (N, num_classes)

    results: list[InferenceResult] = []

    for i in range(probabilities.shape[0]):
        confidence, predicted_idx = probabilities[i].max(dim=-1)
        predicted_idx = predicted_idx.item()
        label = CLASS_LABELS.get(predicted_idx, "unknown")

        all_probs = {
            CLASS_LABELS.get(j, f"class_{j}"): probabilities[i, j].item()
            for j in range(probabilities.shape[-1])
        }

        indices = (
            frame_indices_list[i]
            if frame_indices_list and i < len(frame_indices_list)
            else []
        )

        results.append(InferenceResult(
            predicted_class=predicted_idx,
            label=label,
            confidence=confidence.item(),
            all_probabilities=all_probs,
            is_threat=predicted_idx in THREAT_INDICES,
            frame_indices=indices,
        ))

    logger.debug(
        f"Batch inference: {len(results)} clips | "
        f"threats={sum(r.is_threat for r in results)}"
    )
    return results

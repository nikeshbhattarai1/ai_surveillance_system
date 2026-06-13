from __future__ import annotations

import cv2
import numpy as np
import torch
from collections import deque
from pathlib import Path
from typing import Generator, Optional

from ai_surveillance_system.core.logger import get_logger

logger = get_logger(__name__)

# Constants
IMAGE_HEIGHT = 224
IMAGE_WIDTH = 224
SEQUENCE_LENGTH = 32 # frames per clip

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# Per-frame preprocessing
def preprocess_frame(frame_bgr: np.ndarray) -> np.ndarray:
    """
    Mirrors ViolenceDataset.__getitem__() from training exactly:
      1. BGR → RGB
      2. Resize to IMAGE_WIDTH × IMAGE_HEIGHT
      3. float32 [0, 1]
      4. ImageNet mean/std normalisation

    Returns:
        Normalised float32 array of shape (H, W, 3).
    """
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    frame_resized = cv2.resize(
        frame_rgb,
        (IMAGE_WIDTH, IMAGE_HEIGHT),
        interpolation=cv2.INTER_LINEAR,
    )
    frame_float = frame_resized.astype(np.float32) / 255.0
    return (frame_float - IMAGENET_MEAN) / IMAGENET_STD   # (H, W, 3)

# Tensor construction
def frames_to_tensor(frames: list[np.ndarray]) -> torch.Tensor:
    """
    Convert a list of (H, W, 3) float32 normalised frames to a batched
    clip tensor for ViolenceDetector.

    Dimension order: (N, T, C, H, W) — axis 1 is time.

    Args:
        frames: exactly SEQUENCE_LENGTH items, each (H, W, 3) float32.

    Returns:
        Tensor of shape (1, T, 3, H, W).
    """
    clip_array = np.stack(frames, axis=0) # (T, H, W, 3)
    tensor = torch.from_numpy(clip_array).float() # (T, H, W, 3)
    tensor = tensor.permute(0, 3, 1, 2)  # (T, 3, H, W)
    return tensor.unsqueeze(0)  # (1, T, 3, H, W)


# Video file clip extraction
def extract_clips(
    video_path: str | Path,
    sequence_length: int = SEQUENCE_LENGTH,
    overlap: float = 0.5,
) -> Generator[tuple[torch.Tensor, list[int]], None, None]:
    """
    Yield (clip_tensor, frame_indices) for every sliding window in a video.

    Matches training's extract_frames() logic:
      - Reads exactly `sequence_length` contiguous frames per clip.
      - Slides the window by (1 - overlap) × sequence_length frames.
      - Skips the video entirely if it has fewer than sequence_length frames.

    Args:
        video_path: Path to the video file.
        sequence_length: Number of frames per clip.
        overlap: Fractional overlap between consecutive windows
                         (0.0 = no overlap, 0.5 = half-window step).

    Yields:
        clip_tensor   : shape (1, T, 3, H, W) — ready for run_inference().
        frame_indices : list of original frame numbers included in this clip.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    logger.info(
        f"Video: {Path(video_path).name} | "
        f"frames={total_frames} | fps={fps:.1f}"
    )

    if total_frames < sequence_length:
        cap.release()
        logger.warning(
            f"Video too short ({total_frames} < {sequence_length} frames): "
            f"{video_path}"
        )
        return

    step = max(1, int(sequence_length * (1.0 - overlap)))
    start_idx = 0

    try:
        while start_idx + sequence_length <= total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_idx)
            frames:  list[np.ndarray] = []
            indices: list[int] = []

            for offset in range(sequence_length):
                ok, frame = cap.read()
                if not ok or frame is None:
                    logger.debug(
                        f"Frame read failed at offset "
                        f"{start_idx + offset} in {video_path}"
                    )
                    break
                try:
                    frames.append(preprocess_frame(frame))
                    indices.append(start_idx + offset)
                except Exception as exc:
                    logger.warning(
                        f"Frame decode error at {start_idx + offset}: {exc}"
                    )
                    break

            if len(frames) == sequence_length:
                yield frames_to_tensor(frames), indices

            start_idx += step
    finally:
        cap.release()

# Rolling buffer for WebSocket streaming
class StreamFrameBuffer:
    """
    Accumulates preprocessed frames from a live WebSocket stream and
    yields a clip tensor once SEQUENCE_LENGTH frames are buffered.
    """

    def __init__(
        self,
        sequence_length: int = SEQUENCE_LENGTH,
        overlap: float = 0.5,
    ) -> None:
        self.sequence_length = sequence_length
        self.step = max(1, int(sequence_length * (1.0 - overlap)))
        self._buffer: deque[np.ndarray] = deque(maxlen=sequence_length)
        self._frames_since_last_inference = 0
        self._total_frames_pushed = 0

    def push(
        self,
        frame_bgr: np.ndarray,
    ) -> tuple[Optional[torch.Tensor], Optional[list[int]]]:
        """
        Preprocess one BGR frame and add it to the rolling buffer.
        """
        processed = preprocess_frame(frame_bgr)
        self._buffer.append(processed)
        self._total_frames_pushed += 1
        self._frames_since_last_inference += 1

        # Fire inference when buffer is full and step frames have arrived
        if (
            len(self._buffer) == self.sequence_length
            and self._frames_since_last_inference >= self.step
        ):
            start = self._total_frames_pushed - self.sequence_length
            indices = list(range(start, self._total_frames_pushed))

            clip = frames_to_tensor(list(self._buffer))
            self._frames_since_last_inference = 0
            return clip, indices

        return None, None

    def push_bytes(
        self,
        frame_bytes: bytes,
    ) -> tuple[Optional[torch.Tensor], Optional[list[int]], Optional[np.ndarray]]:
        """
        Decode a JPEG/PNG frame from raw bytes, push to buffer.
        """
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame_bgr is None:
            raise ValueError(
                "Failed to decode frame bytes — invalid or corrupt image data."
            )

        clip, indices = self.push(frame_bgr)
        raw = frame_bgr if clip is not None else None
        return clip, indices, raw

    @property
    def buffered(self) -> int:
        """Current number of frames in the buffer."""
        return len(self._buffer)

    def reset(self) -> None:
        """Clear the buffer (e.g. when a client disconnects)."""
        self._buffer.clear()
        self._frames_since_last_inference = 0
        self._total_frames_pushed = 0

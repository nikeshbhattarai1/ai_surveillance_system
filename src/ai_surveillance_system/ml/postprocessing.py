from __future__ import annotations

import cv2
import uuid
import numpy as np
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ai_surveillance_system.ml.inference import InferenceResult
from ai_surveillance_system.core.config import get_settings
from ai_surveillance_system.core.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# DB EventType string values
LABEL_TO_EVENT_TYPE: dict[str, str] = {
    "violence": "violence",
    "normal":   "normal",
    # Add "fire": "fire" etc. when the model is extended
}

# Result dataclass
@dataclass
class ProcessedDetection:
    label: str
    confidence: float
    is_threat: bool
    event_type: str  # maps to DB EventType
    frame_paths: list[str] = field(default_factory=list)
    frame_number: Optional[int] = None  # first frame of the clip
    all_probabilities: dict[str, float] = field(default_factory=dict)


# Evidence frame saving
def save_evidence_frames(
    frames_bgr: list[np.ndarray],
    label: str,
    confidence: float,
    job_id: Optional[str] = None,
) -> list[str]:
    """
    Save up to three annotated frames from a threat clip:
      - frames_bgr[0] → first frame
      - frames_bgr[len // 2] → middle frame (most likely to show peak)
      - frames_bgr[-1]  → last frame

    Saving three frames gives forensic reviewers temporal context to
    confirm whether the detected event is genuine, replacing the previous
    approach of saving one unpredictable frame.

    Args:
        frames_bgr: Raw BGR frames from the clip (any length ≥ 1).
        label: Predicted class label, e.g. "violence".
        confidence: Model confidence for the overlay text.
        job_id: Optional job UUID used to prefix filenames.

    Returns:
        List of saved file paths (1–3 items).
    """
    frames_dir = Path(settings.FRAMES_DIR)
    frames_dir.mkdir(parents=True, exist_ok=True)

    n = len(frames_bgr)
    # Select first / middle / last without duplicates
    indices = sorted({0, n // 2, n - 1})
    positions = {0: "first", n // 2: "mid", n - 1: "last"}

    saved_paths: list[str] = []
    overlay_text = f"{label.upper()}  {confidence:.0%}"

    for idx in indices:
        frame = frames_bgr[idx].copy()
        pos_name = positions.get(idx, str(idx))

        # Draw a filled rectangle behind the text for readability
        (text_w, text_h), _ = cv2.getTextSize(
            overlay_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2
        )
        cv2.rectangle(frame, (8, 8), (text_w + 20,
                      text_h + 20), (0, 0, 180), -1)
        cv2.putText(
            frame, overlay_text, (14, text_h + 12),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA,
        )

        uid = str(uuid.uuid4())[:8]
        prefix = job_id or "stream"
        filename = f"{prefix}_{label}_{pos_name}_{uid}.jpg"
        path = frames_dir / filename

        success = cv2.imwrite(
            str(path),
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, 85]
        )

        if success:
            saved_paths.append(str(path))
            logger.debug(f"Evidence frame saved: {path}")
        else:
            logger.warning(f"Failed to save frame: {path}")

    return saved_paths

# Per-clip postprocessing
def postprocess(
    inference_result: InferenceResult,
    raw_frames: Optional[list[np.ndarray]] = None,
    frame_number: Optional[int] = None,
    job_id: Optional[str] = None,
    confidence_threshold: Optional[float] = None,
) -> ProcessedDetection:
    """
    Gate the inference result against the confidence threshold and
    (if threat confirmed) save evidence frames.

    Args:
        inference_result: Output of run_inference() or run_batch_inference().
        raw_frames: Raw BGR frames for the clip — passed to
                    save_evidence_frames() when a threat is confirmed.
                    If None, no frames are saved.
        frame_number: Index of the first frame in this clip.
        job_id: Video job UUID (None for live stream events).
        confidence_threshold: Override settings.CONFIDENCE_THRESHOLD.

    Returns:
        ProcessedDetection ready for persistence in detection_service.
    """
    threshold = (
        confidence_threshold
        if confidence_threshold is not None
        else settings.CONFIDENCE_THRESHOLD
    )

    is_confirmed_threat = (
        inference_result.is_threat
        and inference_result.confidence >= threshold
    )

    frame_paths: list[str] = []
    if is_confirmed_threat and raw_frames:
        try:
            frame_paths = save_evidence_frames(
                raw_frames,
                inference_result.label,
                inference_result.confidence,
                job_id=job_id,
            )
        except Exception as exc:
            logger.error(f"Failed to save evidence frames: {exc}")

    event_type = (
        LABEL_TO_EVENT_TYPE.get(inference_result.label, "unknown")
        if is_confirmed_threat
        else "normal"
    )

    return ProcessedDetection(
        label=inference_result.label,
        confidence=inference_result.confidence,
        is_threat=is_confirmed_threat,
        event_type=event_type,
        frame_paths=frame_paths,
        frame_number=frame_number,
        all_probabilities=inference_result.all_probabilities,
    )


# Multi-clip aggregation
def aggregate_clip_results(
    detections: list[ProcessedDetection],
    min_threat_clips: int = 1,
) -> ProcessedDetection:
    """
    Reduce a list of per-clip ProcessedDetections to a single verdict.

    Args:
        detections: List of ProcessedDetection from postprocess().
        min_threat_clips: Minimum number of threat clips required to
                          declare the segment a confirmed threat.

    Returns:
        Single ProcessedDetection — either the highest-confidence threat
        or a "normal / clear" result.

    Raises:
        ValueError: if detections is empty.
    """
    if not detections:
        raise ValueError("Cannot aggregate an empty detections list.")

    threat_detections = [d for d in detections if d.is_threat]
    threat_count = len(threat_detections)
    total = len(detections)

    if threat_count >= min_threat_clips:
        # Return the clip with the highest model confidence as representative
        best = max(threat_detections, key=lambda d: d.confidence)
        logger.info(
            f"Aggregated {total} clips → THREAT confirmed | "
            f"{threat_count}/{total} clips triggered | "
            f"best confidence={best.confidence:.3f} "
            f"ml_label={best.label} event_type={best.event_type}"
        )
        return best

    # No threat confirmed
    max_conf = max(d.confidence for d in detections)
    logger.info(
        f"Aggregated {total} clips → CLEAR | "
        f"{threat_count}/{total} clips triggered (< min={min_threat_clips}) | "
        f"max confidence seen={max_conf:.3f}"
    )
    return ProcessedDetection(
        label="normal",
        confidence=max_conf,
        is_threat=False,
        event_type=LABEL_TO_EVENT_TYPE["normal"],
        frame_paths=[],
        frame_number=None,
        all_probabilities={},
    )

"""Utilities for running medical image inference and persisting results."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.inference.inference import HeatmapGenerator
from app.db import InferencePrediction, InferenceRequest

CLASS_NAMES = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Effusion",
    "Emphysema",
    "Fibrosis",
    "Hernia",
    "Infiltration",
    "Mass",
    "Nodule",
    "Pleural_Thickening",
    "Pneumonia",
    "Pneumothorax",
]

MODEL_PATH = (
    Path(__file__).resolve().parents[1] / "ai" / "models" / "best_auc_weights_only.pth"
)
AI_IMAGE_UPLOAD_DIR = Path(__file__).resolve().parents[1] / "ai" / "upload"
AI_IMAGE_UPLOAD_ROOT = AI_IMAGE_UPLOAD_DIR.resolve()
PROCESSED_IMAGE_DIR = AI_IMAGE_UPLOAD_DIR / "processed"

_heatmap_generator: HeatmapGenerator | None = None
_heatmap_generator_lock = asyncio.Lock()


async def _get_heatmap_generator() -> HeatmapGenerator:
    global _heatmap_generator

    if _heatmap_generator is not None:
        return _heatmap_generator

    async with _heatmap_generator_lock:
        if _heatmap_generator is None:
            _heatmap_generator = await asyncio.to_thread(
                HeatmapGenerator,
                str(MODEL_PATH),
                14,
                224,
            )
    return _heatmap_generator


def _resolve_upload_path(path_value: str | Path) -> Path:
    candidate = Path(path_value).expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (AI_IMAGE_UPLOAD_DIR / candidate).resolve()
    resolved.relative_to(AI_IMAGE_UPLOAD_ROOT)
    return resolved


def _relative_upload_path(path_value: str | Path) -> str:
    return _resolve_upload_path(path_value).relative_to(AI_IMAGE_UPLOAD_ROOT).as_posix()


def _build_image_url(relative_path: str) -> str:
    return f"/api/v1/images/{relative_path}"


def _save_image(array: Any, destination: Path) -> str | None:
    if array is None:
        return None

    image_array = np.asarray(array)
    if image_array.size == 0:
        return None

    destination_path = _resolve_upload_path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image_array).save(destination_path)
    return _relative_upload_path(destination_path)


def _format_prediction_summary(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    positive_labels = [
        item["label_name"] for item in predictions if item.get("is_positive")
    ]
    top_predictions = sorted(
        predictions,
        key=lambda item: float(item.get("probability", 0.0)),
        reverse=True,
    )[:3]

    return {
        "positive_labels": positive_labels,
        "top_predictions": top_predictions,
    }


async def run_image_inference(
    session: AsyncSession,
    user_id: UUID,
    image_payloads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not image_payloads:
        return []

    generator = await _get_heatmap_generator()
    inference_results: list[dict[str, Any]] = []

    for index, payload in enumerate(image_payloads, start=1):
        image_path = _resolve_upload_path(payload["image_path"])
        threshold = float(payload.get("threshold", 0.5))
        filename = payload.get("filename") or image_path.name
        relative_image_path = _relative_upload_path(image_path)

        start_time = time.perf_counter()
        probs = await asyncio.to_thread(generator.predict, str(image_path))
        heatmap_img, bbox_img, crop_img = await asyncio.to_thread(
            generator.generate,
            str(image_path),
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        request = InferenceRequest(
            user_id=user_id,
            image_path=relative_image_path,
            model_name="HeatmapGenerator",
            model_version="swin_t_14class",
            inference_time_ms=elapsed_ms,
        )
        session.add(request)
        await session.flush()

        predictions: list[dict[str, Any]] = []
        for label_name, probability in zip(CLASS_NAMES, probs, strict=False):
            probability_value = float(probability)
            is_positive = probability_value >= threshold
            prediction = InferencePrediction(
                request_id=request.id,
                label_name=label_name,
                probability=probability_value,
                threshold_used=threshold,
                is_positive=is_positive,
            )
            session.add(prediction)
            predictions.append(
                {
                    "label_name": label_name,
                    "probability": probability_value,
                    "threshold_used": threshold,
                    "is_positive": is_positive,
                }
            )

        base_name = f"{request.id}_{index}"
        heatmap_path = _save_image(
            heatmap_img,
            PROCESSED_IMAGE_DIR / f"{base_name}_heatmap.png",
        )
        bbox_path = _save_image(
            bbox_img,
            PROCESSED_IMAGE_DIR / f"{base_name}_bbox.png",
        )
        crop_path = _save_image(
            crop_img if crop_img is not None else bbox_img,
            PROCESSED_IMAGE_DIR / f"{base_name}_crop.png",
        )

        inference_results.append(
            {
                "request_id": str(request.id),
                "image_path": relative_image_path,
                "image_url": _build_image_url(relative_image_path),
                "filename": filename,
                "threshold": threshold,
                "inference_time_ms": elapsed_ms,
                "predictions": predictions,
                "heatmap_path": heatmap_path,
                "bbox_path": bbox_path,
                "crop_path": crop_path,
                "heatmap_url": _build_image_url(heatmap_path) if heatmap_path else None,
                "bbox_url": _build_image_url(bbox_path) if bbox_path else None,
                "crop_url": _build_image_url(crop_path) if crop_path else None,
                **_format_prediction_summary(predictions),
            }
        )

    return inference_results

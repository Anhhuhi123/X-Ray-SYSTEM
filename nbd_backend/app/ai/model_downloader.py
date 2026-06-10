"""Download AI model weights from HuggingFace Hub on first startup."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_HF_REPO_ID = "Anh101/Swin_Tiny"
_HF_FILENAME = "best_auc_weights_only.pth"
_MODELS_DIR = Path(__file__).resolve().parent / "models"


def ensure_model_downloaded() -> Path:
    """Return local path to model weights, downloading from HuggingFace if absent.

    The file is saved to app/ai/models/best_auc_weights_only.pth so that the
    existing MODEL_PATH in image_inference_service.py requires no changes.
    """
    target = _MODELS_DIR / _HF_FILENAME

    if target.exists():
        logger.info("Model weights already present at %s — skipping download.", target)
        return target

    logger.info(
        "Model weights not found locally. Downloading %s/%s from HuggingFace…",
        _HF_REPO_ID,
        _HF_FILENAME,
    )

    try:
        from huggingface_hub import hf_hub_download

        _MODELS_DIR.mkdir(parents=True, exist_ok=True)

        hf_hub_download(
            repo_id=_HF_REPO_ID,
            filename=_HF_FILENAME,
            local_dir=str(_MODELS_DIR),
            token=os.environ.get("HF_TOKEN"),
        )

        if not target.exists():
            raise FileNotFoundError(
                f"hf_hub_download completed but {target} was not created."
            )

        logger.info("Model weights downloaded successfully to %s.", target)
        return target

    except Exception:
        logger.exception(
            "Failed to download model weights from HuggingFace (%s/%s). "
            "Inference will fail unless the file is provided manually at %s.",
            _HF_REPO_ID,
            _HF_FILENAME,
            target,
        )
        raise

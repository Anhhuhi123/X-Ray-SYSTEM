from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.db import InferencePrediction, InferenceRequest


@pytest.mark.integration
async def test_inference_request_and_predictions_persist(
    db_session, db_user
):
    request = InferenceRequest(
        id=uuid.uuid4(),
        user_id=db_user.id,
        image_path="/tmp/example-image.jpg",
        model_name="resnet50-multilabel",
        model_version="2026-05-12",
        inference_time_ms=42.5,
    )
    request.predictions.append(
        InferencePrediction(
            id=uuid.uuid4(),
            label_name="cat",
            probability=0.93,
            threshold_used=0.5,
            is_positive=True,
        )
    )

    db_session.add(request)
    await db_session.flush()

    result = await db_session.execute(
        select(InferenceRequest).where(InferenceRequest.id == request.id)
    )
    stored_request = result.scalar_one()

    assert stored_request.user_id == db_user.id
    assert stored_request.image_path == "/tmp/example-image.jpg"
    assert stored_request.predictions[0].label_name == "cat"
    assert stored_request.predictions[0].request_id == request.id
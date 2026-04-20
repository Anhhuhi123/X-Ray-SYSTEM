"""
Routes for public chat access via immutable snapshots.

All public endpoints use share_token for access - no authentication required
for read operations. Clone requires authentication.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import User, get_async_session
from app.schemas.new_chat import (
    CloneResponse,
    PublicChatResponse,
)
from app.services.public_chat_service import (
    clone_from_snapshot,
    get_public_chat,
    get_snapshot_report,
)
from app.users import current_active_user

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/{share_token}", response_model=PublicChatResponse)
async def read_public_chat(
    share_token: str,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get a public chat snapshot by share token.

    No authentication required.
    Returns immutable snapshot data (sanitized, citations stripped).
    """
    return await get_public_chat(session, share_token)


@router.post("/{share_token}/clone", response_model=CloneResponse)
async def clone_public_chat(
    share_token: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """
    Clone a public chat snapshot to the user's account.

    Creates thread and copies messages.
    Requires authentication.
    """
    return await clone_from_snapshot(session, share_token, user)


@router.get("/{share_token}/reports/{report_id}/content")
async def get_public_report_content(
    share_token: str,
    report_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get report content from a public chat snapshot.

    No authentication required - the share_token provides access.
    Returns report content including title, markdown body, metadata, and versions.
    """
    from app.services.public_chat_service import get_snapshot_report_versions

    report_info = await get_snapshot_report(session, share_token, report_id)

    if not report_info:
        raise HTTPException(status_code=404, detail="Report not found")

    # Get version siblings from the same snapshot
    versions = await get_snapshot_report_versions(
        session, share_token, report_info.get("report_group_id")
    )

    return {
        "id": report_info.get("original_id"),
        "title": report_info.get("title"),
        "content": report_info.get("content"),
        "report_metadata": report_info.get("report_metadata"),
        "report_group_id": report_info.get("report_group_id"),
        "versions": versions,
    }

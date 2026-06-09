import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import NewChatThread, User, get_async_session
from app.users import current_superuser

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(current_superuser)],
)

class OverviewStats(BaseModel):
    total_users: int
    today_users: int
    week_users: int
    total_requests: int
    today_requests: int
    week_requests: int
    total_conversations: int
    active_conversations: int
    avg_response_time: float
    success_rate: float
    error_rate: float
    input_tokens: int
    output_tokens: int
    total_tokens: int


@router.get("/overview", response_model=OverviewStats)
async def get_overview_stats(
    session: AsyncSession = Depends(get_async_session),
):
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # User stats
    total_users_result = await session.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar_one_or_none() or 0

    today_users = 0
    week_users = 0

    # Conversation stats
    total_convs_result = await session.execute(select(func.count(NewChatThread.id)))
    total_conversations = total_convs_result.scalar_one_or_none() or 0

    # Let's say "active" means updated in the last 24 hours
    active_convs_result = await session.execute(
        select(func.count(NewChatThread.id)).where(NewChatThread.updated_at >= today_start)
    )
    active_conversations = active_convs_result.scalar_one_or_none() or 0

    # Mocked data for requests and tokens
    return OverviewStats(
        total_users=total_users,
        today_users=today_users,
        week_users=week_users,
        total_requests=45231,
        today_requests=1250,
        week_requests=8430,
        total_conversations=total_conversations,
        active_conversations=active_conversations,
        avg_response_time=1.2,
        success_rate=98.5,
        error_rate=1.5,
        input_tokens=1500000,
        output_tokens=300000,
        total_tokens=1800000,
    )

class AdminUserItem(BaseModel):
    id: str
    email: str
    name: str | None
    status: str
    joined_date: datetime
    last_active: datetime | None
    total_conversations: int
    total_requests: int

class AdminUsersResponse(BaseModel):
    items: list[AdminUserItem]
    total: int
    page: int
    page_size: int

@router.get("/users", response_model=AdminUsersResponse)
async def get_admin_users(
    page: int = 1,
    page_size: int = 10,
    search: str | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    query = select(User)
    
    if search:
        query = query.where(User.email.ilike(f"%{search}%"))

    # Get total count
    total_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one_or_none() or 0

    # Get paginated users
    query = query.order_by(User.email.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    users = result.scalars().all()

    items = []
    for user in users:
        # Get conversation count for this user
        conv_result = await session.execute(
            select(func.count(NewChatThread.id)).where(NewChatThread.created_by_id == user.id)
        )
        conv_count = conv_result.scalar_one_or_none() or 0

        items.append(
            AdminUserItem(
                id=str(user.id),
                email=user.email,
                name=user.display_name,
                status="Active" if user.is_active else "Inactive",
                joined_date=datetime.now(UTC),  # User table has no created_at
                last_active=getattr(user, 'last_login', None),
                total_conversations=conv_count,
                total_requests=conv_count * 10, # Mocked
            )
        )

    return AdminUsersResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )

class TokenUsage(BaseModel):
    input: int
    output: int
    total: int

class AdminConversationItem(BaseModel):
    id: str
    messageId: str
    userId: str | None
    user: str | None
    timestamp: datetime
    question: str
    answerPreview: str
    model: str
    responseTime: str
    tokens: TokenUsage
    status: str
    fullAnswer: str | None

class AdminConversationsResponse(BaseModel):
    items: list[AdminConversationItem]
    total: int
    page: int
    page_size: int

@router.get("/conversations", response_model=AdminConversationsResponse)
async def get_admin_conversations(
    page: int = 1,
    page_size: int = 10,
    search: str | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    query = select(NewChatThread, User).outerjoin(User, NewChatThread.created_by_id == User.id)

    if search:
        query = query.where(NewChatThread.title.ilike(f"%{search}%"))

    # Get total count
    total_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one_or_none() or 0

    # Get paginated threads
    query = query.order_by(NewChatThread.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    threads_with_user = result.all()

    items = []
    for thread, user in threads_with_user:
        # Fetch real messages from the thread to make it accurate.
        from app.db import NewChatMessage
        messages_result = await session.execute(
            select(NewChatMessage)
            .where(NewChatMessage.thread_id == thread.id)
            .order_by(NewChatMessage.created_at.asc())
        )
        messages = messages_result.scalars().all()
        
        question = thread.title
        full_answer = "No response yet."
        msg_id = ""
        
        for msg in reversed(messages):
            if msg.role == "assistant":
                content = msg.content
                if isinstance(content, list) and len(content) > 0 and "text" in content[0]:
                    full_answer = content[0]["text"]
                elif isinstance(content, str):
                    full_answer = content
                else:
                    full_answer = str(content)
                msg_id = str(msg.id)
                break
        
        for msg in messages:
            if msg.role == "user":
                content = msg.content
                if isinstance(content, list) and len(content) > 0 and "text" in content[0]:
                    question = content[0]["text"]
                elif isinstance(content, str):
                    question = content
                break
                
        answer_preview = full_answer[:50] + "..." if len(full_answer) > 50 else full_answer

        items.append(
            AdminConversationItem(
                id=str(thread.id),
                messageId=msg_id or str(thread.id),
                userId=str(user.id) if user else None,
                user=user.display_name or user.email if user else "Unknown",
                timestamp=thread.created_at,
                question=question,
                answerPreview=answer_preview,
                model="Mocked Model",
                responseTime="1.0s",
                tokens=TokenUsage(input=10, output=20, total=30),
                status="Success" if messages else "Empty",
                fullAnswer=full_answer,
            )
        )

    return AdminConversationsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )



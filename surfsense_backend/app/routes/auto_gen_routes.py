import logging

from fastapi import APIRouter, HTTPException, status
from app.schemas.auto_gen import (
    DiscussionRequest,
    DiscussionResponse
)
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from app.config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/autogen", tags=["autogen"])


@router.post("/team/discussion", response_model=DiscussionResponse)
async def run_team_discussion(request: DiscussionRequest):
    try:
        # Create model client
        model_client = OpenAIChatCompletionClient(
            model="gemini-2.5-flash",
            api_key=config.GEMINI_API_KEY,
        )

        # Create agents
        primary_agent = AssistantAgent(
            "primary",
            model_client=model_client,
            system_message="You are a helpful AI assistant.",
        )

        critic_agent = AssistantAgent(
            "critic",
            model_client=model_client,
            system_message=(
                "Provide constructive feedback. "
                "Respond with 'APPROVE' when your feedback is addressed."
            ),
        )

        # Termination condition
        termination = TextMentionTermination("APPROVE")

        # Create team
        team = RoundRobinGroupChat(
            [primary_agent, critic_agent],
            termination_condition=termination
        )

        # Reset team
        await team.reset()

        # Run team (collect result instead of Console stream)
        result = await team.run(task=request.task)

        messages = [
            {
                "role": msg.source,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in result.messages
        ]

        logger.info("Team discussion completed")

        return DiscussionResponse(
            result={
                "conversation": messages,
                "stop_reason": result.stop_reason
            }
        )

    except Exception as e:
        logger.exception("Error running team discussion")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
from pydantic import BaseModel


# Request / Response schema
class DiscussionRequest(BaseModel):
    task: str


# class DiscussionResponse(BaseModel):
#     result: str


class Message(BaseModel):
    role: str
    content: str
    created_at: str | None


class DiscussionResult(BaseModel):
    conversation: list[Message]
    stop_reason: str | None


class DiscussionResponse(BaseModel):
    result: DiscussionResult

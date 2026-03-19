from pydantic import BaseModel
from typing import List, Optional

# Request / Response schema
class DiscussionRequest(BaseModel):
    task: str

# class DiscussionResponse(BaseModel):
#     result: str

class Message(BaseModel):
    role: str
    content: str
    created_at: Optional[str]

class DiscussionResult(BaseModel):
    conversation: List[Message]
    stop_reason: Optional[str]

class DiscussionResponse(BaseModel):
    result: DiscussionResult
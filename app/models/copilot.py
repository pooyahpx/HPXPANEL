from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CopilotRole = Literal["user", "assistant", "system"]


class CopilotMessage(BaseModel):
    role: CopilotRole
    content: str = Field(min_length=1, max_length=12000)


class CopilotChatRequest(BaseModel):
    messages: list[CopilotMessage] = Field(min_length=1, max_length=40)
    page_path: str | None = Field(default=None, max_length=512)


class CopilotChatResponse(BaseModel):
    reply: str
    actions_taken: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CopilotStatusResponse(BaseModel):
    enabled: bool
    configured: bool
    model: str

    model_config = ConfigDict(from_attributes=True)

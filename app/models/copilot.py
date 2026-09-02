from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CopilotRole = Literal["user", "assistant", "system"]
CopilotProvider = Literal["groq", "openai", "openrouter", "ollama"]


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
    provider: str
    model: str
    api_key_masked: str = ""

    model_config = ConfigDict(from_attributes=True)


class CopilotSettingsUpdate(BaseModel):
    enabled: bool | None = None
    provider: CopilotProvider | None = None
    api_key: str | None = Field(default=None, max_length=512)
    model: str | None = Field(default=None, max_length=128)
    base_url: str | None = Field(default=None, max_length=512)

    @field_validator("api_key", "model", "base_url", mode="before")
    @classmethod
    def strip_optional_strings(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class CopilotSettingsResponse(CopilotStatusResponse):
    saved: bool = True
    writable: bool = True

    model_config = ConfigDict(from_attributes=True)

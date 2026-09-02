from app.db import AsyncSession
from app.models.admin import AdminDetails
from app.models.copilot import (
    CopilotChatRequest,
    CopilotChatResponse,
    CopilotSettingsResponse,
    CopilotSettingsUpdate,
    CopilotStatusResponse,
)
from app.operation import BaseOperation
from app.services.copilot import run_copilot_chat
from app.services.copilot.llm import CopilotNotConfiguredError, CopilotProviderError
from app.services.copilot.settings_store import copilot_env_is_writable, masked_api_key, persist_copilot_settings
import config


class CopilotOperation(BaseOperation):
    def _status_response(self) -> CopilotStatusResponse:
        settings = config.copilot_settings
        return CopilotStatusResponse(
            enabled=settings.enabled,
            configured=settings.is_configured,
            provider=settings.provider,
            model=settings.model,
            api_key_masked=masked_api_key(),
        )

    async def get_status(self) -> CopilotStatusResponse:
        return self._status_response()

    async def update_settings(self, payload: CopilotSettingsUpdate) -> CopilotSettingsResponse:
        if not copilot_env_is_writable():
            await self.raise_error(
                message="Copilot settings path is not writable on this server",
                code=500,
            )

        effective_provider = (payload.provider or config.copilot_settings.provider).strip().lower()
        has_existing_key = bool(config.copilot_settings.api_key.strip())
        has_new_key = bool(payload.api_key and payload.api_key.strip())
        if effective_provider != "ollama" and not has_existing_key and not has_new_key:
            await self.raise_error(message="API key is required for this provider", code=400)

        try:
            persist_copilot_settings(
                enabled=payload.enabled,
                provider=payload.provider,
                api_key=payload.api_key,
                model=payload.model,
                base_url=payload.base_url,
            )
        except ValueError as exc:
            await self.raise_error(message=str(exc), code=400)

        from app.nats.message import MessageTopic
        from app.nats.router import router

        await router.publish(MessageTopic.SETTING, {"action": "copilot_refresh"})

        status = self._status_response()
        return CopilotSettingsResponse(**status.model_dump(), saved=True, writable=True)

    async def chat(
        self,
        db: AsyncSession,
        *,
        admin: AdminDetails,
        request: CopilotChatRequest,
    ) -> CopilotChatResponse:
        try:
            reply, actions = await run_copilot_chat(
                db,
                admin=admin,
                messages=request.messages,
                page_path=request.page_path,
            )
        except CopilotNotConfiguredError as exc:
            await self.raise_error(message=str(exc), code=503)
        except CopilotProviderError as exc:
            await self.raise_error(message=str(exc), code=502)

        return CopilotChatResponse(reply=reply, actions_taken=actions)

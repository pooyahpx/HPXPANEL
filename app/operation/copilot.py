from app.db import AsyncSession
from app.models.admin import AdminDetails
from app.models.copilot import CopilotChatRequest, CopilotChatResponse, CopilotStatusResponse
from app.operation import BaseOperation
from app.services.copilot import run_copilot_chat
from app.services.copilot.llm import CopilotNotConfiguredError, CopilotProviderError
from config import copilot_settings


class CopilotOperation(BaseOperation):
    async def get_status(self) -> CopilotStatusResponse:
        return CopilotStatusResponse(
            enabled=copilot_settings.enabled,
            configured=copilot_settings.is_configured,
            provider=copilot_settings.provider,
            model=copilot_settings.model,
        )

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

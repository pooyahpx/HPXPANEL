from fastapi import APIRouter, Depends

from app.db import AsyncSession, get_db
from app.models.admin import AdminDetails
from app.models.copilot import (
    CopilotChatRequest,
    CopilotChatResponse,
    CopilotSettingsResponse,
    CopilotSettingsUpdate,
    CopilotStatusResponse,
)
from app.operation import OperatorType
from app.operation.copilot import CopilotOperation
from app.utils import responses

from .authentication import get_current, require_permission

router = APIRouter(
    tags=["HPX Copilot"],
    prefix="/api/copilot",
    responses={401: responses._401, 403: responses._403},
)

copilot_operator = CopilotOperation(operator_type=OperatorType.WEB)


@router.get("/status", response_model=CopilotStatusResponse)
async def copilot_status(_: AdminDetails = Depends(get_current)):
    return await copilot_operator.get_status()


@router.put("/settings", response_model=CopilotSettingsResponse)
async def copilot_update_settings(
    payload: CopilotSettingsUpdate,
    _: AdminDetails = Depends(require_permission("settings", "update")),
):
    return await copilot_operator.update_settings(payload)


@router.post("/chat", response_model=CopilotChatResponse)
async def copilot_chat(
    request: CopilotChatRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
):
    return await copilot_operator.chat(db, admin=admin, request=request)

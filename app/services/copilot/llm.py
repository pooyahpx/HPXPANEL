from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from app.models.admin import AdminDetails
from app.models.copilot import CopilotMessage
from app.services.copilot.context import build_panel_snapshot
from app.services.copilot.tools import TOOL_DEFINITIONS, execute_tool, tool_result_content
from config import copilot_settings

logger = logging.getLogger(__name__)


class CopilotNotConfiguredError(RuntimeError):
    pass


class CopilotProviderError(RuntimeError):
    pass


def _system_prompt(*, admin: AdminDetails, snapshot: dict[str, Any]) -> str:
    return (
        "You are HPX Copilot — an operations assistant embedded in the HPXPANEL admin dashboard.\n"
        "You help admins manage HPX Pulse tunnels, HPX ICMP tunnels, users, nodes, and panel troubleshooting.\n"
        "Reply in the same language the user writes (Persian/Farsi or English).\n"
        "Be concise, practical, and step-oriented. Use tools when you need live panel data.\n"
        "Never invent pulse/tunnel IDs — always list or look up first.\n"
        "For Iran connectivity issues, remind that PANEL_URL must include the working port (often :8000).\n"
        "For Pulse agents, mention join commands, Sync button, and `sudo hpx-pulse-agent install-engine --force` when relevant.\n"
        f"Current admin: {admin.username}\n"
        f"Panel context: {json.dumps(snapshot, ensure_ascii=False)}"
    )


async def _chat_completion(messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if not copilot_settings.is_configured:
        raise CopilotNotConfiguredError("Copilot is not configured — set OPENAI_API_KEY in panel .env")

    url = f"{copilot_settings.base_url.rstrip('/')}/v1/chat/completions"
    payload: dict[str, Any] = {
        "model": copilot_settings.model,
        "messages": messages,
        "temperature": 0.3,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    headers = {
        "Authorization": f"Bearer {copilot_settings.api_key}",
        "Content-Type": "application/json",
    }

    timeout = aiohttp.ClientTimeout(total=120.0)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status >= 400:
                detail = (await response.text())[:500]
                raise CopilotProviderError(f"LLM request failed ({response.status}): {detail}")
            return await response.json()


async def run_copilot_chat(
    db,
    *,
    admin: AdminDetails,
    messages: list[CopilotMessage],
    page_path: str | None,
) -> tuple[str, list[str]]:
    snapshot = await build_panel_snapshot(db, admin=admin, page_path=page_path)
    llm_messages: list[dict[str, Any]] = [{"role": "system", "content": _system_prompt(admin=admin, snapshot=snapshot)}]
    for msg in messages:
        llm_messages.append({"role": msg.role, "content": msg.content})

    actions_taken: list[str] = []

    for _ in range(copilot_settings.max_tool_rounds):
        data = await _chat_completion(llm_messages, tools=TOOL_DEFINITIONS)
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            content = (message.get("content") or "").strip()
            if not content:
                raise CopilotProviderError("Empty response from LLM")
            return content, actions_taken

        llm_messages.append(message)

        for call in tool_calls:
            fn = call.get("function") or {}
            name = fn.get("name") or ""
            raw_args = fn.get("arguments") or "{}"
            try:
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            except json.JSONDecodeError:
                arguments = {}

            result, action = await execute_tool(db, admin=admin, name=name, arguments=arguments)
            if action:
                actions_taken.append(action)

            llm_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id"),
                    "content": tool_result_content(result),
                }
            )

    raise CopilotProviderError("Copilot exceeded maximum tool rounds — try a simpler question")

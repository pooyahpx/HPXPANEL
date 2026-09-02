from __future__ import annotations

import asyncio
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


def _is_groq_provider() -> bool:
    provider = copilot_settings.provider.strip().lower()
    base = copilot_settings.base_url.strip().lower()
    return provider == "groq" or "groq.com" in base


def _provider_error_message(status: int, detail: str) -> str:
    lowered = detail.lower()
    if status == 429 and _is_groq_provider():
        return (
            "Groq rate limit reached (too many Copilot requests per minute). "
            "Wait 30–60 seconds and try again. For higher free limits, set "
            "COPILOT_MODEL=openai/gpt-oss-20b in panel .env and restart."
        )
    if status == 429:
        if "insufficient_quota" in lowered or "credit_balance_exhausted" in lowered:
            return (
                "API quota exhausted. For a free provider use Groq: COPILOT_PROVIDER=groq and "
                "OPENAI_API_KEY=gsk_... from console.groq.com"
            )
        return f"Rate limit exceeded (429). Wait a moment and retry. {detail[:240]}"
    if "insufficient_quota" in lowered or "credit_balance_exhausted" in lowered:
        return (
            "API quota exhausted. For a free provider use Groq: COPILOT_PROVIDER=groq and "
            "OPENAI_API_KEY=gsk_... from console.groq.com"
        )
    return f"LLM request failed ({status}): {detail}"


def _rate_limit_wait_seconds(response: aiohttp.ClientResponse, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return min(float(retry_after), 30.0)
        except ValueError:
            pass
    return min(2.0**attempt, 15.0)


def _system_prompt(*, admin: AdminDetails, snapshot: dict[str, Any]) -> str:
    return (
        "You are HPX Copilot — an operations assistant embedded in the HPXPANEL admin dashboard.\n"
        "You help admins manage HPX Pulse tunnels, HPX ICMP tunnels, hosts, users, nodes, and panel troubleshooting.\n"
        "Reply in the same language the user writes (Persian/Farsi or English).\n"
        "Be concise, practical, and step-oriented. Use tools when you need live panel data.\n"
        "Never invent pulse/tunnel IDs — always list or look up first.\n"
        "For proxy share links (vless://, vmess://, trojan://, ss://): use import_proxy_link with confirm=false first. "
        "Do NOT ask the admin for inbound_tag — leave it empty so the tool auto-creates a matching Xray inbound when needed. "
        "Explain the planned inbound + Host, then call import_proxy_link(confirm=true) after admin approval.\n"
        "For Iran connectivity issues, remind that PANEL_URL must include the working port (often :8000).\n"
        "For Pulse agents, mention join commands, Sync button, and `sudo hpx-pulse-agent install-engine --force` when relevant.\n"
        f"Current admin: {admin.username}\n"
        f"Panel context: {json.dumps(snapshot, ensure_ascii=False)}"
    )


async def _chat_completion(messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if not copilot_settings.is_configured:
        raise CopilotNotConfiguredError(
            "Copilot is not configured — set OPENAI_API_KEY (or COPILOT_PROVIDER=ollama) in panel .env"
        )

    url = f"{copilot_settings.base_url.rstrip('/')}/v1/chat/completions"
    payload: dict[str, Any] = {
        "model": copilot_settings.model,
        "messages": messages,
        "temperature": 0.3,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    headers = {"Content-Type": "application/json"}
    api_key = copilot_settings.api_key.strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    timeout = aiohttp.ClientTimeout(total=120.0)
    max_attempts = 3 if _is_groq_provider() else 1
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for attempt in range(max_attempts):
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 429 and attempt < max_attempts - 1:
                    await asyncio.sleep(_rate_limit_wait_seconds(response, attempt))
                    continue
                if response.status >= 400:
                    detail = (await response.text())[:500]
                    raise CopilotProviderError(_provider_error_message(response.status, detail))
                return await response.json()
    raise CopilotProviderError("LLM request failed after rate-limit retries")


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

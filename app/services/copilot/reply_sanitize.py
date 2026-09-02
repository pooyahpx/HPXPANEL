from __future__ import annotations

import re

from app.models.copilot import CopilotMessage

_SHARE_LINK_RE = re.compile(r"(vless|vmess|trojan|ss)://\S+", re.IGNORECASE)
_FAKE_IMPORT_RE = re.compile(r"import_proxy_link\s*\(", re.IGNORECASE)
_CONFIRM_RE = re.compile(
    r"^(بله|تایید|آره|آری|باشه|بزن|انجام بده|yes|y|confirm|ok|okay|go ahead|do it)\s*[!.]*$",
    re.IGNORECASE,
)
_BASH_IMPORT_BLOCK_RE = re.compile(
    r"```(?:bash|sh|shell)?\s*\n.*?import_proxy_link.*?```",
    re.IGNORECASE | re.DOTALL,
)


def extract_share_link(text: str) -> str | None:
    match = _SHARE_LINK_RE.search(text or "")
    return match.group(0) if match else None


def extract_share_link_from_messages(messages: list[CopilotMessage]) -> str | None:
    for msg in reversed(messages):
        if msg.role != "user":
            continue
        link = extract_share_link(msg.content)
        if link:
            return link
    return None


def user_confirmed_import(messages: list[CopilotMessage]) -> bool:
    if not messages:
        return False
    last = messages[-1]
    if last.role != "user":
        return False
    text = last.content.strip()
    if _CONFIRM_RE.match(text):
        return True
    lowered = text.lower()
    return any(token in lowered for token in ("تایید", "بله", "بزن", "confirm", "yes"))


def sanitize_copilot_reply(content: str) -> str:
    """Remove hallucinated shell commands; Copilot tools run inside the panel only."""
    if not _FAKE_IMPORT_RE.search(content):
        return content

    cleaned = _BASH_IMPORT_BLOCK_RE.sub("", content)
    cleaned = re.sub(r"`import_proxy_link\([^`]+`", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"import_proxy_link\([^)]*\)", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    notice = (
        "\n\n---\n"
        "**مهم:** ساخت Host داخل پنل است — روی سرور دستور bash اجرا نمی‌کنی.\n"
        "فقط در همین چت بنویس **بله** یا **تایید** تا Copilot خودش Host را در HPXPANEL بسازد.\n"
        "**Important:** Do not run shell commands. Reply **yes** here and Copilot creates the Host in the panel."
    )
    if notice.strip() not in cleaned:
        cleaned += notice
    return cleaned

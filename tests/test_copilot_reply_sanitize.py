from app.models.copilot import CopilotMessage
from app.services.copilot.reply_sanitize import (
    extract_share_link,
    extract_share_link_from_messages,
    sanitize_copilot_reply,
    user_confirmed_import,
)


def test_extract_share_link():
    link = "vless://uuid@1.2.3.4:443?encryption=none#test"
    assert extract_share_link(f"import this {link} please") == link


def test_user_confirmed_import():
    assert user_confirmed_import([CopilotMessage(role="user", content="بله")])
    assert user_confirmed_import([CopilotMessage(role="user", content="yes")])
    assert not user_confirmed_import([CopilotMessage(role="user", content="show nodes")])


def test_sanitize_removes_fake_bash_import():
    raw = (
        "Preview done.\n```bash\nimport_proxy_link(confirm=true, link=\"vless://x\")\n```\n"
    )
    out = sanitize_copilot_reply(raw)
    assert "import_proxy_link" not in out
    assert "بله" in out or "yes" in out


def test_extract_link_from_messages():
    messages = [
        CopilotMessage(role="user", content="vless://abc@host:443#x"),
        CopilotMessage(role="assistant", content="preview"),
        CopilotMessage(role="user", content="تایید"),
    ]
    assert extract_share_link_from_messages(messages) == "vless://abc@host:443#x"

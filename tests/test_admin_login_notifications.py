from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.notification.discord import admin as discord_admin
from app.notification.telegram import admin as telegram_admin


@pytest.mark.asyncio
async def test_failed_login_notification_outputs_never_render_password(monkeypatch):
    secret = "submitted-password-MUST-NOT-LEAK"
    telegram_send = AsyncMock()
    discord_send = AsyncMock()
    telegram_settings = SimpleNamespace(
        notify_telegram=True,
        channels=SimpleNamespace(admin=None),
        telegram_chat_id=123,
        telegram_topic_id=None,
    )
    discord_settings = SimpleNamespace(
        notify_discord=True,
        channels=SimpleNamespace(admin=None),
        discord_webhook_url="https://discord.invalid/webhook",
    )
    monkeypatch.setattr(telegram_admin, "notification_settings", AsyncMock(return_value=telegram_settings))
    monkeypatch.setattr(discord_admin, "notification_settings", AsyncMock(return_value=discord_settings))
    monkeypatch.setattr(telegram_admin, "send_telegram_message", telegram_send)
    monkeypatch.setattr(discord_admin, "send_discord_webhook", discord_send)

    await telegram_admin.admin_login("test-admin", "192.0.2.1", False)
    await discord_admin.admin_login("test-admin", "192.0.2.1", False)

    telegram_output = telegram_send.await_args.args[0]
    discord_output = discord_send.await_args.args[0]
    assert secret not in telegram_output
    assert "Password" not in telegram_output
    assert secret not in repr(discord_output)
    assert "Password" not in repr(discord_output)

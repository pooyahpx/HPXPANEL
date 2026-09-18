from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.shop.payments import (
    GATEWAY_CARD,
    GATEWAY_IDPAY,
    GATEWAY_NOWPAYMENTS,
    GATEWAY_PAYPAL,
    GATEWAY_STRIPE,
    GATEWAY_ZARINPAL,
    PaymentCreateResult,
    PaymentGatewayError,
    _mask_secret,
    create_payment,
    enabled_gateways,
    fx_toman_per_usd,
    gateway_public_fields,
    toman_to_rial,
    toman_to_usd_cents,
    verify_nowpayments_signature,
    verify_stripe_signature,
)


def _cfg(**kwargs):
    base = {
        "pay_card_enabled": True,
        "pay_zarinpal_enabled": False,
        "pay_zarinpal_merchant_id": None,
        "pay_zarinpal_sandbox": False,
        "pay_idpay_enabled": False,
        "pay_idpay_api_key": None,
        "pay_idpay_sandbox": True,
        "pay_nowpayments_enabled": False,
        "pay_nowpayments_api_key": None,
        "pay_nowpayments_ipn_secret": None,
        "pay_paypal_enabled": False,
        "pay_paypal_client_id": None,
        "pay_paypal_client_secret": None,
        "pay_paypal_sandbox": True,
        "pay_stripe_enabled": False,
        "pay_stripe_secret_key": None,
        "pay_stripe_webhook_secret": None,
        "pay_callback_base_url": "https://panel.example.com",
        "pay_fx_toman_per_usd": 600_000,
        "pay_unpaid_expire_minutes": 60,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_toman_conversions():
    assert toman_to_rial(1000) == 10_000
    assert toman_to_usd_cents(600_000) == 100
    assert toman_to_usd_cents(0) == 50
    assert toman_to_usd_cents(1_200_000, rate_toman_per_usd=600_000) == 200
    assert toman_to_usd_cents(900_000, rate_toman_per_usd=900_000) == 100


def test_fx_helper_and_mask():
    assert fx_toman_per_usd(None) == 600_000
    assert fx_toman_per_usd(_cfg(pay_fx_toman_per_usd=750_000)) == 750_000
    assert fx_toman_per_usd(_cfg(pay_fx_toman_per_usd=100)) == 1000
    assert _mask_secret(None) is None
    assert _mask_secret("short") == "••••"
    assert _mask_secret("abcdefghijklmnop") == "abcd••••mnop"


def test_enabled_gateways_requires_credentials():
    assert enabled_gateways(_cfg()) == [GATEWAY_CARD]
    assert GATEWAY_ZARINPAL not in enabled_gateways(_cfg(pay_zarinpal_enabled=True))
    assert GATEWAY_ZARINPAL in enabled_gateways(
        _cfg(pay_zarinpal_enabled=True, pay_zarinpal_merchant_id="merchant-uuid-1234")
    )
    assert GATEWAY_IDPAY in enabled_gateways(_cfg(pay_idpay_enabled=True, pay_idpay_api_key="idpay-key-123456"))
    assert GATEWAY_NOWPAYMENTS in enabled_gateways(
        _cfg(pay_nowpayments_enabled=True, pay_nowpayments_api_key="now-key-123456")
    )
    assert GATEWAY_PAYPAL not in enabled_gateways(
        _cfg(pay_paypal_enabled=True, pay_paypal_client_id="cid", pay_paypal_client_secret="")
    )
    assert GATEWAY_PAYPAL in enabled_gateways(
        _cfg(pay_paypal_enabled=True, pay_paypal_client_id="cid-12345678", pay_paypal_client_secret="sec-12345678")
    )
    assert GATEWAY_STRIPE in enabled_gateways(
        _cfg(pay_stripe_enabled=True, pay_stripe_secret_key="sk_test_1234567890")
    )
    # Card stays available even when other gateways are on
    gws = enabled_gateways(
        _cfg(
            pay_card_enabled=True,
            pay_zarinpal_enabled=True,
            pay_zarinpal_merchant_id="m-1234567890abcd",
        )
    )
    assert GATEWAY_CARD in gws and GATEWAY_ZARINPAL in gws


def test_gateway_public_fields_mask_secrets():
    fields = gateway_public_fields(
        _cfg(
            pay_zarinpal_enabled=True,
            pay_zarinpal_merchant_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            pay_idpay_enabled=True,
            pay_idpay_api_key="idpay_secret_key_abc",
            pay_paypal_enabled=True,
            pay_paypal_client_id="paypal_client_id_value",
            pay_paypal_client_secret="paypal_client_secret_value",
            pay_stripe_enabled=True,
            pay_stripe_secret_key="sk_live_abcdefghijklmnop",
            pay_stripe_webhook_secret="whsec_abcdefghijklmnop",
            pay_fx_toman_per_usd=720_000,
            pay_unpaid_expire_minutes=45,
        )
    )
    assert "••••" in (fields["pay_zarinpal_merchant_id"] or "")
    assert "••••" in (fields["pay_idpay_api_key"] or "")
    assert "••••" in (fields["pay_paypal_client_id"] or "")
    assert "••••" in (fields["pay_paypal_client_secret"] or "")
    assert "••••" in (fields["pay_stripe_secret_key"] or "")
    assert "••••" in (fields["pay_stripe_webhook_secret"] or "")
    assert fields["pay_fx_toman_per_usd"] == 720_000
    assert fields["pay_unpaid_expire_minutes"] == 45
    assert GATEWAY_ZARINPAL in fields["enabled_gateways"]


def test_nowpayments_signature():
    cfg = _cfg(pay_nowpayments_ipn_secret="ipn-secret")
    body = b'{"payment_status":"finished"}'
    import hashlib
    import hmac

    sig = hmac.new(b"ipn-secret", body, hashlib.sha512).hexdigest()
    assert verify_nowpayments_signature(cfg, body, sig) is True
    assert verify_nowpayments_signature(cfg, body, "bad") is False
    assert verify_nowpayments_signature(_cfg(pay_nowpayments_ipn_secret=None), body, sig) is False


def test_stripe_signature_ok_and_fail():
    import hashlib
    import hmac
    import json
    import time

    secret = "whsec_test_secret_value"
    cfg = _cfg(pay_stripe_webhook_secret=secret)
    payload = {"type": "checkout.session.completed", "data": {"object": {"id": "cs_1"}}}
    body = json.dumps(payload).encode()
    ts = str(int(time.time()))
    signed = f"{ts}.{body.decode()}".encode()
    v1 = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    event = verify_stripe_signature(cfg, body, f"t={ts},v1={v1}")
    assert event["type"] == "checkout.session.completed"

    with pytest.raises(PaymentGatewayError):
        verify_stripe_signature(cfg, body, f"t={ts},v1=deadbeef")


@pytest.mark.asyncio
async def test_create_payment_zarinpal_mocked():
    cfg = _cfg(pay_zarinpal_merchant_id="merchant-id-12345678", pay_zarinpal_sandbox=True)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": {"code": 100, "authority": "A000000000000000000000000000000000000"}, "errors": []}
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("app.shop.payments.httpx.AsyncClient", return_value=mock_client):
        result = await create_payment(
            cfg,
            gateway=GATEWAY_ZARINPAL,
            order_id=42,
            amount_toman=150_000,
            description="Order 42",
        )
    assert isinstance(result, PaymentCreateResult)
    assert result.payment_ref.startswith("A0")
    assert "StartPay" in result.payment_url
    mock_client.post.assert_awaited()


@pytest.mark.asyncio
async def test_create_payment_uses_configured_fx_for_stripe():
    cfg = _cfg(pay_stripe_secret_key="sk_test_1234567890abcdef", pay_fx_toman_per_usd=1_000_000)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "cs_test_1", "url": "https://checkout.stripe.com/c/pay/cs_test_1"}
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("app.shop.payments.httpx.AsyncClient", return_value=mock_client):
        result = await create_payment(
            cfg,
            gateway=GATEWAY_STRIPE,
            order_id=7,
            amount_toman=1_000_000,
            description="Order 7",
        )
    assert result.payment_ref == "cs_test_1"
    posted = mock_client.post.await_args
    form = posted.kwargs.get("data") or posted.args[1] if len(posted.args) > 1 else posted.kwargs["data"]
    # 1_000_000 Toman / 1_000_000 rate = $1.00 = 100 cents
    assert form["line_items[0][price_data][unit_amount]"] == "100"

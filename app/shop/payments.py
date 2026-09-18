"""Shop payment gateway helpers (create invoice + verify callbacks)."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx

from app.db.models import ShopConfig

GATEWAY_CARD = "card"
GATEWAY_ZARINPAL = "zarinpal"
GATEWAY_IDPAY = "idpay"
GATEWAY_NOWPAYMENTS = "nowpayments"
GATEWAY_PAYPAL = "paypal"
GATEWAY_STRIPE = "stripe"

ONLINE_GATEWAYS = (
    GATEWAY_ZARINPAL,
    GATEWAY_IDPAY,
    GATEWAY_NOWPAYMENTS,
    GATEWAY_PAYPAL,
    GATEWAY_STRIPE,
)

ALL_GATEWAYS = (GATEWAY_CARD, *ONLINE_GATEWAYS)


@dataclass(frozen=True)
class PaymentCreateResult:
    payment_ref: str
    payment_url: str
    raw: dict[str, Any] | None = None


class PaymentGatewayError(Exception):
    """Raised when a gateway request fails."""


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "••••"
    return f"{value[:4]}••••{value[-4:]}"


def enabled_gateways(config: ShopConfig) -> list[str]:
    """Return gateway ids that are enabled and have minimum credentials."""
    out: list[str] = []
    if getattr(config, "pay_card_enabled", True):
        out.append(GATEWAY_CARD)
    if getattr(config, "pay_zarinpal_enabled", False) and (config.pay_zarinpal_merchant_id or "").strip():
        out.append(GATEWAY_ZARINPAL)
    if getattr(config, "pay_idpay_enabled", False) and (config.pay_idpay_api_key or "").strip():
        out.append(GATEWAY_IDPAY)
    if getattr(config, "pay_nowpayments_enabled", False) and (config.pay_nowpayments_api_key or "").strip():
        out.append(GATEWAY_NOWPAYMENTS)
    if (
        getattr(config, "pay_paypal_enabled", False)
        and (config.pay_paypal_client_id or "").strip()
        and (config.pay_paypal_client_secret or "").strip()
    ):
        out.append(GATEWAY_PAYPAL)
    if getattr(config, "pay_stripe_enabled", False) and (config.pay_stripe_secret_key or "").strip():
        out.append(GATEWAY_STRIPE)
    return out


def callback_base(config: ShopConfig) -> str:
    base = (getattr(config, "pay_callback_base_url", None) or "").strip().rstrip("/")
    if not base:
        raise PaymentGatewayError("pay_callback_base_url is required for online gateways")
    return base


def callback_url(config: ShopConfig, gateway: str) -> str:
    return urljoin(callback_base(config) + "/", f"api/shop/payments/{gateway}/callback")


def return_url(config: ShopConfig, order_id: int) -> str:
    return urljoin(callback_base(config) + "/", f"api/shop/payments/return?order_id={order_id}")


def toman_to_rial(amount_toman: int) -> int:
    return max(0, int(amount_toman)) * 10


def toman_to_usd_cents(amount_toman: int, rate_toman_per_usd: int = 600_000) -> int:
    """Rough USD conversion for PayPal/Stripe when price is stored in Toman."""
    if amount_toman <= 0:
        return 50  # Stripe minimum-ish
    usd = amount_toman / max(rate_toman_per_usd, 1)
    cents = round(usd * 100)
    return max(50, cents)


async def create_payment(
    config: ShopConfig,
    *,
    gateway: str,
    order_id: int,
    amount_toman: int,
    description: str,
    buyer_email: str | None = None,
) -> PaymentCreateResult:
    if gateway == GATEWAY_ZARINPAL:
        return await _zarinpal_create(config, order_id=order_id, amount_toman=amount_toman, description=description)
    if gateway == GATEWAY_IDPAY:
        return await _idpay_create(config, order_id=order_id, amount_toman=amount_toman, description=description)
    if gateway == GATEWAY_NOWPAYMENTS:
        return await _nowpayments_create(config, order_id=order_id, amount_toman=amount_toman, description=description)
    if gateway == GATEWAY_PAYPAL:
        return await _paypal_create(
            config,
            order_id=order_id,
            amount_toman=amount_toman,
            description=description,
        )
    if gateway == GATEWAY_STRIPE:
        return await _stripe_create(
            config,
            order_id=order_id,
            amount_toman=amount_toman,
            description=description,
            buyer_email=buyer_email,
        )
    raise PaymentGatewayError(f"unsupported gateway: {gateway}")


async def _zarinpal_create(
    config: ShopConfig, *, order_id: int, amount_toman: int, description: str
) -> PaymentCreateResult:
    merchant = (config.pay_zarinpal_merchant_id or "").strip()
    if not merchant:
        raise PaymentGatewayError("Zarinpal merchant id missing")
    sandbox = bool(config.pay_zarinpal_sandbox)
    base = "https://sandbox.zarinpal.com" if sandbox else "https://payment.zarinpal.com"
    payload = {
        "merchant_id": merchant,
        "amount": toman_to_rial(amount_toman),
        "callback_url": return_url(config, order_id),
        "description": description[:255],
        "metadata": {"order_id": str(order_id)},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{base}/pg/v4/payment/request.json", json=payload)
        data = resp.json()
    errors = data.get("errors")
    result = data.get("data") or {}
    code = result.get("code")
    authority = result.get("authority")
    if code != 100 or not authority:
        raise PaymentGatewayError(f"Zarinpal request failed: {errors or data}")
    start_base = "https://sandbox.zarinpal.com" if sandbox else "https://www.zarinpal.com"
    return PaymentCreateResult(
        payment_ref=str(authority),
        payment_url=f"{start_base}/pg/StartPay/{authority}",
        raw=data,
    )


async def verify_zarinpal(config: ShopConfig, *, authority: str, amount_toman: int) -> bool:
    merchant = (config.pay_zarinpal_merchant_id or "").strip()
    sandbox = bool(config.pay_zarinpal_sandbox)
    base = "https://sandbox.zarinpal.com" if sandbox else "https://payment.zarinpal.com"
    payload = {
        "merchant_id": merchant,
        "amount": toman_to_rial(amount_toman),
        "authority": authority,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{base}/pg/v4/payment/verify.json", json=payload)
        data = resp.json()
    result = data.get("data") or {}
    return result.get("code") in (100, 101)


async def _idpay_create(
    config: ShopConfig, *, order_id: int, amount_toman: int, description: str
) -> PaymentCreateResult:
    api_key = (config.pay_idpay_api_key or "").strip()
    if not api_key:
        raise PaymentGatewayError("IDPay API key missing")
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    if config.pay_idpay_sandbox:
        headers["X-SANDBOX"] = "1"
    payload = {
        "order_id": str(order_id),
        "amount": toman_to_rial(amount_toman),
        "callback": return_url(config, order_id),
        "desc": description[:255],
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post("https://api.idpay.ir/v1.1/payment", headers=headers, json=payload)
        data = resp.json()
    if resp.status_code not in (200, 201) or not data.get("id") or not data.get("link"):
        raise PaymentGatewayError(f"IDPay request failed: {data}")
    return PaymentCreateResult(payment_ref=str(data["id"]), payment_url=str(data["link"]), raw=data)


async def verify_idpay(config: ShopConfig, *, payment_id: str, order_id: int) -> bool:
    api_key = (config.pay_idpay_api_key or "").strip()
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    if config.pay_idpay_sandbox:
        headers["X-SANDBOX"] = "1"
    payload = {"id": payment_id, "order_id": str(order_id)}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post("https://api.idpay.ir/v1.1/payment/verify", headers=headers, json=payload)
        data = resp.json()
    status = data.get("status")
    # 100 = paid, 101 = already verified
    return resp.status_code == 200 and str(status) in ("100", "101")


async def _nowpayments_create(
    config: ShopConfig, *, order_id: int, amount_toman: int, description: str
) -> PaymentCreateResult:
    api_key = (config.pay_nowpayments_api_key or "").strip()
    if not api_key:
        raise PaymentGatewayError("NOWPayments API key missing")
    # Invoice amount in USD (approx from Toman)
    price_amount = max(0.5, round(amount_toman / 600_000, 2))
    payload = {
        "price_amount": price_amount,
        "price_currency": "usd",
        "order_id": str(order_id),
        "order_description": description[:255],
        "ipn_callback_url": callback_url(config, GATEWAY_NOWPAYMENTS),
        "success_url": return_url(config, order_id),
        "cancel_url": return_url(config, order_id),
    }
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post("https://api.nowpayments.io/v1/invoice", headers=headers, json=payload)
        data = resp.json()
    invoice_id = data.get("id")
    invoice_url = data.get("invoice_url")
    if not invoice_id or not invoice_url:
        raise PaymentGatewayError(f"NOWPayments invoice failed: {data}")
    return PaymentCreateResult(payment_ref=str(invoice_id), payment_url=str(invoice_url), raw=data)


def verify_nowpayments_signature(config: ShopConfig, body: bytes, signature: str | None) -> bool:
    secret = (config.pay_nowpayments_ipn_secret or "").strip()
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(digest, signature)


async def _paypal_access_token(config: ShopConfig) -> str:
    client_id = (config.pay_paypal_client_id or "").strip()
    secret = (config.pay_paypal_client_secret or "").strip()
    base = "https://api-m.sandbox.paypal.com" if config.pay_paypal_sandbox else "https://api-m.paypal.com"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{base}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, secret),
        )
        data = resp.json()
    token = data.get("access_token")
    if not token:
        raise PaymentGatewayError(f"PayPal auth failed: {data}")
    return token


async def _paypal_create(
    config: ShopConfig, *, order_id: int, amount_toman: int, description: str
) -> PaymentCreateResult:
    token = await _paypal_access_token(config)
    base = "https://api-m.sandbox.paypal.com" if config.pay_paypal_sandbox else "https://api-m.paypal.com"
    cents = toman_to_usd_cents(amount_toman)
    amount = f"{cents / 100:.2f}"
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": str(order_id),
                "description": description[:127],
                "amount": {"currency_code": "USD", "value": amount},
                "custom_id": str(order_id),
            }
        ],
        "application_context": {
            "return_url": return_url(config, order_id),
            "cancel_url": return_url(config, order_id),
            "user_action": "PAY_NOW",
        },
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{base}/v2/checkout/orders", headers=headers, json=payload)
        data = resp.json()
    order_ref = data.get("id")
    approve = None
    for link in data.get("links") or []:
        if link.get("rel") == "approve":
            approve = link.get("href")
            break
    if not order_ref or not approve:
        raise PaymentGatewayError(f"PayPal create failed: {data}")
    return PaymentCreateResult(payment_ref=str(order_ref), payment_url=str(approve), raw=data)


async def capture_paypal(config: ShopConfig, *, paypal_order_id: str) -> bool:
    token = await _paypal_access_token(config)
    base = "https://api-m.sandbox.paypal.com" if config.pay_paypal_sandbox else "https://api-m.paypal.com"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{base}/v2/checkout/orders/{paypal_order_id}/capture", headers=headers)
        data = resp.json()
    return resp.status_code in (200, 201) and data.get("status") == "COMPLETED"


async def _stripe_create(
    config: ShopConfig,
    *,
    order_id: int,
    amount_toman: int,
    description: str,
    buyer_email: str | None = None,
) -> PaymentCreateResult:
    secret = (config.pay_stripe_secret_key or "").strip()
    if not secret:
        raise PaymentGatewayError("Stripe secret key missing")
    cents = toman_to_usd_cents(amount_toman)
    form = {
        "mode": "payment",
        "success_url": return_url(config, order_id) + "&session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": return_url(config, order_id),
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][product_data][name]": description[:120] or f"Order #{order_id}",
        "line_items[0][price_data][unit_amount]": str(cents),
        "line_items[0][quantity]": "1",
        "client_reference_id": str(order_id),
        "metadata[order_id]": str(order_id),
    }
    if buyer_email:
        form["customer_email"] = buyer_email
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.stripe.com/v1/checkout/sessions",
            data=form,
            auth=(secret, ""),
        )
        data = resp.json()
    session_id = data.get("id")
    url = data.get("url")
    if not session_id or not url:
        raise PaymentGatewayError(f"Stripe session failed: {data}")
    return PaymentCreateResult(payment_ref=str(session_id), payment_url=str(url), raw=data)


def verify_stripe_signature(config: ShopConfig, body: bytes, signature_header: str | None) -> dict[str, Any]:
    """Minimal Stripe webhook signature check (v1). Returns parsed JSON event."""
    secret = (config.pay_stripe_webhook_secret or "").strip()
    if not secret:
        raise PaymentGatewayError("Stripe webhook secret missing")
    if not signature_header:
        raise PaymentGatewayError("Missing Stripe-Signature")
    parts = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
    timestamp = parts.get("t")
    v1 = parts.get("v1")
    if not timestamp or not v1:
        raise PaymentGatewayError("Invalid Stripe-Signature")
    signed = f"{timestamp}.{body.decode('utf-8')}".encode()
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, v1):
        raise PaymentGatewayError("Stripe signature mismatch")
    return json.loads(body)


def gateway_public_fields(config: ShopConfig) -> dict[str, Any]:
    """Safe config fields for API responses (secrets masked)."""
    return {
        "pay_card_enabled": bool(getattr(config, "pay_card_enabled", True)),
        "pay_zarinpal_enabled": bool(getattr(config, "pay_zarinpal_enabled", False)),
        "pay_zarinpal_merchant_id": getattr(config, "pay_zarinpal_merchant_id", None),
        "pay_zarinpal_sandbox": bool(getattr(config, "pay_zarinpal_sandbox", False)),
        "pay_idpay_enabled": bool(getattr(config, "pay_idpay_enabled", False)),
        "pay_idpay_api_key": _mask_secret(getattr(config, "pay_idpay_api_key", None)),
        "pay_idpay_sandbox": bool(getattr(config, "pay_idpay_sandbox", True)),
        "pay_nowpayments_enabled": bool(getattr(config, "pay_nowpayments_enabled", False)),
        "pay_nowpayments_api_key": _mask_secret(getattr(config, "pay_nowpayments_api_key", None)),
        "pay_nowpayments_ipn_secret": _mask_secret(getattr(config, "pay_nowpayments_ipn_secret", None)),
        "pay_paypal_enabled": bool(getattr(config, "pay_paypal_enabled", False)),
        "pay_paypal_client_id": getattr(config, "pay_paypal_client_id", None),
        "pay_paypal_client_secret": _mask_secret(getattr(config, "pay_paypal_client_secret", None)),
        "pay_paypal_sandbox": bool(getattr(config, "pay_paypal_sandbox", True)),
        "pay_stripe_enabled": bool(getattr(config, "pay_stripe_enabled", False)),
        "pay_stripe_secret_key": _mask_secret(getattr(config, "pay_stripe_secret_key", None)),
        "pay_stripe_webhook_secret": _mask_secret(getattr(config, "pay_stripe_webhook_secret", None)),
        "pay_callback_base_url": getattr(config, "pay_callback_base_url", None),
        "enabled_gateways": enabled_gateways(config),
    }

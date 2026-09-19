# Shop & payment gateways

Runbook for the Telegram shop: enable selling, card vs online gateways, multi-shop deep links, and revenue vs create-budget ledgers.

## Enable the shop

1. Open **Dashboard → Shop → Settings** (or Telegram admin → Shop manage).
2. Turn **Enabled** on.
3. Add at least one **plan** with groups, data, days, and price (Toman).
4. For card-to-card: enable **Card**, set card number(s) / holder, optional note and photos.
5. For online gateways: enable the gateway, paste credentials, set **callback base URL** to your public panel URL (HTTPS).

Buyers open the bot and use **Shop** (or `/start`). Admins approve pending card orders; online paid orders auto-fulfill when the gateway callback succeeds.

## Payment methods

| Method | Buyer flow | Admin |
|--------|------------|--------|
| **Card** | Transfer → send receipt photo → order `pending` | Approve / reject in dashboard or Telegram |
| **Online** (Zarinpal, IDPay, NOWPayments, PayPal, Stripe) | Pay link → `awaiting_payment` → paid → fulfilled | Callbacks under `/api/shop/payment/...` |

### FX & unpaid TTL

- **FX (Toman per USD)** — used for PayPal / Stripe / NOWPayments amount conversion. Minimum effective rate is clamped for safety.
- **Unpaid expire minutes** — online orders in `awaiting_payment` older than this become `expired` and are not fulfillable.

Secrets (merchant IDs, API keys) are masked in Telegram admin views (`••••`).

## Multi-shop (several sellers)

Each admin can have their own enabled `ShopConfig`. When more than one shop is enabled:

- Buyers see a **seller picker** on first visit.
- Preference is stored on the Telegram profile (`preferred_shop_admin_id`).
- Deep links skip the picker:

  - `/start shop_<admin_username>`
  - `/start seller_<admin_username>`

Plans and orders always belong to the selected shop admin.

## Revenue ledger vs create-budget

| Ledger | What it tracks | Who settles |
|--------|----------------|-------------|
| **Revenue** (Shop → Revenue) | Paid/approved shop **sales** by gateway (`card`, `zarinpal`, …) | Owner |
| **Accounting** (create-budget) | Admin create-budget charges/credits for panel user provisioning | Owner |

Approving a shop order records a **sale** row in the revenue ledger (idempotent per `order_id`). Use **by_gateway** totals for daily/period gateway reconciliation.

## Checklist

- [ ] Shop enabled + plans + groups
- [ ] Card and/or online gateways with credentials
- [ ] Callback base URL reachable from the internet
- [ ] FX rate set if using USD gateways
- [ ] Unpaid TTL sensible for your buyers
- [ ] Multi-shop: share `shop_<username>` links if needed
- [ ] Owner reviews Revenue + Accounting settle toggles

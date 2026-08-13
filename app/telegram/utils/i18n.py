"""FA/EN strings for Telegram shop + language picker."""

from __future__ import annotations

from html import escape

from aiogram.utils.formatting import html_decoration

b = html_decoration.bold
c = html_decoration.code

GB = 1024**3


def rich(lang: str, key: str, **kwargs) -> str:
    """Apply HTML bold/code placeholders, then format kwargs.

    HTML tokens ({b}/{c}) must be expanded before str.format, otherwise
    keys like admin_shop_home crash with KeyError('b') and the button
    appears dead.
    """
    table = STRINGS.get(lang) or STRINGS["en"]
    text = table.get(key) or STRINGS["en"].get(key) or key
    text = (
        text.replace("{b}", "<b>")
        .replace("{/b}", "</b>")
        .replace("{c}", "<code>")
        .replace("{/c}", "</code>")
    )
    if kwargs:
        text = text.format(**kwargs)
    return text


def t(lang: str, key: str, **kwargs) -> str:
    table = STRINGS.get(lang) or STRINGS["en"]
    text = table.get(key) or STRINGS["en"].get(key) or key
    if kwargs:
        # Protect rich-text tokens if a plain t() call includes them + kwargs.
        text = (
            text.replace("{b}", "{{b}}")
            .replace("{/b}", "{{/b}}")
            .replace("{c}", "{{c}}")
            .replace("{/c}", "{{/c}}")
        )
        text = text.format(**kwargs)
    return text


def format_bytes(n: int) -> str:
    if not n:
        return "∞"
    if n >= GB:
        val = n / GB
        return f"{val:g} GB"
    return f"{n} B"


def format_price(toman: int) -> str:
    return f"{toman:,}".replace(",", "٬") if toman else "0"


STRINGS: dict[str, dict[str, str]] = {
    "fa": {
        "choose_lang": "🌐 زبان را انتخاب کنید\nChoose your language",
        "lang_set": "✅ زبان روی فارسی تنظیم شد",
        "shop_disabled": "🛍 فروشگاه فعلاً غیرفعال است.",
        "shop_home": "🛍 {b}فروشگاه HPXPANEL{/b}\n\nبه فروشگاه ما خوش آمدید.",
        "shop_plans_prompt": "📦 {b}پلن‌ها{/b}\n\nیکی از پلن‌ها را انتخاب کنید:",
        "shop_empty": "هنوز پلنی تعریف نشده است.",
        "plan_line": "{name}\n📦 {data} · 📅 {days} روز · 💰 {price} تومان",
        "days_unlimited": "نامحدود",
        "pay_title": "💳 پرداخت کارت‌به‌کارت\n\n{b}پلن:{/b} {name}\n{b}حجم:{/b} {data}\n{b}مدت:{/b} {days}\n{b}مبلغ:{/b} {price} تومان",
        "pay_card": "\n\n🏦 کارت: {c}{card}{/c}\n👤 به نام: {holder}\n\nبعد از واریز، {b}عکس رسید{/b} را همینجا بفرستید.",
        "pay_no_card": "\n\n⚠️ ادمین هنوز شماره کارت ثبت نکرده است.",
        "send_receipt": "🖼 لطفاً فقط عکس رسید پرداخت را بفرستید.",
        "order_created": "✅ سفارش #{id} ثبت شد.\nبعد از تأیید ادمین، اکانت براتون ارسال می‌شود.",
        "order_approved": "✅ سفارش #{id} تأیید شد.\n👤 یوزرنیم: {c}{username}{/c}\n🔗 سابسکریپشن:\n{url}",
        "order_rejected": "❌ سفارش #{id} رد شد.",
        "my_orders": "📋 سفارش‌های شما:",
        "order_row": "#{id} · {plan} · {status} · {price} تومان",
        "status_pending": "در انتظار",
        "status_approved": "تأیید شده",
        "status_rejected": "رد شده",
        "btn_shop": "🛍 فروشگاه",
        "btn_my_orders": "📋 سفارش‌ها",
        "btn_lang": "🌐 زبان",
        "btn_back": "⬅️ بازگشت",
        "btn_buy": "خرید",
        "btn_plans": "📦 پلن‌ها",
        "btn_admin_shop": "🛍 مدیریت فروشگاه",
        "btn_promote_admin": "👤 ادمین کردن",
        "owner_claimed": "✅ شما به‌عنوان اونر پنل شناسایی شدید.",
        "claim_ask_password": "🔑 رمز ورود پنل (اکانت اونر) را بفرستید تا تلگرام‌تان به اونر وصل شود:",
        "claim_ok": "✅ تلگرام شما به اونر پنل وصل شد. دوباره /start بزنید.",
        "claim_bad_password": "❌ رمز اشتباه است.",
        "promote_ask_target": "👤 آیدی عددی تلگرام شخص را بفرستید، یا یک پیام از او را فوروارد کنید:",
        "promote_ok": "✅ ادمین ساخته شد.\nیوزرنیم پنل: {c}{username}{/c}\nرمز: {c}{password}{/c}\nالان می‌تواند /start بزند.",
        "promote_exists": "⚠️ این تلگرام از قبل ادمین است: {username}",
        "promote_fail": "❌ ساخت ادمین ناموفق بود: {error}",
        "admin_shop_home": "🛍 {b}مدیریت فروشگاه{/b}\nفعال: {enabled}\nکارت: {card}\nبه نام: {holder}\nتوضیحات کارت: {card_note}\nعکس کارت: {card_photos}\nپلن‌های فعال: {plans}\nسفارش‌های باز: {pending}",
        "admin_enabled_on": "✅ فروشگاه روشن شد",
        "admin_enabled_off": "⏸ فروشگاه خاموش شد",
        "admin_ask_card": "💳 شماره کارت را بفرستید:",
        "admin_ask_holder": "👤 نام صاحب کارت را بفرستید:",
        "admin_card_saved": "✅ اطلاعات کارت ذخیره شد",
        "admin_ask_plan_name": "📦 نام پلن را بفرستید (مثلاً ۳۰ گیگ یک‌ماهه):",
        "admin_ask_plan_gb": "📶 حجم را به گیگابایت بفرستید (۰ = نامحدود):",
        "admin_ask_plan_days": "📅 تعداد روز را بفرستید (۰ = نامحدود):",
        "admin_ask_plan_price": "💰 قیمت به تومان را بفرستید:",
        "admin_ask_plan_groups": "👥 آیدی گروه‌ها را با کاما بفرستید (مثلاً 1,2) یا - برای هیچ:",
        "admin_plan_created": "✅ پلن ساخته شد: {name}",
        "admin_plan_toggled": "پلن {name}: {state}",
        "admin_plan_deleted": "🗑 پلن حذف شد",
        "admin_pending_empty": "سفارش بازی نیست.",
        "admin_new_order": "🧾 سفارش جدید #{id}\nخریدار: {buyer}\nپلن: {plan}\nمبلغ: {price} تومان",
        "admin_approved": "✅ سفارش تأیید و یوزر ساخته شد: {username}",
        "admin_rejected": "❌ سفارش رد شد",
        "btn_enable": "🟢 روشن کردن",
        "btn_disable": "🔴 خاموش کردن",
        "btn_set_card": "💳 کارت",
        "btn_card_note": "📝 توضیحات کارت",
        "btn_card_photos": "🖼 عکس‌های کارت",
        "btn_support": "💬 پشتیبانی",
        "btn_support_reply": "↩️ پاسخ",
        "admin_ask_card_note": "📝 توضیحات بخش کارت را بفرستید (یا - برای پاک کردن):",
        "admin_card_note_saved": "✅ توضیحات کارت ذخیره شد",
        "admin_ask_card_photos": "🖼 عکس(های) کارت را بفرستید.\n/done وقتی تمام شد · /clear برای حذف همه",
        "admin_card_photos_saved": "✅ {count} عکس کارت ذخیره شد",
        "admin_card_photos_cleared": "🗑 عکس‌های کارت پاک شد",
        "admin_card_photo_added": "➕ عکس اضافه شد ({count}). /done برای ذخیره",
        "support_prompt": "💬 پیام خود را بفرستید (متن یا عکس). ادمین به زودی پاسخ می‌دهد.",
        "support_sent": "✅ پیام شما برای پشتیبانی ارسال شد.",
        "support_from_user": "💬 پیام پشتیبانی\nاز: {buyer}\nآیدی: {c}{id}{/c}",
        "support_reply_prompt": "↩️ پاسخ خود را برای این کاربر بفرستید:",
        "support_reply_sent": "✅ پاسخ ارسال شد.",
        "support_reply_received": "💬 پاسخ پشتیبانی:\n\n{message}",
        "btn_add_plan": "➕ پلن جدید",
        "btn_list_plans": "📦 لیست پلن‌ها",
        "btn_pending": "🧾 سفارش‌های باز",
        "btn_approve": "✅ تأیید",
        "btn_reject": "❌ رد",
        "btn_deactivate": "⏸ غیرفعال",
        "btn_activate": "▶️ فعال",
        "btn_delete": "🗑 حذف",
        "invalid_number": "❌ عدد معتبر بفرستید",
        "canceled": "💢 لغو شد",
        "no_shop_for_admin": "ابتدا فروشگاه را از منوی مدیریت روشن کنید و کارت/پلن بسازید.",
        "active": "فعال",
        "inactive": "غیرفعال",
        "yes": "بله",
        "no": "خیر",
        "claim_hint": "اگر اونر پنل هستی، دستور /claimowner را بفرست و رمز ورود پنل را بده.",
    },
    "en": {
        "choose_lang": "🌐 Choose your language\nزبان را انتخاب کنید",
        "lang_set": "✅ Language set to English",
        "shop_disabled": "🛍 Shop is currently disabled.",
        "shop_home": "🛍 {b}HPXPANEL Shop{/b}\n\nWelcome to our shop.",
        "shop_plans_prompt": "📦 {b}Plans{/b}\n\nPick a plan:",
        "shop_empty": "No plans available yet.",
        "plan_line": "{name}\n📦 {data} · 📅 {days} days · 💰 {price} Toman",
        "days_unlimited": "Unlimited",
        "pay_title": "💳 Card-to-card payment\n\n{b}Plan:{/b} {name}\n{b}Data:{/b} {data}\n{b}Duration:{/b} {days}\n{b}Price:{/b} {price} Toman",
        "pay_card": "\n\n🏦 Card: {c}{card}{/c}\n👤 Holder: {holder}\n\nAfter transfer, send the {b}receipt photo{/b} here.",
        "pay_no_card": "\n\n⚠️ Admin has not set a card number yet.",
        "send_receipt": "🖼 Please send only the payment receipt photo.",
        "order_created": "✅ Order #{id} submitted.\nYou will receive your account after admin approval.",
        "order_approved": "✅ Order #{id} approved.\n👤 Username: {c}{username}{/c}\n🔗 Subscription:\n{url}",
        "order_rejected": "❌ Order #{id} was rejected.",
        "my_orders": "📋 Your orders:",
        "order_row": "#{id} · {plan} · {status} · {price} Toman",
        "status_pending": "pending",
        "status_approved": "approved",
        "status_rejected": "rejected",
        "btn_shop": "🛍 Shop",
        "btn_my_orders": "📋 Orders",
        "btn_lang": "🌐 Language",
        "btn_back": "⬅️ Back",
        "btn_buy": "Buy",
        "btn_plans": "📦 Plans",
        "btn_admin_shop": "🛍 Manage shop",
        "btn_promote_admin": "👤 Make admin",
        "owner_claimed": "✅ You are recognized as the panel owner.",
        "claim_ask_password": "🔑 Send the panel owner login password to bind your Telegram:",
        "claim_ok": "✅ Your Telegram is now bound to the panel owner. Send /start again.",
        "claim_bad_password": "❌ Wrong password.",
        "promote_ask_target": "👤 Send their numeric Telegram ID, or forward a message from them:",
        "promote_ok": "✅ Admin created.\nPanel username: {c}{username}{/c}\nPassword: {c}{password}{/c}\nThey can /start now.",
        "promote_exists": "⚠️ This Telegram is already an admin: {username}",
        "promote_fail": "❌ Failed to create admin: {error}",
        "admin_shop_home": "🛍 {b}Shop admin{/b}\nEnabled: {enabled}\nCard: {card}\nHolder: {holder}\nCard note: {card_note}\nCard photos: {card_photos}\nActive plans: {plans}\nPending orders: {pending}",
        "admin_enabled_on": "✅ Shop enabled",
        "admin_enabled_off": "⏸ Shop disabled",
        "admin_ask_card": "💳 Send the card number:",
        "admin_ask_holder": "👤 Send the card holder name:",
        "admin_card_saved": "✅ Card details saved",
        "admin_ask_plan_name": "📦 Send plan name (e.g. 30GB monthly):",
        "admin_ask_plan_gb": "📶 Send data limit in GB (0 = unlimited):",
        "admin_ask_plan_days": "📅 Send duration in days (0 = unlimited):",
        "admin_ask_plan_price": "💰 Send price in Toman:",
        "admin_ask_plan_groups": "👥 Send group IDs comma-separated (e.g. 1,2) or - for none:",
        "admin_plan_created": "✅ Plan created: {name}",
        "admin_plan_toggled": "Plan {name}: {state}",
        "admin_plan_deleted": "🗑 Plan deleted",
        "admin_pending_empty": "No pending orders.",
        "admin_new_order": "🧾 New order #{id}\nBuyer: {buyer}\nPlan: {plan}\nAmount: {price} Toman",
        "admin_approved": "✅ Order approved, user created: {username}",
        "admin_rejected": "❌ Order rejected",
        "btn_enable": "🟢 Enable",
        "btn_disable": "🔴 Disable",
        "btn_set_card": "💳 Card",
        "btn_card_note": "📝 Card note",
        "btn_card_photos": "🖼 Card photos",
        "btn_support": "💬 Support",
        "btn_support_reply": "↩️ Reply",
        "admin_ask_card_note": "📝 Send card section instructions (or - to clear):",
        "admin_card_note_saved": "✅ Card note saved",
        "admin_ask_card_photos": "🖼 Send card photo(s).\n/done when finished · /clear to remove all",
        "admin_card_photos_saved": "✅ Saved {count} card photo(s)",
        "admin_card_photos_cleared": "🗑 Card photos cleared",
        "admin_card_photo_added": "➕ Photo added ({count}). /done to save",
        "support_prompt": "💬 Send your message (text or photo). Support will reply soon.",
        "support_sent": "✅ Your message was sent to support.",
        "support_from_user": "💬 Support message\nFrom: {buyer}\nID: {c}{id}{/c}",
        "support_reply_prompt": "↩️ Send your reply to this user:",
        "support_reply_sent": "✅ Reply sent.",
        "support_reply_received": "💬 Support reply:\n\n{message}",
        "btn_add_plan": "➕ New plan",
        "btn_list_plans": "📦 Plans",
        "btn_pending": "🧾 Pending",
        "btn_approve": "✅ Approve",
        "btn_reject": "❌ Reject",
        "btn_deactivate": "⏸ Disable",
        "btn_activate": "▶️ Enable",
        "btn_delete": "🗑 Delete",
        "invalid_number": "❌ Send a valid number",
        "canceled": "💢 Canceled",
        "no_shop_for_admin": "Enable the shop and add card/plans from Manage shop first.",
        "active": "active",
        "inactive": "inactive",
        "yes": "Yes",
        "no": "No",
        "claim_hint": "If you are the panel owner, send /claimowner and enter your panel password.",
    },
}


def plan_caption(lang: str, name: str, data_limit: int, expire_days: int, price: int) -> str:
    days = t(lang, "days_unlimited") if not expire_days else str(expire_days)
    return t(
        lang,
        "plan_line",
        name=escape(name),
        data=format_bytes(data_limit),
        days=days,
        price=format_price(price),
    )

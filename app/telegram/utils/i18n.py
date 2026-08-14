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
        "pay_cards_header": "\n\n🏦 کارت‌های بانکی:",
        "pay_card_item": "{index}. {c}{card}{/c} · 👤 {holder}",
        "pay_cards_footer": "\n\nبعد از واریز، {b}عکس رسید{/b} را همینجا بفرستید.",
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
        "btn_test": "🧪 کانفیگ تست",
        "test_claim_ok": "✅ کانفیگ تست شما آماده است.\n👤 یوزرنیم: {c}{username}{/c}\n🔗 سابسکریپشن:\n{url}",
        "test_already_claimed": "⚠️ قبلاً کانفیگ تست گرفته‌اید. هر کاربر فقط یک‌بار می‌تواند تست بگیرد.",
        "test_disabled": "🧪 کانفیگ تست فعلاً فعال نیست.",
        "btn_admin_shop": "🛍 مدیریت فروشگاه",
        "btn_promote_admin": "👤 ادمین کردن",
        "owner_claimed": "✅ شما به‌عنوان اونر پنل شناسایی شدید.",
        "claim_ask_password": "🔑 رمز ورود پنل (اکانت اونر) را بفرستید تا تلگرام‌تان به اونر وصل شود:",
        "claim_ok": "✅ تلگرام شما به اونر پنل وصل شد. دوباره /start بزنید.",
        "claim_bad_password": "❌ رمز اشتباه است.",
        "promote_ask_target": "👤 آیدی عددی تلگرام شخص را بفرستید، یا یک پیام از او را فوروارد کنید:",
        "promote_ask_username": "👤 یوزرنیم اکانت ادمین در پنل را بفرستید (همان که با آن لاگین می‌کند):",
        "promote_ok": "✅ تلگرام به ادمین پنل وصل شد.\nیوزرنیم: {c}{username}{/c}\nبا همان رمز پنل می‌تواند /start بزند.",
        "promote_exists": "⚠️ این تلگرام از قبل ادمین است: {username}",
        "promote_panel_not_found": "❌ ادمین با این یوزرنیم در پنل پیدا نشد.",
        "promote_owner_forbidden": "❌ اکانت اونر از این مسیر وصل نمی‌شود. اونر باید با رمز پنل /claim_owner بزند.",
        "promote_panel_linked": "⚠️ این ادمین پنل از قبل به تلگرام دیگری وصل است.",
        "promote_fail": "❌ اتصال ادمین ناموفق بود: {error}",
        "admin_shop_home": "🛍 {b}مدیریت فروشگاه{/b}\nفعال: {enabled}\nکارت‌ها: {cards}\nپیام خوش‌آمد: {welcome}\nتوضیحات کارت: {card_note}\nعکس کارت: {card_photos}\nتست: {test}\nپلن‌های فعال: {plans}\nسفارش‌های باز: {pending}",
        "admin_cards_count": "{count} کارت",
        "admin_test_summary": "{data} · {days} روز · گروه {groups}",
        "admin_test_enabled_on": "✅ کانفیگ تست فعال شد",
        "admin_test_enabled_off": "⏸ کانفیگ تست غیرفعال شد",
        "admin_ask_test_gb": "🧪 حجم کانفیگ تست را به گیگابایت بفرستید (۰ = نامحدود):",
        "admin_ask_test_days": "🧪 مدت تست به روز (۰ = نامحدود):",
        "admin_ask_test_groups": "🧪 آیدی گروه‌های تست را با کاما بفرستید (مثلاً 1,2):",
        "admin_test_saved": "✅ تنظیمات کانفیگ تست ذخیره شد",
        "admin_order_approved_by_other": "✅ {b}سفارش #{id} توسط ادمین دیگر تأیید شد{/b}\n\n👤 ادمین: {c}{admin}{/c}\n🛒 خریدار: {buyer}\n📦 پلن: {plan}\n🔑 یوزر: {c}{username}{/c}",
        "admin_enabled_on": "✅ فروشگاه روشن شد",
        "admin_enabled_off": "⏸ فروشگاه خاموش شد",
        "admin_ask_card": "💳 شماره کارت را بفرستید.\n/done برای ذخیره · /clear برای پاک کردن همه\nحداکثر ۳ کارت",
        "admin_ask_holder": "👤 نام صاحب کارت را بفرستید:",
        "admin_ask_card_next": "💳 کارت {count} از {max} ذخیره شد.\nشماره کارت بعدی را بفرستید یا /done:",
        "admin_card_saved": "✅ {count} کارت ذخیره شد",
        "admin_cards_cleared": "🗑 کارت‌ها پاک شد",
        "admin_ask_plan_name": "📦 نام پلن را بفرستید (مثلاً ۳۰ گیگ یک‌ماهه):",
        "admin_ask_plan_gb": "📶 حجم را به گیگابایت بفرستید (۰ = نامحدود):",
        "admin_ask_plan_days": "📅 تعداد روز را بفرستید (۰ = نامحدود):",
        "admin_ask_plan_price": "💰 قیمت به تومان را بفرستید:",
        "admin_ask_plan_groups": "👥 آیدی گروه‌ها را با کاما بفرستید (مثلاً 1,2) یا - برای هیچ:",
        "admin_ask_plan_ip_limit": "👥 تعداد کاربر همزمان را بفرستید (مثلاً 2) یا - برای نامحدود:",
        "admin_ask_plan_hwid_limit": "📱 تعداد دستگاه را بفرستید:\n• عدد (مثلاً 3) = حداکثر دستگاه\n• 0 = بدون محدودیت دستگاه\n• - = پیش‌فرض پنل",
        "admin_plan_edit": "✏️ {b}ویرایش پلن{/b}: {name}\n\n📶 {data} · 📅 {days} · 💰 {price} تومان\n👥 کاربر: {users} · 📱 دستگاه: {devices}\n👥 گروه‌ها: {groups}",
        "admin_plan_updated": "✅ پلن به‌روز شد",
        "admin_ask_edit_plan_name": "📦 نام جدید پلن (فعلی: {current}):",
        "admin_ask_edit_plan_gb": "📶 حجم جدید به GB (فعلی: {current}، 0=نامحدود):",
        "admin_ask_edit_plan_days": "📅 روز جدید (فعلی: {current}، 0=نامحدود):",
        "admin_ask_edit_plan_price": "💰 قیمت جدید به تومان (فعلی: {current}):",
        "admin_ask_edit_plan_groups": "👥 گروه‌ها (فعلی: {current}) — کاما یا -:",
        "admin_ask_edit_plan_users": "👥 تعداد کاربر همزمان (فعلی: {current}) — عدد یا -:",
        "admin_ask_edit_plan_hwid": "📱 تعداد دستگاه (فعلی: {current}):\n0=بدون محدودیت · -=پیش‌فرض",
        "btn_edit_plan_name": "📦 نام",
        "btn_edit_plan_gb": "📶 حجم",
        "btn_edit_plan_days": "📅 روز",
        "btn_edit_plan_price": "💰 قیمت",
        "btn_edit_plan_groups": "👥 گروه",
        "btn_edit_plan_users": "👥 کاربر",
        "btn_edit_plan_hwid": "📱 دستگاه",
        "btn_toggle_plan": "⏯ فعال/غیرفعال",
        "limit_unlimited": "نامحدود",
        "limit_default": "پیش‌فرض",
        "limit_disabled": "غیرفعال",
        "admin_plan_created": "✅ پلن ساخته شد: {name}",
        "admin_plan_toggled": "پلن {name}: {state}",
        "admin_plan_deleted": "🗑 پلن حذف شد",
        "admin_pending_empty": "سفارش بازی نیست.",
        "admin_new_order": "🧾 سفارش جدید #{id}\nخریدار: {buyer}\nپلن: {plan}\nمبلغ: {price} تومان",
        "admin_approved": "✅ سفارش تأیید و یوزر ساخته شد: {username}",
        "admin_rejected": "❌ سفارش رد شد",
        "btn_enable": "🟢 روشن کردن",
        "btn_disable": "🔴 خاموش کردن",
        "btn_set_card": "💳 کارت‌ها",
        "btn_test_settings": "🧪 تنظیم تست",
        "btn_toggle_test": "⏯ تست روشن/خاموش",
        "btn_card_note": "📝 توضیحات کارت",
        "btn_card_photos": "🖼 عکس‌های کارت",
        "btn_support": "💬 پشتیبانی",
        "btn_support_reply": "↩️ پاسخ",
        "admin_ask_card_note": "📝 توضیحات بخش کارت را بفرستید (یا - برای پاک کردن):",
        "admin_ask_welcome": "👋 پیام خوش‌آمد فروشگاه را بفرستید.\nاین متن جایگزین پیام پیش‌فرض می‌شود.\nبرای بازگشت به پیش‌فرض، - بفرستید.",
        "admin_welcome_saved": "✅ پیام خوش‌آمد ذخیره شد",
        "welcome_default_hint": "پیش‌فرض",
        "admin_user_joined": "👋 {b}کاربر جدید به ربات پیوست{/b}\n\n👤 نام: {name}\n📛 یوزرنیم: {username}\n🆔 آیدی: {c}{id}{/c}",
        "btn_welcome": "👋 خوش‌آمد",
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
        "pay_cards_header": "\n\n🏦 Bank cards:",
        "pay_card_item": "{index}. {c}{card}{/c} · 👤 {holder}",
        "pay_cards_footer": "\n\nAfter transfer, send the {b}receipt photo{/b} here.",
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
        "btn_test": "🧪 Test config",
        "test_claim_ok": "✅ Your test config is ready.\n👤 Username: {c}{username}{/c}\n🔗 Subscription:\n{url}",
        "test_already_claimed": "⚠️ You already claimed a test config. One test per user only.",
        "test_disabled": "🧪 Test config is not available.",
        "btn_admin_shop": "🛍 Manage shop",
        "btn_promote_admin": "👤 Make admin",
        "owner_claimed": "✅ You are recognized as the panel owner.",
        "claim_ask_password": "🔑 Send the panel owner login password to bind your Telegram:",
        "claim_ok": "✅ Your Telegram is now bound to the panel owner. Send /start again.",
        "claim_bad_password": "❌ Wrong password.",
        "promote_ask_target": "👤 Send their numeric Telegram ID, or forward a message from them:",
        "promote_ask_username": "👤 Send their existing panel admin username (the one they use to log in):",
        "promote_ok": "✅ Telegram linked to panel admin.\nUsername: {c}{username}{/c}\nThey can /start with their panel password.",
        "promote_exists": "⚠️ This Telegram is already an admin: {username}",
        "promote_panel_not_found": "❌ No panel admin found with that username.",
        "promote_owner_forbidden": "❌ Owner account cannot be linked here. Owner must use /claim_owner with the panel password.",
        "promote_panel_linked": "⚠️ This panel admin is already linked to another Telegram account.",
        "promote_fail": "❌ Failed to link admin: {error}",
        "admin_shop_home": "🛍 {b}Shop admin{/b}\nEnabled: {enabled}\nCards: {cards}\nWelcome: {welcome}\nCard note: {card_note}\nCard photos: {card_photos}\nTest: {test}\nActive plans: {plans}\nPending orders: {pending}",
        "admin_cards_count": "{count} cards",
        "admin_test_summary": "{data} · {days} days · groups {groups}",
        "admin_test_enabled_on": "✅ Test config enabled",
        "admin_test_enabled_off": "⏸ Test config disabled",
        "admin_ask_test_gb": "🧪 Send test data limit in GB (0 = unlimited):",
        "admin_ask_test_days": "🧪 Send test duration in days (0 = unlimited):",
        "admin_ask_test_groups": "🧪 Send test group IDs comma-separated (e.g. 1,2):",
        "admin_test_saved": "✅ Test config saved",
        "admin_order_approved_by_other": "✅ {b}Order #{id} approved by another admin{/b}\n\n👤 Admin: {c}{admin}{/c}\n🛒 Buyer: {buyer}\n📦 Plan: {plan}\n🔑 User: {c}{username}{/c}",
        "admin_enabled_on": "✅ Shop enabled",
        "admin_enabled_off": "⏸ Shop disabled",
        "admin_ask_card": "💳 Send the card number.\n/done to save · /clear to remove all\nUp to 3 cards",
        "admin_ask_holder": "👤 Send the card holder name:",
        "admin_ask_card_next": "💳 Card {count} of {max} saved.\nSend the next card number or /done:",
        "admin_card_saved": "✅ Saved {count} card(s)",
        "admin_cards_cleared": "🗑 Cards cleared",
        "admin_ask_plan_name": "📦 Send plan name (e.g. 30GB monthly):",
        "admin_ask_plan_gb": "📶 Send data limit in GB (0 = unlimited):",
        "admin_ask_plan_days": "📅 Send duration in days (0 = unlimited):",
        "admin_ask_plan_price": "💰 Send price in Toman:",
        "admin_ask_plan_groups": "👥 Send group IDs comma-separated (e.g. 1,2) or - for none:",
        "admin_ask_plan_ip_limit": "👥 Send concurrent user count (e.g. 2) or - for unlimited:",
        "admin_ask_plan_hwid_limit": "📱 Send device limit:\n• number (e.g. 3) = max devices\n• 0 = no device limit\n• - = panel default",
        "admin_plan_edit": "✏️ {b}Edit plan{/b}: {name}\n\n📶 {data} · 📅 {days} · 💰 {price} T\n👥 Users: {users} · 📱 Devices: {devices}\nGroups: {groups}",
        "admin_plan_updated": "✅ Plan updated",
        "admin_ask_edit_plan_name": "📦 New plan name (current: {current}):",
        "admin_ask_edit_plan_gb": "📶 New data in GB (current: {current}, 0=unlimited):",
        "admin_ask_edit_plan_days": "📅 New days (current: {current}, 0=unlimited):",
        "admin_ask_edit_plan_price": "💰 New price in Toman (current: {current}):",
        "admin_ask_edit_plan_groups": "👥 Groups (current: {current}) — comma-separated or -:",
        "admin_ask_edit_plan_users": "👥 Concurrent users (current: {current}) — number or -:",
        "admin_ask_edit_plan_hwid": "📱 Device limit (current: {current}):\n0=disabled · -=default",
        "btn_edit_plan_name": "📦 Name",
        "btn_edit_plan_gb": "📶 Data",
        "btn_edit_plan_days": "📅 Days",
        "btn_edit_plan_price": "💰 Price",
        "btn_edit_plan_groups": "👥 Groups",
        "btn_edit_plan_users": "👥 Users",
        "btn_edit_plan_hwid": "📱 Devices",
        "btn_toggle_plan": "⏯ Toggle",
        "limit_unlimited": "unlimited",
        "limit_default": "default",
        "limit_disabled": "disabled",
        "admin_plan_created": "✅ Plan created: {name}",
        "admin_plan_toggled": "Plan {name}: {state}",
        "admin_plan_deleted": "🗑 Plan deleted",
        "admin_pending_empty": "No pending orders.",
        "admin_new_order": "🧾 New order #{id}\nBuyer: {buyer}\nPlan: {plan}\nAmount: {price} Toman",
        "admin_approved": "✅ Order approved, user created: {username}",
        "admin_rejected": "❌ Order rejected",
        "btn_enable": "🟢 Enable",
        "btn_disable": "🔴 Disable",
        "btn_set_card": "💳 Cards",
        "btn_test_settings": "🧪 Test settings",
        "btn_toggle_test": "⏯ Toggle test",
        "btn_card_note": "📝 Card note",
        "btn_card_photos": "🖼 Card photos",
        "btn_support": "💬 Support",
        "btn_support_reply": "↩️ Reply",
        "admin_ask_card_note": "📝 Send card section instructions (or - to clear):",
        "admin_ask_welcome": "👋 Send the shop welcome message.\nIt replaces the default home text.\nSend - to restore the default.",
        "admin_welcome_saved": "✅ Welcome message saved",
        "welcome_default_hint": "default",
        "admin_user_joined": "👋 {b}New user joined the bot{/b}\n\n👤 Name: {name}\n📛 Username: {username}\n🆔 ID: {c}{id}{/c}",
        "btn_welcome": "👋 Welcome",
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

(() => {
  "use strict";

  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  const API = "/api/telegram/miniapp";

  const I18N = {
    fa: {
      boot: "در حال آماده‌سازی…",
      bootFail: "باز کردن از داخل تلگرام لازم است",
      hello: "سلام، {name}",
      home: "خانه",
      plans: "پلن‌ها",
      orders: "سفارش‌ها",
      wallet: "کیف پول",
      more: "بیشتر",
      heroTitle: "مرکز کنترل سرویس",
      heroNote: "خرید، تمدید، سفارش‌ها و وضعیت سرور — همه از همین‌جا.",
      welcomeFallback: "به فروشگاه HPXPANEL خوش آمدید.",
      buy: "خرید سرویس",
      renew: "تمدید در بات",
      myOrders: "سفارش‌های من",
      walletTile: "کیف پول",
      status: "وضعیت سرور",
      tutorial: "آموزش",
      referral: "دعوت دوستان",
      support: "پشتیبانی",
      test: "تست رایگان",
      adminPanel: "پنل ادمین",
      openBot: "ادامه در بات",
      continueBuy: "ادامه خرید در بات",
      copy: "کپی",
      copied: "کپی شد",
      emptyPlans: "پلنی فعال نیست.",
      emptyOrders: "هنوز سفارشی ندارید.",
      emptyStatus: "وضعیتی موجود نیست.",
      loading: "در حال بارگذاری…",
      error: "خطا در دریافت اطلاعات",
      days: "{n} روز",
      unlimited: "نامحدود",
      price: "{n} تومان",
      balance: "موجودی",
      hosts: "هاست‌ها",
      pulses: "پالس‌ها",
      cards: "کارت‌های پرداخت",
      refCode: "کد دعوت",
      refLink: "لینک دعوت",
      refReward: "پاداش: {toman} تومان · {gb} گیگ",
      orderPending: "در انتظار",
      orderApproved: "تأیید شده",
      orderRejected: "رد شده",
      paid: "پرداخت‌شده",
      unpaid: "پرداخت نشده",
      shopOff: "فروشگاه فعلاً غیرفعال است.",
      adminHint: "دسترسی ادمین فعال است",
      noTelegram: "این صفحه فقط داخل تلگرام کار می‌کند.",
      retry: "تلاش دوباره",
    },
    en: {
      boot: "Preparing…",
      bootFail: "Open this app from Telegram",
      hello: "Hi, {name}",
      home: "Home",
      plans: "Plans",
      orders: "Orders",
      wallet: "Wallet",
      more: "More",
      heroTitle: "Service control hub",
      heroNote: "Buy, renew, track orders, and check server health — all here.",
      welcomeFallback: "Welcome to the HPXPANEL shop.",
      buy: "Buy service",
      renew: "Renew in bot",
      myOrders: "My orders",
      walletTile: "Wallet",
      status: "Server status",
      tutorial: "Tutorial",
      referral: "Invite friends",
      support: "Support",
      test: "Free test",
      adminPanel: "Admin panel",
      openBot: "Continue in bot",
      continueBuy: "Continue purchase in bot",
      copy: "Copy",
      copied: "Copied",
      emptyPlans: "No active plans.",
      emptyOrders: "No orders yet.",
      emptyStatus: "No status available.",
      loading: "Loading…",
      error: "Failed to load",
      days: "{n} days",
      unlimited: "Unlimited",
      price: "{n} Toman",
      balance: "Balance",
      hosts: "Hosts",
      pulses: "Pulses",
      cards: "Payment cards",
      refCode: "Referral code",
      refLink: "Invite link",
      refReward: "Reward: {toman} Toman · {gb} GB",
      orderPending: "Pending",
      orderApproved: "Approved",
      orderRejected: "Rejected",
      paid: "Paid",
      unpaid: "Unpaid",
      shopOff: "Shop is currently disabled.",
      adminHint: "Admin access enabled",
      noTelegram: "This page only works inside Telegram.",
      retry: "Retry",
    },
  };

  const state = {
    session: null,
    lang: "fa",
    route: "home",
    cache: {},
  };

  const el = {
    boot: document.getElementById("boot"),
    bootSub: document.getElementById("boot-sub"),
    app: document.getElementById("app"),
    view: document.getElementById("view"),
    dock: document.getElementById("dock"),
    hello: document.getElementById("hello"),
    avatar: document.getElementById("avatar"),
    langToggle: document.getElementById("lang-toggle"),
    refresh: document.getElementById("refresh-btn"),
    toast: document.getElementById("toast"),
  };

  function t(key, vars) {
    const dict = I18N[state.lang] || I18N.fa;
    let s = dict[key] || I18N.en[key] || key;
    if (vars) {
      Object.keys(vars).forEach((k) => {
        s = s.replaceAll(`{${k}}`, String(vars[k]));
      });
    }
    return s;
  }

  function fmtPrice(n) {
    const num = Number(n || 0);
    const formatted = num.toLocaleString(state.lang === "fa" ? "fa-IR" : "en-US");
    return t("price", { n: formatted });
  }

  function haptic(type) {
    try {
      if (tg && tg.HapticFeedback) {
        if (type === "success") tg.HapticFeedback.notificationOccurred("success");
        else if (type === "error") tg.HapticFeedback.notificationOccurred("error");
        else tg.HapticFeedback.impactOccurred("light");
      }
    } catch (_) {
      /* ignore */
    }
  }

  let toastTimer = null;
  function toast(msg) {
    el.toast.hidden = false;
    el.toast.textContent = msg;
    el.toast.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      el.toast.classList.remove("is-on");
    }, 2200);
  }

  function initData() {
    if (!tg) return "";
    return tg.initData || "";
  }

  async function api(path, options) {
    const headers = Object.assign(
      { Accept: "application/json" },
      (options && options.headers) || {},
    );
    const raw = initData();
    if (raw) {
      headers["X-Telegram-Init-Data"] = raw;
      headers.Authorization = `tma ${raw}`;
    }
    const res = await fetch(`${API}${path}`, {
      ...options,
      headers,
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  function applyDir() {
    document.documentElement.lang = state.lang;
    document.documentElement.dir = state.lang === "fa" ? "rtl" : "ltr";
    el.langToggle.textContent = state.lang === "fa" ? "EN" : "FA";
  }

  function icon(name) {
    const paths = {
      home: '<path d="M3 11.5 12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-8.5z" stroke-linejoin="round"/>',
      plans:
        '<rect x="4" y="5" width="16" height="14" rx="2"/><path d="M8 9h8M8 13h5"/>',
      orders:
        '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
      wallet:
        '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18M16 14h2"/>',
      more: '<circle cx="6" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="18" cy="12" r="1.5"/>',
      buy: '<path d="M12 5v14M5 12h14"/>',
      renew: '<path d="M4 12a8 8 0 1 0 2.3-5.6"/><path d="M4 4v5h5"/>',
      status: '<path d="M4 19V5M10 19V9M16 19v-6M22 19V7"/>',
      tutorial: '<path d="M4 19V6a2 2 0 0 1 2-2h12v15H6a2 2 0 0 0-2 2z"/><path d="M18 4v15"/>',
      referral: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
      support: '<path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/>',
      test: '<path d="M9 3h6M10 3v6l-4 8a2 2 0 0 0 1.8 3h8.4A2 2 0 0 0 18 17l-4-8V3"/>',
      admin: '<rect x="3" y="4" width="18" height="14" rx="2"/><path d="M3 10h18"/>',
    };
    return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">${paths[name] || ""}</svg>`;
  }

  function openBot(start) {
    const bot = state.session && state.session.bot_username;
    if (!bot) {
      toast(t("error"));
      return;
    }
    const url = start ? `https://t.me/${bot}?start=${encodeURIComponent(start)}` : `https://t.me/${bot}`;
    haptic("light");
    if (tg && tg.openTelegramLink) tg.openTelegramLink(url);
    else window.open(url, "_blank");
  }

  function openExternal(url) {
    if (!url) return;
    haptic("light");
    if (tg && tg.openLink) tg.openLink(url);
    else window.open(url, "_blank");
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      haptic("success");
      toast(t("copied"));
    } catch (_) {
      toast(t("error"));
    }
  }

  function statusBadge(status) {
    const s = String(status || "").toLowerCase();
    if (["online", "ok", "healthy", "up", "active", "approved"].includes(s)) {
      return `<span class="badge ok">${escapeHtml(status)}</span>`;
    }
    if (["pending", "warn", "warning", "degraded", "unknown"].includes(s)) {
      return `<span class="badge warn">${escapeHtml(status)}</span>`;
    }
    if (["offline", "down", "error", "rejected", "bad"].includes(s)) {
      return `<span class="badge bad">${escapeHtml(status)}</span>`;
    }
    return `<span class="badge">${escapeHtml(status || "—")}</span>`;
  }

  function orderLabel(status) {
    const s = String(status || "").toLowerCase();
    if (s === "pending") return t("orderPending");
    if (s === "approved") return t("orderApproved");
    if (s === "rejected") return t("orderRejected");
    return status || "—";
  }

  function escapeHtml(v) {
    return String(v == null ? "" : v)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function setRoute(route) {
    state.route = route;
    renderDock();
    render();
  }

  function features() {
    return (state.session && state.session.features) || {};
  }

  function shop() {
    return (state.session && state.session.shop) || null;
  }

  function dockItems() {
    const f = features();
    const items = [{ id: "home", label: t("home"), icon: "home" }];
    if (f.shop) items.push({ id: "plans", label: t("plans"), icon: "plans" });
    if (f.shop) items.push({ id: "orders", label: t("orders"), icon: "orders" });
    if (f.wallet) items.push({ id: "wallet", label: t("wallet"), icon: "wallet" });
    items.push({ id: "more", label: t("more"), icon: "more" });
    return items.slice(0, 5);
  }

  function renderDock() {
    const items = dockItems();
    el.dock.innerHTML = items
      .map(
        (item) => `
      <button type="button" class="dock-btn${state.route === item.id ? " is-active" : ""}" data-route="${item.id}">
        ${icon(item.icon)}
        <span>${escapeHtml(item.label)}</span>
      </button>`,
      )
      .join("");
    el.dock.querySelectorAll("[data-route]").forEach((btn) => {
      btn.addEventListener("click", () => {
        haptic("light");
        setRoute(btn.getAttribute("data-route"));
      });
    });
  }

  function renderHeader() {
    const user = (state.session && state.session.user) || {};
    const name = user.first_name || user.username || "User";
    el.hello.textContent = t("hello", { name });
    if (user.photo_url) {
      el.avatar.style.backgroundImage = `url("${user.photo_url}")`;
    }
  }

  function tile(opts) {
    return `
      <button type="button" class="tile" data-action="${escapeHtml(opts.action)}">
        <span class="tile-icon ${opts.tone || ""}">${icon(opts.icon)}</span>
        <p class="tile-label">${escapeHtml(opts.label)}</p>
        ${opts.hint ? `<p class="tile-hint">${escapeHtml(opts.hint)}</p>` : ""}
      </button>`;
  }

  function renderHome() {
    const f = features();
    const s = shop();
    const note = (s && s.welcome_note) || t("welcomeFallback");
    const tiles = [];
    if (f.shop) {
      tiles.push(tile({ action: "plans", icon: "buy", tone: "accent", label: t("buy"), hint: "→" }));
      tiles.push(tile({ action: "orders", icon: "orders", label: t("myOrders") }));
      tiles.push(tile({ action: "renew", icon: "renew", label: t("renew") }));
    }
    if (f.wallet) tiles.push(tile({ action: "wallet", icon: "wallet", tone: "accent", label: t("walletTile") }));
    if (f.server_status) tiles.push(tile({ action: "status", icon: "status", label: t("status") }));
    if (f.tutorial) tiles.push(tile({ action: "tutorial", icon: "tutorial", label: t("tutorial") }));
    if (f.referral) tiles.push(tile({ action: "referral", icon: "referral", label: t("referral") }));
    if (f.test) tiles.push(tile({ action: "test", icon: "test", tone: "warn", label: t("test") }));
    tiles.push(tile({ action: "support", icon: "support", label: t("support") }));
    if (f.open_panel) tiles.push(tile({ action: "admin", icon: "admin", tone: "accent", label: t("adminPanel") }));

    el.view.innerHTML = `
      <section class="hero">
        <p class="hero-kicker">HPXPANEL Mini App</p>
        <h2 class="hero-title">${escapeHtml(t("heroTitle"))}</h2>
        <p class="hero-note">${escapeHtml(note || t("heroNote"))}</p>
        ${state.session && state.session.is_admin ? `<p class="muted" style="margin-top:10px">${escapeHtml(t("adminHint"))}</p>` : ""}
      </section>
      ${f.shop || f.admin ? `<div class="grid">${tiles.join("")}</div>` : `<div class="empty">${escapeHtml(t("shopOff"))}</div>`}
    `;

    el.view.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", () => onAction(btn.getAttribute("data-action")));
    });
  }

  async function renderPlans() {
    el.view.innerHTML = `<p class="muted">${escapeHtml(t("loading"))}</p>`;
    try {
      const data = state.cache.plans || (await api("/plans"));
      state.cache.plans = data;
      const plans = data.plans || [];
      if (!plans.length) {
        el.view.innerHTML = `<div class="empty">${escapeHtml(t("emptyPlans"))}</div>`;
        return;
      }
      el.view.innerHTML = `
        <p class="section-title">${escapeHtml(t("plans"))}</p>
        <div class="stack">
          ${plans
            .map((p) => {
              const days = p.expire_days ? t("days", { n: p.expire_days }) : t("unlimited");
              return `
              <button type="button" class="plan" data-plan="${p.id}">
                <div class="plan-top">
                  <p class="plan-name">${escapeHtml(p.name)}</p>
                  <p class="plan-price">${escapeHtml(fmtPrice(p.price_toman))}</p>
                </div>
                <p class="plan-meta">${escapeHtml(p.data_label || "—")} · ${escapeHtml(days)}</p>
              </button>`;
            })
            .join("")}
        </div>
        ${renderCardsBlock()}
        <div style="margin-top:14px">
          <button type="button" class="cta" id="buy-bot">${escapeHtml(t("continueBuy"))}</button>
        </div>`;
      el.view.querySelectorAll("[data-plan]").forEach((btn) => {
        btn.addEventListener("click", () => {
          haptic("light");
          openBot("shop");
        });
      });
      const buy = document.getElementById("buy-bot");
      if (buy) buy.addEventListener("click", () => openBot("shop"));
      wireCopyButtons();
    } catch (err) {
      el.view.innerHTML = errorBlock(err);
    }
  }

  function renderCardsBlock() {
    const cards = (shop() && shop().cards) || [];
    if (!cards.length) return "";
    return `
      <p class="section-title" style="margin-top:18px">${escapeHtml(t("cards"))}</p>
      <div class="stack">
        ${cards
          .map(
            (c) => `
          <div class="card">
            <p class="mono">${escapeHtml(c.number || "")}</p>
            <p class="muted">${escapeHtml(c.holder || "")}</p>
            <button type="button" class="cta ghost" style="margin-top:10px;min-height:40px" data-copy="${escapeHtml(c.number || "")}">${escapeHtml(t("copy"))}</button>
          </div>`,
          )
          .join("")}
      </div>`;
  }

  function wireCopyButtons() {
    el.view.querySelectorAll("[data-copy]").forEach((btn) => {
      btn.addEventListener("click", () => copyText(btn.getAttribute("data-copy") || ""));
    });
  }

  async function renderOrders() {
    el.view.innerHTML = `<p class="muted">${escapeHtml(t("loading"))}</p>`;
    try {
      const data = state.cache.orders || (await api("/orders"));
      state.cache.orders = data;
      const orders = data.orders || [];
      if (!orders.length) {
        el.view.innerHTML = `<div class="empty">${escapeHtml(t("emptyOrders"))}</div>`;
        return;
      }
      el.view.innerHTML = `
        <p class="section-title">${escapeHtml(t("orders"))}</p>
        <div class="stack">
          ${orders
            .map((o) => {
              const badgeClass =
                String(o.status).toLowerCase() === "approved"
                  ? "ok"
                  : String(o.status).toLowerCase() === "rejected"
                    ? "bad"
                    : "warn";
              return `
              <div class="card">
                <div class="plan-top">
                  <p class="plan-name">#${escapeHtml(o.id)} · ${escapeHtml(o.order_kind || "purchase")}</p>
                  <span class="badge ${badgeClass}">${escapeHtml(orderLabel(o.status))}</span>
                </div>
                <p class="plan-meta">${escapeHtml(fmtPrice(o.quoted_price_toman || 0))} · ${escapeHtml(o.payment_paid ? t("paid") : t("unpaid"))}</p>
                ${o.requested_username ? `<p class="mono muted">${escapeHtml(o.requested_username)}</p>` : ""}
              </div>`;
            })
            .join("")}
        </div>`;
    } catch (err) {
      el.view.innerHTML = errorBlock(err);
    }
  }

  async function renderWallet() {
    el.view.innerHTML = `<p class="muted">${escapeHtml(t("loading"))}</p>`;
    try {
      const data = state.cache.wallet || (await api("/wallet"));
      state.cache.wallet = data;
      el.view.innerHTML = `
        <section class="hero">
          <p class="hero-kicker">${escapeHtml(t("balance"))}</p>
          <p class="balance">${escapeHtml(Number(data.balance_toman || 0).toLocaleString(state.lang === "fa" ? "fa-IR" : "en-US"))}</p>
          <p class="muted" style="margin-top:8px">Toman</p>
        </section>
        <button type="button" class="cta secondary" id="wallet-bot">${escapeHtml(t("openBot"))}</button>`;
      document.getElementById("wallet-bot").addEventListener("click", () => openBot("shop"));
    } catch (err) {
      el.view.innerHTML = errorBlock(err);
    }
  }

  async function renderStatus() {
    el.view.innerHTML = `<p class="muted">${escapeHtml(t("loading"))}</p>`;
    try {
      const data = state.cache.status || (await api("/server-status"));
      state.cache.status = data;
      const hosts = data.hosts || [];
      const pulses = data.pulses || [];
      if (!hosts.length && !pulses.length) {
        el.view.innerHTML = `<div class="empty">${escapeHtml(t("emptyStatus"))}</div>`;
        return;
      }
      el.view.innerHTML = `
        ${
          hosts.length
            ? `<p class="section-title">${escapeHtml(t("hosts"))}</p>
               <div class="stack">${hosts
                 .map(
                   (h) => `
                 <div class="status-row">
                   <p class="status-name">${escapeHtml(h.name)}</p>
                   ${statusBadge(h.status)}
                 </div>`,
                 )
                 .join("")}</div>`
            : ""
        }
        ${
          pulses.length
            ? `<p class="section-title" style="margin-top:16px">${escapeHtml(t("pulses"))}</p>
               <div class="stack">${pulses
                 .map(
                   (p) => `
                 <div class="status-row">
                   <p class="status-name">${escapeHtml(p.name)}</p>
                   ${statusBadge(p.status)}
                 </div>`,
                 )
                 .join("")}</div>`
            : ""
        }`;
    } catch (err) {
      el.view.innerHTML = errorBlock(err);
    }
  }

  async function renderReferral() {
    el.view.innerHTML = `<p class="muted">${escapeHtml(t("loading"))}</p>`;
    try {
      const data = await api("/referral");
      el.view.innerHTML = `
        <section class="hero">
          <p class="hero-kicker">${escapeHtml(t("referral"))}</p>
          <h2 class="hero-title">${escapeHtml(data.code || "—")}</h2>
          <p class="hero-note">${escapeHtml(
            t("refReward", {
              toman: Number(data.reward_toman || 0).toLocaleString(state.lang === "fa" ? "fa-IR" : "en-US"),
              gb: data.reward_data_gb || 0,
            }),
          )}</p>
        </section>
        <div class="stack">
          <div class="card">
            <p class="muted">${escapeHtml(t("refCode"))}</p>
            <p class="mono">${escapeHtml(data.code || "")}</p>
            <button type="button" class="cta ghost" style="margin-top:10px;min-height:40px" data-copy="${escapeHtml(data.code || "")}">${escapeHtml(t("copy"))}</button>
          </div>
          ${
            data.link
              ? `<div class="card">
                  <p class="muted">${escapeHtml(t("refLink"))}</p>
                  <p class="mono" style="word-break:break-all">${escapeHtml(data.link)}</p>
                  <button type="button" class="cta ghost" style="margin-top:10px;min-height:40px" data-copy="${escapeHtml(data.link)}">${escapeHtml(t("copy"))}</button>
                </div>`
              : ""
          }
        </div>`;
      wireCopyButtons();
    } catch (err) {
      el.view.innerHTML = errorBlock(err);
    }
  }

  function renderTutorial() {
    const s = shop() || {};
    el.view.innerHTML = `
      <p class="section-title">${escapeHtml(t("tutorial"))}</p>
      <div class="card">
        <p style="white-space:pre-wrap;margin:0">${escapeHtml(s.tutorial_text || t("welcomeFallback"))}</p>
      </div>
      ${
        s.tutorial_url
          ? `<div style="margin-top:12px"><button type="button" class="cta" id="tut-open">${escapeHtml(t("openBot"))}</button></div>`
          : ""
      }`;
    const btn = document.getElementById("tut-open");
    if (btn && s.tutorial_url) btn.addEventListener("click", () => openExternal(s.tutorial_url));
  }

  function renderMore() {
    const f = features();
    const rows = [];
    if (f.server_status) rows.push(tile({ action: "status", icon: "status", label: t("status") }));
    if (f.tutorial) rows.push(tile({ action: "tutorial", icon: "tutorial", label: t("tutorial") }));
    if (f.referral) rows.push(tile({ action: "referral", icon: "referral", label: t("referral") }));
    if (f.test) rows.push(tile({ action: "test", icon: "test", tone: "warn", label: t("test") }));
    rows.push(tile({ action: "support", icon: "support", label: t("support") }));
    if (f.open_panel) rows.push(tile({ action: "admin", icon: "admin", tone: "accent", label: t("adminPanel") }));
    rows.push(tile({ action: "bot", icon: "renew", label: t("openBot") }));

    el.view.innerHTML = `
      <p class="section-title">${escapeHtml(t("more"))}</p>
      <div class="grid">${rows.join("")}</div>`;
    el.view.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", () => onAction(btn.getAttribute("data-action")));
    });
  }

  function errorBlock(err) {
    return `
      <div class="empty">
        <p>${escapeHtml(t("error"))}</p>
        <p class="muted" style="margin-top:8px">${escapeHtml(err && err.message ? err.message : "")}</p>
        <button type="button" class="cta secondary" style="margin-top:14px" id="retry">${escapeHtml(t("retry"))}</button>
      </div>`;
  }

  function onAction(action) {
    haptic("light");
    if (action === "plans") return setRoute("plans");
    if (action === "orders") return setRoute("orders");
    if (action === "wallet") return setRoute("wallet");
    if (action === "status") return setRoute("status");
    if (action === "referral") return setRoute("referral");
    if (action === "tutorial") return setRoute("tutorial");
    if (action === "renew" || action === "test" || action === "support" || action === "bot") {
      return openBot("shop");
    }
    if (action === "admin") {
      const url = state.session && state.session.panel_url;
      if (url) return openExternal(url);
      return openBot();
    }
  }

  function render() {
    renderHeader();
    const route = state.route;
    if (route === "home") return renderHome();
    if (route === "plans") return renderPlans();
    if (route === "orders") return renderOrders();
    if (route === "wallet") return renderWallet();
    if (route === "status") return renderStatus();
    if (route === "referral") return renderReferral();
    if (route === "tutorial") return renderTutorial();
    return renderMore();
  }

  async function boot() {
    el.bootSub.textContent = t("boot");
    if (tg) {
      try {
        tg.ready();
        tg.expand();
        if (tg.setHeaderColor) tg.setHeaderColor("#0f172a");
        if (tg.setBackgroundColor) tg.setBackgroundColor("#0f172a");
      } catch (_) {
        /* ignore */
      }
    }

    if (!initData()) {
      el.bootSub.textContent = t("noTelegram");
      return;
    }

    try {
      const session = await api("/session", { method: "POST" });
      state.session = session;
      state.lang = session.lang === "en" ? "en" : "fa";
      applyDir();
      el.boot.classList.add("is-hidden");
      el.app.hidden = false;
      el.app.classList.remove("is-hidden");
      renderDock();
      render();
    } catch (err) {
      el.bootSub.textContent = (err && err.message) || t("bootFail");
    }
  }

  el.langToggle.addEventListener("click", async () => {
    const next = state.lang === "fa" ? "en" : "fa";
    try {
      await api("/lang", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lang: next }),
      });
      state.lang = next;
      applyDir();
      haptic("success");
      renderDock();
      render();
    } catch (_) {
      toast(t("error"));
    }
  });

  el.refresh.addEventListener("click", async () => {
    state.cache = {};
    haptic("light");
    try {
      state.session = await api("/session", { method: "POST" });
      state.lang = state.session.lang === "en" ? "en" : "fa";
      applyDir();
      renderDock();
      render();
      toast(state.lang === "fa" ? "به‌روز شد" : "Updated");
    } catch (err) {
      toast((err && err.message) || t("error"));
    }
  });

  el.view.addEventListener("click", (e) => {
    const retry = e.target.closest("#retry");
    if (retry) {
      state.cache = {};
      render();
    }
  });

  boot();
})();

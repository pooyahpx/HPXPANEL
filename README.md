<p align="center">
  <img width="88" height="88" alt="HPXPANEL" src="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/dashboard/public/statics/favicon/android-chrome-192x192.png" onerror="this.style.display='none'" />
</p>

<h1 align="center">HPXPANEL</h1>

<p align="center">
  <strong>Command-deck proxy operations console</strong><br/>
  Users · Nodes · Cores · Subscriptions — one sharp control plane.
</p>

<p align="center">
  <a href="https://github.com/pooyahpx/HPXPANEL"><img alt="GitHub" src="https://img.shields.io/badge/github-pooyahpx%2FHPXPANEL-1f6feb?style=flat-square&logo=github" /></a>
  <img alt="UI" src="https://img.shields.io/badge/UI-command%20deck-0ea5e9?style=flat-square" />
  <img alt="Stack" src="https://img.shields.io/badge/stack-FastAPI%20%2B%20React-64748b?style=flat-square" />
</p>

---

## Why HPXPANEL

HPXPANEL is a full proxy management panel with a custom **ops-console** interface — cobalt accents, pixel borders, and mission-style layouts — built for operators who want clarity over clutter.

### Highlights

| Area | What you get |
| --- | --- |
| **Dashboard** | Live resource telemetry, user matrix, quest-style navigation |
| **Users** | Multi-step create wizard, HWID + **IP limiter**, group/template assignment |
| **Nodes & Cores** | Xray / WireGuard / IPsec editors, outbound tooling, core ops |
| **Statistics** | Fullscreen-safe charts, balanced theater grid, realtime traffic |
| **Subscriptions** | User-facing delivery page with usage gauge, metric rail, and traffic chart |

---

## Subscription delivery

End-user subscription pages are redesigned as a compact **user dashboard**:

- Circular usage gauge + remaining traffic
- Lifetime / expiry / last-online telemetry rail
- Protocol-tagged config links with copy & QR
- Usage statistics chart (`1h` → `90d`) fed by the subscription `/usage` API
- HPXPANEL command-deck styling (not a soft clone of other templates)

---

## Stack

- **Backend:** Python · FastAPI · SQLAlchemy · Alembic
- **Frontend:** React · Vite · Tailwind · TanStack Query
- **Cores:** Xray · WireGuard · IPsec / IKEv2 / L2TP support

---

## Quick start

```bash
# Backend
uv sync
uv run alembic upgrade head
uv run main.py

# Dashboard
cd dashboard
bun install
bun run dev
```

Open the panel, then hit a user subscription URL to preview the delivery UI.

---

## Credits

Built and maintained by **[hpx](https://github.com/pooyahpx)**.

Panel architecture descends from the open-source PasarGuard lineage — HPXPANEL is the custom command-deck evolution of that foundation.

---

<p align="center">
  <a href="https://github.com/pooyahpx">dev by hpx</a>
</p>

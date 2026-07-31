---
title: Install from source
description: Run HPXPANEL from the GitHub repository
---

# Install from source

Use this when you want the latest HPXPANEL tree from GitHub.

## Clone

```bash
git clone https://github.com/pooyahpx/HPXPANEL.git
cd HPXPANEL
```

## Backend

Requires [uv](https://github.com/astral-sh/uv).

```bash
uv sync
uv run alembic upgrade head
uv run main.py
```

## Dashboard

Requires [Bun](https://bun.sh/).

```bash
cd dashboard
bun install
bun run dev
```

Dashboard: `http://127.0.0.1:5173/dashboard/`

## Docs site (this site)

```bash
cd docs
bun install
bun run dev
```

## Stack

- Backend: Python, FastAPI, SQLAlchemy, Alembic
- Frontend: React, Vite, Tailwind
- Engines: Xray-core · WireGuard · IPsec (IKEv2 / L2TP)

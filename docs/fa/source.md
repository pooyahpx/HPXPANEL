---
title: نصب از سورس
---

# نصب از سورس

```bash
git clone https://github.com/pooyahpx/HPXPANEL.git
cd HPXPANEL

uv sync
uv run alembic upgrade head
uv run main.py

# ترمینال جدا
cd dashboard && bun install && bun run dev
```

داشبورد: `http://127.0.0.1:5173/dashboard/`

## مستندات

```bash
cd docs && bun install && bun run dev
```

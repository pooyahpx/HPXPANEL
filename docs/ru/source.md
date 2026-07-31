---
title: Из исходников
---

# Из исходников

```bash
git clone https://github.com/pooyahpx/HPXPANEL.git
cd HPXPANEL
uv sync && uv run alembic upgrade head && uv run main.py
cd dashboard && bun install && bun run dev
```

# Contributing to HPXPANEL

**dev by hpx** — thanks for showing up.

HPXPANEL is a command-deck proxy ops console. Contributions should make the panel sharper for operators: clearer UX, stronger protocol coverage (Xray first, plus WireGuard / Hysteria2 / IPsec), and fewer 3am surprises in production.

Repo: [pooyahpx/HPXPANEL](https://github.com/pooyahpx/HPXPANEL)  
Docs: [pooyahpx.github.io/HPXPANEL](https://pooyahpx.github.io/HPXPANEL/)  
Maintainer: [pooyahpx](https://github.com/pooyahpx)

---

## Before you open anything

| You want to… | Do this |
| --- | --- |
| Ask a quick question | Open a [GitHub Discussion / Issue](https://github.com/pooyahpx/HPXPANEL/issues) with context |
| Report a bug | File an issue with the checklist below |
| Ship a change | Branch → PR against `main` |

Skip the formalities. If the PR is useful and clean, it gets reviewed.

---

## Bug reports that actually help

Please include:

1. **What you tried to do**
2. **What broke** (logs / browser console / screenshots)
3. **Relevant config** — `.env` and core JSON with secrets redacted
4. **Environment** — OS, HPXPANEL commit/tag, DB type, Docker or bare metal

Vague “doesn’t work” reports get closed or asked for more detail.

---

## Pull requests

- Prefer a linked issue for non-trivial changes
- One concern per PR when possible
- Match the existing command-deck UI language on frontend work (cobalt accents, readable density — no random redesigns)
- Backend business logic belongs in `app/operation/` — keep routers thin
- Don’t commit secrets, local `.env`, or giant unrelated lockfile churn

### Branching

```text
main   ← production-ready
  └── your-feature-branch
```

Open PRs into `main` unless told otherwise.

---

## Repo map

```text
app/         FastAPI backend, ops layer, DB, routers
cli/         Typer CLI
dashboard/   React command-deck UI
docs/        VitePress docs (EN / FA / RU)
tests/       pytest API tests
```

---

## Local setup

Needs **uv** + **bun**.

```bash
# backend
make setup
make run-migration
make run

# frontend (other terminal / or via make)
make install-front
```

API docs (set `DOCS=true` in `.env`):

- http://localhost:8000/docs  
- http://localhost:8000/redoc  

Docs site:

```bash
cd docs && bun install && bun run dev
```

Debug mode: `DEBUG=true` in `.env` → backend reload + dashboard Vite.

---

## Quality bar

```bash
make check      # backend lint
make format     # backend format
make fformat    # frontend format
make gen-api    # regenerate Orval client after API changes
make test       # pytest
```

Frontend: Tailwind + Shadcn, single-purpose components, no drive-by refactors.

CLI: Typer app under `cli/` — run with `make run-cli`.

---

## What we care about most

- **Xray stack** reliability (VLESS / VMess / Trojan / Shadowsocks / TLS / REALITY)
- **IPsec** (L2TP / IKEv2) when native OS VPN is required
- **Operator UX** — create-user wizard, IP Limiter, subscription delivery page
- **Docs** that sound like HPXPANEL, not a generic panel clone

If your change advances one of those, lead with that in the PR description.

---

Ship something useful.  
**— hpx**

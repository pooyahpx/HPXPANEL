# Contribute to HPXPANEL

Thanks for considering contributing to **HPXPANEL**!

## 🙋 Questions

Please **don’t use GitHub Issues** only for casual questions. Prefer:

-   🗣️ GitHub Discussions / Issues: [pooyahpx/HPXPANEL](https://github.com/pooyahpx/HPXPANEL)
-   👨‍💻 Maintainer: [pooyahpx](https://github.com/pooyahpx)

## 🐞 Reporting Issues

When reporting a bug or issue, please include:

-   ✅ What you expected to happen
-   ❌ What actually happened (include server logs or browser errors)
-   ⚙️ Your `xray` JSON config and `.env` settings (censor sensitive info)
-   🔢 Your HPXPANEL version and Docker version (if applicable)

---

# 🚀 Submitting a Pull Request

If there's no open issue for your idea, consider opening one for discussion **before submitting a PR**.

You can contribute to any issue that:

-   Has no PR linked
-   Has no maintainer assigned

No need to ask for permission!

## 🔀 Branching Strategy

-   Prefer branching off of `main` (or the active development branch)
-   Keep `main` stable and production-ready

---

# 📁 Project Structure

```text
.
├── app          # Backend code (FastAPI - Python)
├── cli          # CLI code (Typer - Python)
├── dashboard    # Frontend code (React Router - TypeScript)
├── docs         # VitePress documentation
└── tests        # API tests
```

---

## ⚙️ Development Setup

The project uses [uv](https://github.com/astral-sh/uv) for Python dependency management and [bun](https://bun.sh/) for frontend dependencies.

### 🐍 Backend Setup

1. Install `uv` if you haven't already.
2. Initialize the virtual environment and install dependencies:
   ```bash
   make setup
   ```
3. Run database migrations:
   ```bash
   make run-migration
   ```
4. Start the application:
   ```bash
   make run
   ```

### 💻 Frontend Setup

1. Install `bun` if you haven't already.
2. Install frontend dependencies:
   ```bash
   make install-front
   ```

---

## 🧠 Backend (FastAPI)

The backend is built with **FastAPI** and **SQLAlchemy**:

-   **Pydantic models**: [`app/models/`](./app/models)
-   **Database structure**: [`app/db/`](./app/db)
    -   SQLAlchemy models: [`app/db/models.py`](./app/db/models.py)
    -   Database CRUD operations: [`app/db/crud/`](./app/db/crud)
    -   Alembic migrations: [`app/db/migrations/`](./app/db/migrations)
-   **Core backend logic**: [`app/operation/`](./app/operation)
-   **API Routers**: [`app/routers/`](./app/routers)

🧩 **Note**: Prefer keeping core backend business logic in the `app/operation` module so routes, DB access, and services stay separated.

### 📘 API Docs (Swagger / ReDoc)

Enable the `DOCS` flag in your `.env` file to access:

-   Swagger UI: http://localhost:8000/docs
-   ReDoc: http://localhost:8000/redoc

### 🎯 Code Formatting & Linting

```bash
make check
make format
```

### 🗃️ Database Migrations

```bash
make run-migration
make check-migrations
```

---

## 💻 Frontend (React + Tailwind)

> ⚠️ **We no longer upload pre-built frontend files.**

The frontend lives in [`dashboard/`](./dashboard) and is built with:

-   **React Router 7 + TypeScript**
-   **Tailwind CSS + Shadcn UI**
-   **Orval** (API client generation)

### 🔄 API Client Generation

```bash
make gen-api
```

### 🎯 Code Formatting

```bash
make fformat
```

### 🧩 Component Guidelines

-   Follow **Tailwind + Shadcn** best practices
-   Keep components **single-purpose**
-   Prioritize **readability** and **maintainability**

---

## 🛠️ HPXPANEL CLI

The CLI is built with [Typer](https://typer.tiangolo.com/).

-   Code: [`cli/`](./cli) and entrypoint [`pasarguard-cli.py`](./pasarguard-cli.py)
-   Run in development:
    ```bash
    make run-cli
    ```

---

## 📚 Docs

```bash
cd docs
bun install
bun run dev
```

Live docs: https://pooyahpx.github.io/HPXPANEL/

---

## 🧪 Testing

```bash
make test
```

---

## 🐛 Debug Mode

Set `DEBUG=true` in `.env`, then:

```bash
make install-front
make run
```

With `DEBUG=true`:

1. Backend runs with Uvicorn reload
2. Frontend Vite dev server starts
3. API client generation can stay in sync

In production (`DEBUG=false`), the backend serves `dashboard/build/` at `/dashboard/` (builds once if missing).

---

Questions? Open an issue on [pooyahpx/HPXPANEL](https://github.com/pooyahpx/HPXPANEL) — **dev by hpx**. Happy contributing! 🚀

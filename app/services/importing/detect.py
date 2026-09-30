"""Detect foreign panel backup / database format (SQLite + SQL dumps)."""

from __future__ import annotations

import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from app.services.importing.sql_dump import DumpEngine, detect_dump_engine
from app.services.importing.types import ImportSource


@dataclass
class ImportArtifact:
    """Resolved input for the importer."""

    source: ImportSource
    kind: str  # sqlite | sql
    path: Path
    engine: DumpEngine | None = None
    warnings: list[str] = field(default_factory=list)


def _sqlite_tables(path: Path) -> set[str]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return {str(r[0]).lower() for r in rows}
    finally:
        conn.close()


def _column_names(path: Path, table: str) -> set[str]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {str(r[1]).lower() for r in rows}
    except sqlite3.Error:
        return set()
    finally:
        conn.close()


def detect_sqlite_source(path: Path) -> ImportSource:
    tables = _sqlite_tables(path)
    if "inbounds" in tables and ("client_traffics" in tables or "clients" in tables):
        if "users" in tables and "proxy_settings" not in _column_names(path, "users"):
            return ImportSource.sanaei
        if "client_traffics" in tables:
            return ImportSource.sanaei
    if "users" in tables and ("groups" in tables or "hosts" in tables):
        cols = _column_names(path, "users")
        if "proxy_settings" in cols or "username" in cols:
            return ImportSource.pasarguard
    if "inbounds" in tables and "settings" in _column_names(path, "inbounds"):
        return ImportSource.sanaei
    return ImportSource.unknown


def _looks_like_sqlite_file(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(16).startswith(b"SQLite format 3")
    except OSError:
        return False


def _sql_name_priority(name: str) -> int:
    lower = name.lower().replace("\\", "/")
    base = Path(lower).name
    if base in {"database.sql", "db_backup.sql"}:
        return 0
    if "/pg_dump/" in f"/{lower}" or lower.startswith("pg_dump/"):
        return 1
    if base.startswith("db-") and base.endswith(".sql"):
        return 1
    if base.endswith(".sql"):
        return 2
    return 9


def _extract_from_zip(zf: zipfile.ZipFile, work_dir: Path) -> list[Path]:
    names = zf.namelist()
    # Prefer SQLite
    for name in names:
        lower = name.lower()
        if lower.endswith((".db", ".sqlite", ".sqlite3")):
            target = work_dir / Path(name).name
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, target.open("wb") as dst:
                dst.write(src.read())
            return [target]

    sql_names = sorted(
        [n for n in names if n.lower().endswith(".sql") and "globals.sql" not in n.lower()],
        key=_sql_name_priority,
    )
    out: list[Path] = []
    for name in sql_names:
        target = work_dir / Path(name).name
        # avoid collisions
        if target.exists():
            target = work_dir / f"{len(out)}_{Path(name).name}"
        with zf.open(name) as src, target.open("wb") as dst:
            dst.write(src.read())
        out.append(target)
        # Prefer single best dump if it's database.sql / db_backup.sql
        if _sql_name_priority(name) == 0:
            return [target]
    return out


def extract_candidate_files(path: Path, work_dir: Path) -> list[Path]:
    """Return candidate DB/SQL files from a path or zip archive."""
    if path.is_dir():
        found: list[Path] = []
        for pattern in ("*.db", "*.sqlite", "*.sqlite3", "*.sql"):
            found.extend(path.rglob(pattern))
        # sqlite first
        found.sort(key=lambda p: (0 if p.suffix.lower() in {".db", ".sqlite", ".sqlite3"} else 1, p.name))
        return found

    if not path.is_file():
        return []

    suffix = path.suffix.lower()
    if suffix in {".db", ".sqlite", ".sqlite3"} or _looks_like_sqlite_file(path):
        return [path]
    if suffix == ".sql":
        return [path]

    if suffix == ".zip" or zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            return _extract_from_zip(zf, work_dir)
    return []


def _detect_sql_source(path: Path) -> tuple[ImportSource, DumpEngine]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    engine = detect_dump_engine(text)
    head = text[:20000].lower()
    # Sanaei almost never ships as SQL dump of client tables this way; treat as PasarGuard
    if "proxy_settings" in head or "users_groups_association" in head or "copy public.users" in head:
        return ImportSource.pasarguard, engine
    if "create table `inbounds`" in head or "insert into `client_traffics`" in head:
        return ImportSource.sanaei, engine
    if engine != DumpEngine.unknown:
        return ImportSource.pasarguard, engine
    return ImportSource.unknown, engine


def resolve_artifact(path: Path, *, explicit: ImportSource | None = None) -> ImportArtifact:
    """Locate and classify the best importable artifact under path."""
    warnings: list[str] = []
    work = Path(tempfile.mkdtemp(prefix="hpx-import-"))
    candidates = extract_candidate_files(path, work)
    if not candidates:
        warnings.append(f"No SQLite or SQL dump found in {path}")
        return ImportArtifact(
            source=explicit or ImportSource.unknown,
            kind="none",
            path=path,
            warnings=warnings,
        )

    # Prefer sqlite candidates
    for cand in candidates:
        if cand.suffix.lower() in {".db", ".sqlite", ".sqlite3"} or _looks_like_sqlite_file(cand):
            detected = detect_sqlite_source(cand)
            source = explicit if explicit and explicit != ImportSource.unknown else detected
            if explicit and explicit != ImportSource.unknown and detected not in {ImportSource.unknown, explicit}:
                warnings.append(f"File looks like {detected.value}, but --source={explicit.value} was forced")
            if detected == ImportSource.unknown and not explicit:
                warnings.append(f"Could not confidently detect panel type for {cand.name}")
            return ImportArtifact(source=source, kind="sqlite", path=cand, warnings=warnings)

    # SQL dumps — pick the one with most relevant content
    best: ImportArtifact | None = None
    best_score = -1
    for cand in candidates:
        if cand.suffix.lower() != ".sql":
            continue
        try:
            text = cand.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        score = 0
        lower = text.lower()
        if "copy " in lower and "users" in lower:
            score += 100
        if "insert into" in lower and "users" in lower:
            score += 80
        if "proxy_settings" in lower:
            score += 40
        if "timescaledb" in lower or "postgresql" in lower:
            score += 10
        if score > best_score:
            detected, engine = _detect_sql_source(cand)
            source = explicit if explicit and explicit != ImportSource.unknown else detected
            best = ImportArtifact(source=source, kind="sql", path=cand, engine=engine, warnings=list(warnings))
            best_score = score

    if best is not None:
        if best.engine == DumpEngine.postgres:
            best.warnings.append("Detected PostgreSQL/TimescaleDB dump — converting rows into HPX")
        elif best.engine == DumpEngine.mysql:
            best.warnings.append("Detected MySQL/MariaDB dump — converting rows into HPX")
        return best

    warnings.append(f"No usable database dump in {path}")
    return ImportArtifact(source=explicit or ImportSource.unknown, kind="none", path=path, warnings=warnings)


def detect_source(path: Path, *, explicit: ImportSource | None = None) -> tuple[ImportSource, Path | None, list[str]]:
    """Backward-compatible helper: returns (source, sqlite_or_sql_path, warnings)."""
    art = resolve_artifact(path, explicit=explicit)
    if art.kind == "none":
        return art.source, None, art.warnings
    return art.source, art.path, art.warnings

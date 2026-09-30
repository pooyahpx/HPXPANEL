"""Parse plain SQL dumps (PostgreSQL/TimescaleDB + MySQL) into table→rows maps."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Any


class DumpEngine(StrEnum):
    postgres = "postgres"  # includes TimescaleDB
    mysql = "mysql"
    unknown = "unknown"


# Tables we care about for PasarGuard / Marzban-lineage imports
INTERESTING_TABLES = frozenset(
    {
        "users",
        "groups",
        "hosts",
        "inbounds",
        "users_groups_association",
        "inbounds_groups_association",
        "admins",
    }
)


_COPY_RE = re.compile(
    r"^COPY\s+(?:(?P<schema>\w+)\.)?(?P<table>\w+)\s*\((?P<cols>[^)]+)\)\s+FROM\s+stdin\s*;?\s*$",
    re.IGNORECASE,
)
_INSERT_PG_RE = re.compile(
    r"^INSERT\s+INTO\s+(?:(?P<schema>\w+)\.)?(?P<table>\w+)\s*\((?P<cols>[^)]+)\)\s*VALUES\s*",
    re.IGNORECASE,
)
_INSERT_MYSQL_RE = re.compile(
    r"^INSERT\s+INTO\s+`?(?P<table>\w+)`?\s*\((?P<cols>[^)]+)\)\s*VALUES\s*",
    re.IGNORECASE,
)


def detect_dump_engine(text: str) -> DumpEngine:
    head = text[:8000]
    if "COPY " in head.upper() and "FROM stdin" in head:
        return DumpEngine.postgres
    if re.search(r"TimescaleDB|PostgreSQL database dump|pg_dump", head, re.IGNORECASE):
        return DumpEngine.postgres
    if re.search(r"MariaDB|MySQL dump|ENGINE=InnoDB|LOCK TABLES", head, re.IGNORECASE):
        return DumpEngine.mysql
    if "INSERT INTO" in head.upper() and ("`" in head or "/*!40" in head):
        return DumpEngine.mysql
    if "INSERT INTO" in head.upper():
        # Ambiguous — try postgres-style first if public. present
        if "INSERT INTO public." in head or "INSERT INTO \"public\"" in head:
            return DumpEngine.postgres
        return DumpEngine.mysql
    return DumpEngine.unknown


def _split_ident_list(cols: str) -> list[str]:
    parts: list[str] = []
    for raw in cols.split(","):
        name = raw.strip().strip("`").strip('"').split(".")[-1]
        if name:
            parts.append(name)
    return parts


def _unescape_copy_field(value: str) -> Any:
    if value == r"\N":
        return None
    # pg_dump escapes: \\ \t \n \r
    out: list[str] = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            mapping = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "\\": "\\"}
            out.append(mapping.get(nxt, nxt))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _parse_copy_block(lines: list[str], start: int, columns: list[str]) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    i = start
    while i < len(lines):
        line = lines[i]
        if line == r"\." or line.strip() == r"\.":
            return rows, i + 1
        # End of copy unexpectedly
        if line.startswith("COPY ") or line.startswith("--") and "Data for Name:" in line:
            return rows, i
        fields = line.split("\t")
        # pad / trim to column count
        if len(fields) < len(columns):
            fields.extend([r"\N"] * (len(columns) - len(fields)))
        row = {columns[j]: _unescape_copy_field(fields[j]) for j in range(len(columns))}
        rows.append(row)
        i += 1
    return rows, i


def _parse_sql_values_tuples(payload: str) -> list[list[Any]]:
    """Parse VALUES (...),(...); into list of value lists."""
    tuples: list[list[Any]] = []
    i = 0
    n = len(payload)
    while i < n:
        while i < n and payload[i] in " \t\r\n,;":
            i += 1
        if i >= n:
            break
        if payload[i] != "(":
            break
        i += 1
        values: list[Any] = []
        while i < n:
            while i < n and payload[i] in " \t\r\n":
                i += 1
            if i >= n:
                break
            if payload[i] == ")":
                i += 1
                tuples.append(values)
                break
            if payload[i] == ",":
                i += 1
                continue
            # NULL
            if payload[i : i + 4].upper() == "NULL" and (i + 4 >= n or payload[i + 4] in ",)"):
                values.append(None)
                i += 4
                continue
            # quoted string
            if payload[i] in {"'", '"'}:
                quote = payload[i]
                i += 1
                buf: list[str] = []
                while i < n:
                    ch = payload[i]
                    if ch == "\\" and quote == "'" and i + 1 < n:
                        # mysql escapes
                        buf.append(payload[i + 1])
                        i += 2
                        continue
                    if ch == quote:
                        # SQL '' escape
                        if i + 1 < n and payload[i + 1] == quote:
                            buf.append(quote)
                            i += 2
                            continue
                        i += 1
                        break
                    buf.append(ch)
                    i += 1
                values.append("".join(buf))
                continue
            # number / bareword (enums, true/false)
            j = i
            while j < n and payload[j] not in ",)":
                j += 1
            token = payload[i:j].strip()
            if token.lower() in {"true", "false"}:
                values.append(token.lower() == "true")
            else:
                try:
                    if "." in token:
                        values.append(float(token))
                    else:
                        values.append(int(token))
                except ValueError:
                    values.append(token)
            i = j
    return tuples


def parse_postgres_dump(text: str) -> dict[str, list[dict[str, Any]]]:
    tables: dict[str, list[dict[str, Any]]] = {t: [] for t in INTERESTING_TABLES}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _COPY_RE.match(line.strip())
        if m:
            table = m.group("table").lower()
            cols = _split_ident_list(m.group("cols"))
            rows, i = _parse_copy_block(lines, i + 1, cols)
            if table in INTERESTING_TABLES:
                tables[table].extend(rows)
            continue

        stripped = line.strip()
        if stripped.upper().startswith("INSERT INTO"):
            # May span multiple lines until ;
            buf = stripped
            while not buf.rstrip().endswith(";") and i + 1 < len(lines):
                i += 1
                buf += " " + lines[i].strip()
            im = _INSERT_PG_RE.match(buf)
            if im:
                table = im.group("table").lower()
                cols = _split_ident_list(im.group("cols"))
                values_part = buf[im.end() :]
                if table in INTERESTING_TABLES:
                    for vals in _parse_sql_values_tuples(values_part):
                        row = {cols[j]: (vals[j] if j < len(vals) else None) for j in range(len(cols))}
                        tables[table].append(row)
            i += 1
            continue
        i += 1
    return {k: v for k, v in tables.items() if v}


def parse_mysql_dump(text: str) -> dict[str, list[dict[str, Any]]]:
    tables: dict[str, list[dict[str, Any]]] = {t: [] for t in INTERESTING_TABLES}
    # Collapse to handle multi-line inserts
    # Process statement by statement ending with ;
    statements: list[str] = []
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("--") or line.startswith("/*") and "INSERT" not in line.upper():
            continue
        buf.append(line)
        if line.rstrip().endswith(";"):
            statements.append(" ".join(buf))
            buf = []
    if buf:
        statements.append(" ".join(buf))

    for stmt in statements:
        s = stmt.strip()
        if not s.upper().startswith("INSERT INTO"):
            continue
        im = _INSERT_MYSQL_RE.match(s)
        if not im:
            # try without backticks via pg regex
            im = _INSERT_PG_RE.match(s)
        if not im:
            continue
        table = im.group("table").lower()
        if table not in INTERESTING_TABLES:
            continue
        cols = _split_ident_list(im.group("cols"))
        values_part = s[im.end() :]
        for vals in _parse_sql_values_tuples(values_part):
            row = {cols[j]: (vals[j] if j < len(vals) else None) for j in range(len(cols))}
            tables[table].append(row)
    return {k: v for k, v in tables.items() if v}


def parse_sql_dump(path: Path) -> tuple[DumpEngine, dict[str, list[dict[str, Any]]]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    engine = detect_dump_engine(text)
    if engine == DumpEngine.postgres:
        return engine, parse_postgres_dump(text)
    if engine == DumpEngine.mysql:
        return engine, parse_mysql_dump(text)
    # last resort: try both
    pg = parse_postgres_dump(text)
    if pg.get("users"):
        return DumpEngine.postgres, pg
    my = parse_mysql_dump(text)
    if my.get("users"):
        return DumpEngine.mysql, my
    return DumpEngine.unknown, {}


def merge_table_maps(*maps: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for m in maps:
        for key, rows in m.items():
            out.setdefault(key, []).extend(rows)
    return out

"""Unit tests for PasarGuard / Sanaei import extractors (no live DB)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.services.importing.detect import detect_source, detect_sqlite_source
from app.services.importing.pasarguard.extract import extract_pasarguard
from app.services.importing.sanaei.extract import extract_sanaei
from app.services.importing.types import ImportSource
from app.services.importing.util import sanitize_username, unique_name


def test_sanitize_username():
    assert sanitize_username("ali@mail.com") == "ali_at_mail.com"
    assert sanitize_username("  ") == "user"


def test_unique_name():
    existing = {"bob"}
    assert unique_name("bob", existing) == "bob_2"
    assert "bob_2" in existing


def _mk_pasarguard_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE groups (id INTEGER PRIMARY KEY, name TEXT, is_disabled INTEGER DEFAULT 0);
        CREATE TABLE inbounds (id INTEGER PRIMARY KEY, tag TEXT);
        CREATE TABLE inbounds_groups_association (inbound_id INTEGER, group_id INTEGER);
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            proxy_settings TEXT,
            status TEXT,
            used_traffic INTEGER,
            data_limit INTEGER,
            expire TEXT,
            note TEXT,
            on_hold_expire_duration INTEGER,
            data_limit_reset_strategy TEXT,
            hwid_limit INTEGER,
            ip_limit INTEGER
        );
        CREATE TABLE users_groups_association (user_id INTEGER, group_id INTEGER);
        CREATE TABLE hosts (
            id INTEGER PRIMARY KEY,
            remark TEXT,
            address TEXT,
            inbound_tag TEXT,
            port INTEGER,
            sni TEXT,
            host TEXT,
            path TEXT,
            security TEXT,
            allowinsecure INTEGER,
            is_disabled INTEGER,
            priority INTEGER
        );
        """
    )
    proxy = json.dumps({"vless": {"id": "11111111-1111-1111-1111-111111111111"}})
    conn.execute(
        "INSERT INTO groups (id, name) VALUES (1, 'vip')",
    )
    conn.execute("INSERT INTO inbounds (id, tag) VALUES (1, 'vless-reality')")
    conn.execute("INSERT INTO inbounds_groups_association VALUES (1, 1)")
    conn.execute(
        "INSERT INTO users (id, username, proxy_settings, status, used_traffic, data_limit, expire, note) "
        "VALUES (1, 'alice', ?, 'active', 2048, 1073741824, NULL, 'pg user')",
        (proxy,),
    )
    conn.execute("INSERT INTO users_groups_association VALUES (1, 1)")
    conn.execute(
        "INSERT INTO hosts (remark, address, inbound_tag, port, sni, host, path, security, priority) "
        "VALUES ('FR', 'fr.example.com', 'vless-reality', 443, 'sni.example', '', '/ws', 'tls', 1)"
    )
    conn.commit()
    conn.close()


def _mk_sanaei_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE inbounds (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            remark TEXT,
            protocol TEXT,
            listen TEXT,
            port INTEGER,
            settings TEXT,
            stream_settings TEXT,
            enable INTEGER
        );
        CREATE TABLE client_traffics (
            id INTEGER PRIMARY KEY,
            inbound_id INTEGER,
            enable INTEGER,
            email TEXT,
            up INTEGER,
            down INTEGER,
            expiry_time INTEGER,
            total INTEGER
        );
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT);
        """
    )
    settings = json.dumps(
        {
            "clients": [
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "email": "bob@test.com",
                    "enable": True,
                    "expiryTime": 0,
                    "totalGB": 0,
                }
            ]
        }
    )
    stream = json.dumps(
        {
            "network": "ws",
            "security": "tls",
            "wsSettings": {"path": "/ws", "headers": {"Host": "cdn.example"}},
            "tlsSettings": {"serverName": "sni.example", "allowInsecure": False},
        }
    )
    conn.execute(
        "INSERT INTO inbounds (id, remark, protocol, listen, port, settings, stream_settings, enable) "
        "VALUES (1, 'WS-TLS', 'vless', '', 443, ?, ?, 1)",
        (settings, stream),
    )
    conn.execute(
        "INSERT INTO client_traffics (inbound_id, enable, email, up, down, expiry_time, total) "
        "VALUES (1, 1, 'bob@test.com', 100, 200, 0, 0)"
    )
    conn.commit()
    conn.close()


def test_detect_and_extract_pasarguard(tmp_path: Path):
    db = tmp_path / "pg.sqlite3"
    _mk_pasarguard_db(db)
    assert detect_sqlite_source(db) == ImportSource.pasarguard
    plan = extract_pasarguard(db)
    assert plan.source == ImportSource.pasarguard
    assert len(plan.users) == 1
    assert plan.users[0].username == "alice"
    assert plan.users[0].used_traffic == 2048
    assert plan.users[0].proxy_settings["vless"]["id"] == "11111111-1111-1111-1111-111111111111"
    assert plan.groups[0].name == "vip"
    assert "vless-reality" in plan.groups[0].inbound_tags
    assert plan.hosts[0].remark == "FR"
    assert plan.hosts[0].address == {"fr.example.com"}


def test_detect_and_extract_sanaei(tmp_path: Path):
    db = tmp_path / "x-ui.db"
    _mk_sanaei_db(db)
    assert detect_sqlite_source(db) == ImportSource.sanaei
    plan = extract_sanaei(db)
    assert plan.source == ImportSource.sanaei
    assert len(plan.users) == 1
    assert plan.users[0].username.startswith("bob")
    assert plan.users[0].used_traffic == 300
    assert plan.users[0].proxy_settings["vless"]["id"] == "22222222-2222-2222-2222-222222222222"
    assert plan.groups
    assert plan.hosts
    assert plan.hosts[0].path == "/ws"


def test_detect_source_zip(tmp_path: Path):
    import zipfile

    db = tmp_path / "x-ui.db"
    _mk_sanaei_db(db)
    zpath = tmp_path / "backup.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.write(db, arcname="etc/x-ui/x-ui.db")
    source, resolved, _warnings = detect_source(zpath)
    assert source == ImportSource.sanaei
    assert resolved is not None
    assert resolved.exists()


def test_postgres_timescale_dump_import(tmp_path: Path):
    from app.services.importing.apply import build_plan
    from app.services.importing.sql_dump import DumpEngine, parse_postgres_dump

    dump = tmp_path / "database.sql"
    dump.write_text(
        """--
-- PostgreSQL database dump
-- Dumped from database version 16 (TimescaleDB)
--

COPY public.groups (id, name, is_disabled) FROM stdin;
1	vip	f
\\.

COPY public.inbounds (id, tag) FROM stdin;
1	vless-reality
\\.

COPY public.inbounds_groups_association (inbound_id, group_id) FROM stdin;
1	1
\\.

COPY public.users (id, username, proxy_settings, status, used_traffic, data_limit, expire, note) FROM stdin;
1	carol	{"vless": {"id": "33333333-3333-3333-3333-333333333333"}}	active	4096	\\N	\\N	from-pg
\\.

COPY public.users_groups_association (user_id, group_id) FROM stdin;
1	1
\\.

COPY public.hosts (id, remark, address, inbound_tag, port, sni, host, path, security, allowinsecure, is_disabled, priority) FROM stdin;
1	DE	de.example.com	vless-reality	443	sni.example	\\N	/ws	tls	\\N	f	1
\\.
""",
        encoding="utf-8",
    )
    tables = parse_postgres_dump(dump.read_text(encoding="utf-8"))
    assert len(tables["users"]) == 1
    assert tables["users"][0]["username"] == "carol"

    from app.services.importing.sql_dump import parse_sql_dump

    eng, tables2 = parse_sql_dump(dump)
    assert eng == DumpEngine.postgres
    assert tables2["users"][0]["username"] == "carol"

    plan = build_plan(dump, source=ImportSource.pasarguard)
    assert plan.source == ImportSource.pasarguard
    assert len(plan.users) == 1
    assert plan.users[0].username == "carol"
    assert plan.users[0].used_traffic == 4096
    assert plan.users[0].proxy_settings["vless"]["id"] == "33333333-3333-3333-3333-333333333333"
    assert plan.groups[0].name == "vip"
    assert "vless-reality" in plan.groups[0].inbound_tags
    assert any("TimescaleDB" in n or "PostgreSQL" in n for n in plan.notes)


def test_mysql_dump_import(tmp_path: Path):
    from app.services.importing.apply import build_plan
    from app.services.importing.sql_dump import DumpEngine, parse_sql_dump

    dump = tmp_path / "db_backup.sql"
    dump.write_text(
        """-- MySQL dump
CREATE TABLE `users` (`id` int, `username` varchar(64));
INSERT INTO `users` (`id`, `username`, `proxy_settings`, `status`, `used_traffic`, `data_limit`, `expire`, `note`) VALUES
(1,'dave','{"vless": {"id": "44444444-4444-4444-4444-444444444444"}}','active',100,NULL,NULL,'from-mysql');
INSERT INTO `groups` (`id`, `name`, `is_disabled`) VALUES (1,'gold',0);
INSERT INTO `inbounds` (`id`, `tag`) VALUES (1,'vmess-ws');
INSERT INTO `inbounds_groups_association` (`inbound_id`, `group_id`) VALUES (1,1);
INSERT INTO `users_groups_association` (`user_id`, `group_id`) VALUES (1,1);
INSERT INTO `hosts` (`id`, `remark`, `address`, `inbound_tag`, `port`, `sni`, `host`, `path`, `security`, `allowinsecure`, `is_disabled`, `priority`) VALUES
(1,'NL','nl.example.com','vmess-ws',443,'sni.example',NULL,'/vmess','tls',NULL,0,1);
""",
        encoding="utf-8",
    )
    eng, tables = parse_sql_dump(dump)
    assert eng == DumpEngine.mysql
    assert tables["users"][0]["username"] == "dave"

    plan = build_plan(dump)
    assert len(plan.users) == 1
    assert plan.users[0].username == "dave"
    assert plan.users[0].used_traffic == 100
    assert plan.users[0].proxy_settings["vless"]["id"] == "44444444-4444-4444-4444-444444444444"

def test_zip_with_pg_dump(tmp_path: Path):
    import zipfile

    from app.services.importing.apply import build_plan

    dump = tmp_path / "database.sql"
    dump.write_text(
        """-- PostgreSQL database dump
COPY public.users (id, username, proxy_settings, status, used_traffic, data_limit, expire, note) FROM stdin;
9	erin	{"vless": {"id": "55555555-5555-5555-5555-555555555555"}}	active	1	\\N	\\N	zip
\\.
""",
        encoding="utf-8",
    )
    zpath = tmp_path / "pg-backup.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.write(dump, arcname="db_dump/database.sql")
    plan = build_plan(zpath)
    assert len(plan.users) == 1
    assert plan.users[0].username == "erin"

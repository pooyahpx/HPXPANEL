"""Apply an ImportPlan into the live HPXPANEL database."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.admin import get_admin, get_owner
from app.db.crud.group import create_group, get_group_by_id
from app.db.crud.host import create_host
from app.db.crud.user import create_user
from app.db.models import Group, ProxyHostFingerprint, ProxyHostSecurity, User
from app.models.group import GroupCreate
from app.models.host import CreateHost
from app.models.proxy import ProxyTable
from app.models.user import UserCreate
from app.services.importing.pasarguard.extract import extract_pasarguard
from app.services.importing.sanaei.extract import extract_sanaei
from app.services.importing.types import (
    ConflictPolicy,
    ImportPlan,
    ImportResult,
    ImportSource,
)
from app.services.importing.util import unique_name

_SECURITY_MAP = {
    "inbound_default": ProxyHostSecurity.inbound_default,
    "tls": ProxyHostSecurity.tls,
    "reality": ProxyHostSecurity.inbound_default,  # Reality is core/inbound-level in HPX
    "none": ProxyHostSecurity.none,
}


def _normalize_proxy_dict(raw: dict) -> dict:
    """Ensure Shadowsocks passwords meet HPX min length before ProxyTable validation."""
    data = dict(raw or {})
    ss = data.get("shadowsocks")
    if isinstance(ss, dict):
        password = str(ss.get("password") or "")
        if 0 < len(password) < 22:
            data["shadowsocks"] = {**ss, "password": password.ljust(22, "0")}
    return data


def build_plan(path: Path, *, source: ImportSource | None = None) -> ImportPlan:
    from app.services.importing.detect import resolve_artifact
    from app.services.importing.pasarguard.extract import plan_from_tables
    from app.services.importing.sql_dump import DumpEngine, parse_sql_dump

    art = resolve_artifact(path, explicit=source)
    if art.kind == "none":
        plan = ImportPlan(source=art.source or ImportSource.unknown)
        plan.warnings.extend(art.warnings)
        plan.warnings.append(
            "Need a SQLite DB (.db/.sqlite3) or SQL dump (.sql / zip with database.sql / pg_dump)."
        )
        return plan

    if art.kind == "sqlite":
        if art.source == ImportSource.pasarguard:
            plan = extract_pasarguard(art.path)
        elif art.source == ImportSource.sanaei:
            plan = extract_sanaei(art.path)
        else:
            plan = ImportPlan(source=ImportSource.unknown)
            plan.warnings.append(f"Unsupported or unknown source for {art.path}")
        plan.warnings.extend(art.warnings)
        return plan

    # SQL dump → always PasarGuard-lineage row extract (Timescale/Postgres/MySQL)
    engine, tables = parse_sql_dump(art.path)
    if not tables.get("users"):
        plan = ImportPlan(source=art.source if art.source != ImportSource.unknown else ImportSource.pasarguard)
        plan.warnings.extend(art.warnings)
        plan.warnings.append(f"No users rows parsed from SQL dump ({art.path.name}, engine={engine.value})")
        return plan

    engine_label = {
        DumpEngine.postgres: "PostgreSQL/TimescaleDB",
        DumpEngine.mysql: "MySQL/MariaDB",
        DumpEngine.unknown: "SQL",
    }.get(engine, "SQL")
    plan = plan_from_tables(
        tables,
        source_note=f"Converted from {engine_label} dump ({art.path.name}) → HPX database",
    )
    if art.source == ImportSource.sanaei:
        plan.warnings.append("Sanaei SQL dumps are experimental; prefer x-ui.db SQLite when possible.")
    plan.warnings.extend(art.warnings)
    return plan


async def _resolve_admin(db: AsyncSession, admin_username: str | None):
    if admin_username:
        admin = await get_admin(db, admin_username, load_users=False, load_usage_logs=False)
        if admin is None:
            raise ValueError(f"Admin '{admin_username}' not found")
        return admin
    owner = await get_owner(db)
    if owner is None:
        raise ValueError("No owner admin found — create an owner first (hpxpanel cli forge-seal)")
    return owner


async def _existing_usernames(db: AsyncSession) -> set[str]:
    rows = (await db.execute(select(User.username))).scalars().all()
    return {str(u) for u in rows}


async def _existing_group_names(db: AsyncSession) -> set[str]:
    rows = (await db.execute(select(Group.name))).scalars().all()
    return {str(n) for n in rows}


async def apply_plan(
    db: AsyncSession,
    plan: ImportPlan,
    *,
    dry_run: bool = True,
    conflict: ConflictPolicy = ConflictPolicy.skip,
    admin_username: str | None = None,
    default_group_id: int | None = None,
    import_hosts: bool = True,
    import_groups: bool = True,
) -> ImportResult:
    result = ImportResult(source=plan.source, dry_run=dry_run)
    result.warnings.extend(plan.warnings)
    result.notes.extend(plan.notes)

    if plan.source == ImportSource.unknown:
        result.errors.append("Unknown import source — pass --source pasarguard|sanaei")
        return result

    admin = await _resolve_admin(db, admin_username)
    existing_users = await _existing_usernames(db)
    existing_groups = await _existing_group_names(db)

    group_name_to_id: dict[str, int] = {}
    if default_group_id is not None:
        g = await get_group_by_id(db, default_group_id, load_users=False, load_inbounds=False)
        if g is None:
            result.errors.append(f"default group id {default_group_id} not found")
            return result
        group_name_to_id[g.name] = g.id

    if import_groups:
        for draft in plan.groups:
            name = draft.name
            if name in existing_groups:
                if dry_run:
                    group_name_to_id[draft.name] = -1
                    continue
                row = (await db.execute(select(Group).where(Group.name == name))).scalar_one_or_none()
                if row:
                    group_name_to_id[draft.name] = row.id
                continue
            if dry_run:
                result.groups_created += 1
                existing_groups.add(name)
                group_name_to_id[draft.name] = -1
                continue
            try:
                tags = draft.inbound_tags or ["imported"]
                created = await create_group(
                    db,
                    GroupCreate(name=name, inbound_tags=tags, is_disabled=draft.is_disabled),
                )
                group_name_to_id[draft.name] = created.id
                existing_groups.add(name)
                result.groups_created += 1
            except Exception as exc:
                result.errors.append(f"group '{name}': {exc}")

    if import_hosts:
        for draft in plan.hosts:
            if not draft.inbound_tag:
                result.warnings.append(f"host '{draft.remark}' skipped — missing inbound_tag")
                continue
            if dry_run:
                result.hosts_created += 1
                continue
            try:
                security = _SECURITY_MAP.get(draft.security, ProxyHostSecurity.inbound_default)
                await create_host(
                    db,
                    CreateHost(
                        remark=draft.remark,
                        address=draft.address or {"CHANGE_ME"},
                        inbound_tag=draft.inbound_tag,
                        port=draft.port,
                        sni=draft.sni or set(),
                        host=draft.host or set(),
                        path=draft.path,
                        security=security,
                        allowinsecure=draft.allowinsecure,
                        is_disabled=draft.is_disabled,
                        priority=draft.priority,
                        fingerprint=ProxyHostFingerprint.none,
                    ),
                )
                result.hosts_created += 1
            except Exception as exc:
                result.errors.append(f"host '{draft.remark}': {exc}")

    for draft in plan.users:
        username = draft.username
        renamed = False
        if username in existing_users:
            if conflict == ConflictPolicy.skip:
                result.users_skipped += 1
                result.skipped_usernames.append(username)
                continue
            username = unique_name(username, existing_users)
            renamed = True
        else:
            existing_users.add(username)

        group_ids: list[int] = []
        for gname in draft.source_group_names:
            gid = group_name_to_id.get(gname)
            if gid and gid > 0:
                group_ids.append(gid)
        if not group_ids and default_group_id is not None:
            group_ids = [default_group_id]

        if dry_run:
            result.users_created += 1
            if renamed:
                result.users_renamed += 1
                result.renamed.append(f"{draft.username}->{username}")
            continue

        try:
            proxy = ProxyTable.model_validate(_normalize_proxy_dict(draft.proxy_settings or {}))
            proxy.wireguard.peer_ips = []
            proxy.wg_c.peer_ips = []

            status = draft.status if draft.status in {"active", "disabled", "on_hold"} else "active"
            new_user = UserCreate(
                username=username,
                status=status,
                proxy_settings=proxy,
                expire=draft.expire,
                data_limit=draft.data_limit,
                note=draft.note,
                on_hold_expire_duration=draft.on_hold_expire_duration,
                group_ids=group_ids,
                hwid_limit=draft.hwid_limit,
                ip_limit=draft.ip_limit,
            )
            groups: list[Group] = []
            for gid in group_ids:
                g = await get_group_by_id(db, gid, load_users=False, load_inbounds=True)
                if g:
                    groups.append(g)

            db_user = await create_user(db, new_user, groups, admin, commit=True)
            if draft.used_traffic and draft.used_traffic > 0:
                await db.execute(
                    update(User).where(User.id == db_user.id).values(used_traffic=int(draft.used_traffic))
                )
                await db.commit()
            result.users_created += 1
            if renamed:
                result.users_renamed += 1
                result.renamed.append(f"{draft.username}->{username}")
        except Exception as exc:
            result.errors.append(f"user '{draft.username}': {exc}")

    if not dry_run and result.users_created:
        result.notes.append("Import finished. Re-issue subscription links to clients.")
    return result

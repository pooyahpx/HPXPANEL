from datetime import UTC, datetime as dt

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminSession


async def create_admin_session(
    db: AsyncSession,
    *,
    admin_id: int,
    jti: str,
    user_agent: str | None = None,
    ip: str | None = None,
) -> AdminSession:
    now = dt.now(UTC)
    session = AdminSession(
        admin_id=admin_id,
        jti=jti,
        user_agent=user_agent[:512] if user_agent else None,
        ip=ip[:64] if ip else None,
        last_seen_at=now,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def get_admin_session_by_jti(db: AsyncSession, jti: str) -> AdminSession | None:
    stmt = select(AdminSession).where(AdminSession.jti == jti).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_active_admin_sessions(db: AsyncSession, admin_id: int) -> list[AdminSession]:
    stmt = (
        select(AdminSession)
        .where(AdminSession.admin_id == admin_id, AdminSession.revoked_at.is_(None))
        .order_by(AdminSession.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def revoke_admin_session(db: AsyncSession, session: AdminSession) -> AdminSession:
    if session.revoked_at is None:
        session.revoked_at = dt.now(UTC)
        await db.flush()
        await db.refresh(session)
    return session


async def revoke_all_admin_sessions(
    db: AsyncSession,
    admin_id: int,
    *,
    except_jti: str | None = None,
) -> int:
    now = dt.now(UTC)
    stmt = (
        update(AdminSession)
        .where(AdminSession.admin_id == admin_id, AdminSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    if except_jti:
        stmt = stmt.where(AdminSession.jti != except_jti)
    result = await db.execute(stmt)
    await db.flush()
    return int(result.rowcount or 0)


async def touch_admin_session(db: AsyncSession, session: AdminSession) -> AdminSession:
    session.last_seen_at = dt.now(UTC)
    await db.flush()
    return session


async def get_admin_session_by_id(db: AsyncSession, session_id: int, admin_id: int) -> AdminSession | None:
    stmt = (
        select(AdminSession)
        .where(AdminSession.id == session_id, AdminSession.admin_id == admin_id)
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()

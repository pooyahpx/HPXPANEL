from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminWebAuthnCredential


async def list_webauthn_credentials(db: AsyncSession, admin_id: int) -> list[AdminWebAuthnCredential]:
    stmt = (
        select(AdminWebAuthnCredential)
        .where(AdminWebAuthnCredential.admin_id == admin_id)
        .order_by(AdminWebAuthnCredential.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def count_webauthn_credentials(db: AsyncSession, admin_id: int) -> int:
    stmt = select(func.count(AdminWebAuthnCredential.id)).where(AdminWebAuthnCredential.admin_id == admin_id)
    return int((await db.execute(stmt)).scalar_one() or 0)


async def get_webauthn_credential_by_credential_id(
    db: AsyncSession, credential_id: str
) -> AdminWebAuthnCredential | None:
    stmt = select(AdminWebAuthnCredential).where(AdminWebAuthnCredential.credential_id == credential_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_webauthn_credential_for_admin(
    db: AsyncSession, *, admin_id: int, credential_pk: int
) -> AdminWebAuthnCredential | None:
    stmt = select(AdminWebAuthnCredential).where(
        AdminWebAuthnCredential.id == credential_pk,
        AdminWebAuthnCredential.admin_id == admin_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_webauthn_credential(
    db: AsyncSession,
    *,
    admin_id: int,
    credential_id: str,
    public_key: str,
    sign_count: int,
    nickname: str,
    transports: list | None = None,
    aaguid: str | None = None,
) -> AdminWebAuthnCredential:
    row = AdminWebAuthnCredential(
        admin_id=admin_id,
        credential_id=credential_id,
        public_key=public_key,
        sign_count=sign_count,
        nickname=nickname[:128] or "Security key",
        transports=transports,
        aaguid=aaguid,
    )
    bind = await db.connection()
    if bind.dialect.name == "sqlite":
        next_id = (await db.execute(select(func.coalesce(func.max(AdminWebAuthnCredential.id), 0) + 1))).scalar_one()
        row.id = int(next_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def touch_webauthn_credential(db: AsyncSession, row: AdminWebAuthnCredential, *, sign_count: int) -> None:
    row.sign_count = sign_count
    row.last_used_at = datetime.now(UTC)
    await db.commit()


async def delete_webauthn_credential(db: AsyncSession, *, admin_id: int, credential_pk: int) -> bool:
    result = await db.execute(
        delete(AdminWebAuthnCredential).where(
            AdminWebAuthnCredential.id == credential_pk,
            AdminWebAuthnCredential.admin_id == admin_id,
        )
    )
    await db.commit()
    return bool(result.rowcount)

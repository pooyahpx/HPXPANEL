import asyncio
from typing import Annotated
from uuid import uuid4

import pyotp
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app import notification
from app.db import AsyncSession, get_db
from app.db.crud.admin import build_admin_details, get_admin_by_id as get_admin_by_id_crud
from app.db.crud.admin_session import (
    create_admin_session,
    get_admin_session_by_id,
    list_active_admin_sessions,
    revoke_admin_session,
    revoke_all_admin_sessions,
)
from app.models.admin import (
    AdminCreate,
    AdminDetails,
    AdminListQuery,
    AdminModify,
    AdminSessionResponse,
    AdminSessionsResponse,
    AdminSimpleListQuery,
    AdminsResponse,
    AdminsSimpleResponse,
    AdminStatus,
    AdminUsageQuery,
    BulkAdminsActionResponse,
    BulkAdminSelection,
    MFAConfirmRequest,
    MFADisableRequest,
    MFATokenRequest,
    RemoveAdminsResponse,
    Token,
    TOTPSetupResponse,
    verify_password,
)
from app.models.stats import UserUsageStatsList
from app.operation import OperatorType
from app.operation.admin import AdminOperation
from app.rate_limit import rate_limiter
from app.utils import responses
from app.utils.crypto import decrypt_secret, encrypt_secret
from app.utils.jwt import (
    create_admin_token,
    create_mfa_challenge_token,
    get_admin_payload,
    get_mfa_challenge_payload,
    get_secret_key,
)
from app.utils.request import get_client_ip
from config import rate_limit_settings

from .authentication import (
    get_current,
    get_current_with_metrics,
    oauth2_scheme,
    require_permission,
    validate_admin,
    validate_mini_app_admin,
)
from .dependencies import get_admin_list_query, get_admin_simple_list_query, get_admin_usage_query

router = APIRouter(tags=["Admin"], prefix="/api/admin", responses={401: responses._401, 403: responses._403})
admin_operator = AdminOperation(operator_type=OperatorType.API)


def _request_user_agent(request: Request) -> str | None:
    ua = request.headers.get("user-agent")
    return ua[:512] if ua else None


async def _issue_admin_token(
    db: AsyncSession,
    *,
    admin_id: int | None,
    username: str,
    request: Request,
) -> Token:
    jti = str(uuid4()) if admin_id is not None else None
    if admin_id is not None and jti is not None:
        await create_admin_session(
            db,
            admin_id=admin_id,
            jti=jti,
            user_agent=_request_user_agent(request),
            ip=get_client_ip(request),
        )
        await db.commit()
    access_token = await create_admin_token(admin_id, username, jti=jti)
    return Token(access_token=access_token)


def _verify_totp_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return bool(totp.verify(code.strip(), valid_window=1))


@router.post("/token", response_model=Token)
async def admin_token(
    request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """Authenticate an admin and issue a token."""
    await rate_limiter.enforce_client_and_identity(
        request,
        "admin-login",
        rate_limit_settings.admin_login_limit,
        rate_limit_settings.admin_login_window,
        identity=form_data.username,
    )
    client_ip = get_client_ip(request)
    db_admin = await validate_admin(db, form_data.username, form_data.password)
    if not db_admin:
        asyncio.create_task(notification.admin_login(form_data.username, client_ip, False))
        raise HTTPException(
            status_code=401, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"}
        )
    if db_admin.status == AdminStatus.disabled:
        asyncio.create_task(notification.admin_login(form_data.username, client_ip, False))
        raise HTTPException(
            status_code=403, detail="your account has been disabled", headers={"WWW-Authenticate": "Bearer"}
        )

    if db_admin.totp_enabled and db_admin.id is not None:
        mfa_token = await create_mfa_challenge_token(db_admin.id, db_admin.username)
        return Token(access_token="", mfa_required=True, mfa_token=mfa_token)

    asyncio.create_task(notification.admin_login(db_admin.username, client_ip, True))
    return await _issue_admin_token(db, admin_id=db_admin.id, username=form_data.username, request=request)


@router.post("/token/mfa", response_model=Token)
async def admin_token_mfa(request: Request, body: MFATokenRequest, db: AsyncSession = Depends(get_db)):
    """Complete MFA challenge and issue a session token."""
    await rate_limiter.enforce_client_and_identity(
        request,
        "admin-mfa",
        rate_limit_settings.admin_login_limit,
        rate_limit_settings.admin_login_window,
        identity=body.mfa_token[:32],
    )
    client_ip = get_client_ip(request)
    challenge = await get_mfa_challenge_payload(body.mfa_token)
    if not challenge:
        raise HTTPException(status_code=401, detail="Invalid or expired MFA token")

    db_admin = await get_admin_by_id_crud(db, challenge["admin_id"], load_users=False, load_usage_logs=False)
    if not db_admin or not db_admin.totp_enabled or not db_admin.totp_secret:
        raise HTTPException(status_code=401, detail="MFA is not available for this admin")

    secret_key = await get_secret_key()
    try:
        totp_secret = decrypt_secret(db_admin.totp_secret, secret_key)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid MFA configuration")

    if not _verify_totp_code(totp_secret, body.code):
        asyncio.create_task(notification.admin_login(db_admin.username, client_ip, False))
        raise HTTPException(status_code=401, detail="Invalid MFA code")

    asyncio.create_task(notification.admin_login(db_admin.username, client_ip, True))
    return await _issue_admin_token(db, admin_id=db_admin.id, username=db_admin.username, request=request)


@router.post("/miniapp/token", responses={409: responses._409})
async def admin_mini_app_token(
    request: Request, x_telegram_authorization: str = Header(), db: AsyncSession = Depends(get_db)
):
    """Authenticate an admin via Telegram MiniApp and issue a token."""
    await rate_limiter.enforce_client_and_identity(
        request,
        "admin-miniapp-login",
        rate_limit_settings.admin_login_limit,
        rate_limit_settings.admin_login_window,
        identity=x_telegram_authorization,
    )
    client_ip = get_client_ip(request)
    db_admin = await validate_mini_app_admin(db, x_telegram_authorization)
    if not db_admin:
        raise HTTPException(status_code=401, detail="admin not found.", headers={"WWW-Authenticate": "Bearer"})
    if db_admin.status == AdminStatus.disabled:
        raise HTTPException(
            status_code=403, detail="your account has been disabled", headers={"WWW-Authenticate": "Bearer"}
        )
    asyncio.create_task(notification.admin_login(db_admin.username, client_ip, True))
    return await _issue_admin_token(db, admin_id=db_admin.id, username=db_admin.username, request=request)


@router.post("/security/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
):
    if admin.id is None:
        raise HTTPException(status_code=400, detail="TOTP is not available for env admins")

    db_admin = await get_admin_by_id_crud(db, admin.id, load_users=False, load_usage_logs=False)
    if not db_admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    if db_admin.totp_enabled:
        raise HTTPException(status_code=409, detail="TOTP is already enabled")

    secret = pyotp.random_base32()
    secret_key = await get_secret_key()
    db_admin.totp_secret = encrypt_secret(secret, secret_key)
    db_admin.totp_enabled = False
    await db.commit()

    otpauth_url = pyotp.TOTP(secret).provisioning_uri(name=db_admin.username, issuer_name="HPXPANEL")
    return TOTPSetupResponse(secret=secret, otpauth_url=otpauth_url)


@router.post("/security/totp/confirm", response_model=AdminDetails)
async def confirm_totp(
    body: MFAConfirmRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
):
    if admin.id is None:
        raise HTTPException(status_code=400, detail="TOTP is not available for env admins")

    db_admin = await get_admin_by_id_crud(db, admin.id, load_users=False, load_usage_logs=False)
    if not db_admin or not db_admin.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP setup has not been started")

    secret_key = await get_secret_key()
    try:
        totp_secret = decrypt_secret(db_admin.totp_secret, secret_key)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid TOTP secret")

    if not _verify_totp_code(totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid MFA code")

    db_admin.totp_enabled = True
    await db.commit()
    await db.refresh(db_admin)
    return build_admin_details(db_admin)


@router.post("/security/totp/disable", response_model=AdminDetails)
async def disable_totp(
    body: MFADisableRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
):
    if admin.id is None:
        raise HTTPException(status_code=400, detail="TOTP is not available for env admins")

    db_admin = await get_admin_by_id_crud(db, admin.id, load_users=False, load_usage_logs=False)
    if not db_admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    if not await verify_password(body.password, db_admin.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password")

    if db_admin.totp_enabled and db_admin.totp_secret:
        secret_key = await get_secret_key()
        try:
            totp_secret = decrypt_secret(db_admin.totp_secret, secret_key)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid TOTP secret")
        if not _verify_totp_code(totp_secret, body.code):
            raise HTTPException(status_code=400, detail="Invalid MFA code")

    db_admin.totp_enabled = False
    db_admin.totp_secret = None
    await db.commit()
    await db.refresh(db_admin)
    return build_admin_details(db_admin)


@router.get("/security/sessions", response_model=AdminSessionsResponse)
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
    token: str | None = Depends(oauth2_scheme),
):
    if admin.id is None:
        return AdminSessionsResponse(sessions=[])

    current_jti = None
    if token:
        payload = await get_admin_payload(token)
        current_jti = payload.get("jti") if payload else None

    sessions = await list_active_admin_sessions(db, admin.id)
    return AdminSessionsResponse(
        sessions=[
            AdminSessionResponse(
                id=session.id,
                user_agent=session.user_agent,
                ip=session.ip,
                created_at=session.created_at,
                last_seen_at=session.last_seen_at,
                current=bool(current_jti and session.jti == current_jti),
            )
            for session in sessions
        ]
    )


@router.delete("/security/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
):
    if admin.id is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session = await get_admin_session_by_id(db, session_id, admin.id)
    if not session or session.revoked_at is not None:
        raise HTTPException(status_code=404, detail="Session not found")

    await revoke_admin_session(db, session)
    await db.commit()
    return {}


@router.delete("/security/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_other_sessions(
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
    token: str | None = Depends(oauth2_scheme),
):
    if admin.id is None:
        return {}

    current_jti = None
    if token:
        payload = await get_admin_payload(token)
        current_jti = payload.get("jti") if payload else None

    await revoke_all_admin_sessions(db, admin.id, except_jti=current_jti)
    await db.commit()
    return {}


@router.post(
    "",
    response_model=AdminDetails,
    status_code=status.HTTP_201_CREATED,
    responses={201: {"description": "Admin created successfully"}, 409: responses._409},
)
async def create_admin(
    new_admin: AdminCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "create")),
):
    """Create a new admin."""
    return await admin_operator.create_admin(db, new_admin=new_admin, admin=admin)


@router.put(
    "/{username}",
    response_model=AdminDetails,
    responses={403: responses._403, 404: responses._404, 409: responses._409},
)
async def modify_admin(
    username: str,
    modified_admin: AdminModify,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminDetails = Depends(require_permission("admins", "update")),
):
    """Modify an existing admin's details."""
    return await admin_operator.modify_admin(
        db, username=username, modified_admin=modified_admin, current_admin=current_admin
    )


@router.put(
    "/by-username/{username}",
    response_model=AdminDetails,
    responses={403: responses._403, 404: responses._404, 409: responses._409},
)
async def modify_admin_by_username(
    username: str,
    modified_admin: AdminModify,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminDetails = Depends(require_permission("admins", "update")),
):
    return await admin_operator.modify_admin(
        db, username=username, modified_admin=modified_admin, current_admin=current_admin
    )


@router.put(
    "/by-id/{admin_id}",
    response_model=AdminDetails,
    responses={403: responses._403, 404: responses._404, 409: responses._409},
)
async def modify_admin_by_id(
    admin_id: int,
    modified_admin: AdminModify,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminDetails = Depends(require_permission("admins", "update")),
):
    return await admin_operator.modify_admin_by_id(
        db, admin_id=admin_id, modified_admin=modified_admin, current_admin=current_admin
    )


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_admin(
    username: str,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminDetails = Depends(require_permission("admins", "delete")),
):
    """Remove an admin from the database."""
    await admin_operator.remove_admin(db, username=username, current_admin=current_admin)
    return {}


@router.delete("/by-username/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_admin_by_username(
    username: str,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminDetails = Depends(require_permission("admins", "delete")),
):
    await admin_operator.remove_admin(db, username=username, current_admin=current_admin)
    return {}


@router.delete("/by-id/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_admin_by_id(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminDetails = Depends(require_permission("admins", "delete")),
):
    await admin_operator.remove_admin_by_id(db, admin_id=admin_id, current_admin=current_admin)
    return {}


@router.get("", response_model=AdminDetails)
def get_current_admin(admin: AdminDetails = Depends(get_current_with_metrics)):
    """Retrieve the current authenticated admin."""
    return admin


@router.get("s", response_model=AdminsResponse)
async def get_admins(
    query: Annotated[AdminListQuery, Depends(get_admin_list_query)],
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "read")),
):
    """Fetch a list of admins with optional filters for pagination and username."""
    return await admin_operator.get_admins(db, query=query, admin=admin)


@router.get(
    "s/simple",
    response_model=AdminsSimpleResponse,
    summary="Get lightweight admin list",
    description="Returns only id and username for admins. Optimized for dropdowns and autocomplete.",
)
async def get_admins_simple(
    query: Annotated[AdminSimpleListQuery, Depends(get_admin_simple_list_query)],
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "read_simple")),
):
    """Get lightweight admin list with only id and username."""
    return await admin_operator.get_admins_simple(db=db, query=query, admin=admin)


@router.get(
    "/{username}/usage",
    response_model=UserUsageStatsList,
    responses={403: responses._403, 404: responses._404},
)
async def get_admin_usage(
    username: str,
    query: Annotated[AdminUsageQuery, Depends(get_admin_usage_query)],
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
):
    """Get admin usage aggregated from user traffic."""
    return await admin_operator.get_admin_usage(db, username=username, admin=admin, query=query)


@router.get(
    "/by-username/{username}/usage",
    response_model=UserUsageStatsList,
    responses={403: responses._403, 404: responses._404},
)
async def get_admin_usage_by_username(
    username: str,
    query: Annotated[AdminUsageQuery, Depends(get_admin_usage_query)],
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "read")),
):
    return await admin_operator.get_admin_usage(db, username=username, admin=admin, query=query)


@router.get(
    "/by-id/{admin_id}/usage",
    response_model=UserUsageStatsList,
    responses={403: responses._403, 404: responses._404},
)
async def get_admin_usage_by_id(
    admin_id: int,
    query: Annotated[AdminUsageQuery, Depends(get_admin_usage_query)],
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "read")),
):
    return await admin_operator.get_admin_usage_by_id(db, admin_id=admin_id, admin=admin, query=query)


@router.post("/{username}/users/disable", responses={404: responses._404})
async def disable_all_active_users(
    username: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "update")),
):
    """Disable all active users under a specific admin."""
    await admin_operator.disable_all_active_users(db, username=username, admin=admin)
    return {}


@router.post("/by-username/{username}/users/disable", responses={404: responses._404})
async def disable_all_active_users_by_username(
    username: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "update")),
):
    await admin_operator.disable_all_active_users(db, username=username, admin=admin)
    return {}


@router.post("/by-id/{admin_id}/users/disable", responses={404: responses._404})
async def disable_all_active_users_by_id(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "update")),
):
    await admin_operator.disable_all_active_users_by_id(db, admin_id=admin_id, admin=admin)
    return {}


@router.post("/{username}/users/activate", responses={404: responses._404})
async def activate_all_disabled_users(
    username: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "update")),
):
    """Activate all disabled users under a specific admin."""
    await admin_operator.activate_all_disabled_users(db, username=username, admin=admin)
    return {}


@router.post("/by-username/{username}/users/activate", responses={404: responses._404})
async def activate_all_disabled_users_by_username(
    username: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "update")),
):
    await admin_operator.activate_all_disabled_users(db, username=username, admin=admin)
    return {}


@router.post("/by-id/{admin_id}/users/activate", responses={404: responses._404})
async def activate_all_disabled_users_by_id(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "update")),
):
    await admin_operator.activate_all_disabled_users_by_id(db, admin_id=admin_id, admin=admin)
    return {}


@router.delete("/{username}/users", responses={403: responses._403, 404: responses._404})
async def remove_all_users(
    username: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "delete")),
):
    """Remove all users under a specific admin."""
    deleted = await admin_operator.remove_all_users(db, username=username, admin=admin)
    return {"detail": f"operation has been successfuly done {deleted} users deleted"}


@router.delete("/by-username/{username}/users", responses={403: responses._403, 404: responses._404})
async def remove_all_users_by_username(
    username: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "delete")),
):
    deleted = await admin_operator.remove_all_users(db, username=username, admin=admin)
    return {"detail": f"operation has been successfuly done {deleted} users deleted"}


@router.delete("/by-id/{admin_id}/users", responses={403: responses._403, 404: responses._404})
async def remove_all_users_by_id(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "delete")),
):
    deleted = await admin_operator.remove_all_users_by_id(db, admin_id=admin_id, admin=admin)
    return {"detail": f"operation has been successfuly done {deleted} users deleted"}


@router.post("/{username}/reset", response_model=AdminDetails, responses={404: responses._404})
async def reset_admin_usage(
    username: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "reset_usage")),
):
    """Resets usage of admin."""
    return await admin_operator.reset_admin_usage(db, username=username, admin=admin)


@router.post("/by-username/{username}/reset", response_model=AdminDetails, responses={404: responses._404})
async def reset_admin_usage_by_username(
    username: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "reset_usage")),
):
    return await admin_operator.reset_admin_usage(db, username=username, admin=admin)


@router.post("/by-id/{admin_id}/reset", response_model=AdminDetails, responses={404: responses._404})
async def reset_admin_usage_by_id(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "reset_usage")),
):
    return await admin_operator.reset_admin_usage_by_id(db, admin_id=admin_id, admin=admin)


@router.post(
    "s/bulk/delete",
    response_model=RemoveAdminsResponse,
    responses={400: responses._400, 403: responses._403, 404: responses._404},
)
async def bulk_delete_admins(
    bulk_admins: BulkAdminSelection,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "delete")),
):
    """Delete selected admins by ID."""
    return await admin_operator.bulk_remove_admins(db, bulk_admins, admin)


@router.post(
    "s/bulk/reset",
    response_model=BulkAdminsActionResponse,
    responses={400: responses._400, 403: responses._403, 404: responses._404},
)
async def bulk_reset_admins_usage(
    bulk_admins: BulkAdminSelection,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "reset_usage")),
):
    """Reset usage for selected admins by ID."""
    return await admin_operator.bulk_reset_admins_usage(db, bulk_admins, admin)


@router.post(
    "s/bulk/disable",
    response_model=BulkAdminsActionResponse,
    responses={400: responses._400, 403: responses._403, 404: responses._404},
)
async def bulk_disable_admins(
    bulk_admins: BulkAdminSelection,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "update")),
):
    """Disable selected admins by ID."""
    return await admin_operator.bulk_set_admins_disabled(db, bulk_admins, admin, is_disabled=True)


@router.post(
    "s/bulk/enable",
    response_model=BulkAdminsActionResponse,
    responses={400: responses._400, 403: responses._403, 404: responses._404},
)
async def bulk_enable_admins(
    bulk_admins: BulkAdminSelection,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "update")),
):
    """Enable selected admins by ID."""
    return await admin_operator.bulk_set_admins_disabled(db, bulk_admins, admin, is_disabled=False)


@router.post(
    "s/bulk/users/disable",
    response_model=BulkAdminsActionResponse,
    responses={400: responses._400, 403: responses._403, 404: responses._404},
)
async def bulk_disable_all_active_users(
    bulk_admins: BulkAdminSelection,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "update")),
):
    """Disable all active users under selected admins."""
    return await admin_operator.bulk_disable_all_active_users_for_admins(db, bulk_admins, admin)


@router.post(
    "s/bulk/users/activate",
    response_model=BulkAdminsActionResponse,
    responses={400: responses._400, 403: responses._403, 404: responses._404},
)
async def bulk_activate_all_disabled_users(
    bulk_admins: BulkAdminSelection,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "update")),
):
    """Activate all disabled users under selected admins."""
    return await admin_operator.bulk_activate_all_disabled_users_for_admins(db, bulk_admins, admin)


@router.delete(
    "s/bulk/users",
    response_model=BulkAdminsActionResponse,
    responses={400: responses._400, 403: responses._403, 404: responses._404},
)
async def bulk_remove_all_users(
    bulk_admins: BulkAdminSelection,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("admins", "delete")),
):
    """Remove all users under selected admins."""
    return await admin_operator.bulk_remove_all_users_for_admins(db, bulk_admins, admin)

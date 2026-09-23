from datetime import datetime as dt
from enum import StrEnum

from pydantic import BaseModel, Field


class BackupStatus(StrEnum):
    idle = "idle"
    running = "running"
    success = "success"
    failed = "failed"


class BackupRemoteSftp(BaseModel):
    enabled: bool = False
    host: str = ""
    port: int = Field(default=22, ge=1, le=65535)
    username: str = ""
    remote_path: str = "/var/backups/hpxpanel"


class BackupConfig(BaseModel):
    auto_enabled: bool = False
    schedule_hours: int = Field(default=24, ge=1, le=168)
    local_retention: int = Field(default=14, ge=1, le=365)
    upload_to_remote: bool = True
    remote: BackupRemoteSftp = Field(default_factory=BackupRemoteSftp)


class BackupManifest(BaseModel):
    id: str
    created_at: dt
    panel_version: str
    database_engine: str
    database_file: str
    size_bytes: int
    sha256: str
    encrypted: bool = False
    remote_uploaded: bool = False
    remote_error: str = ""


class BackupListItem(BaseModel):
    id: str
    created_at: dt
    panel_version: str
    database_engine: str
    size_bytes: int
    sha256: str
    encrypted: bool = False
    remote_uploaded: bool = False
    filename: str


class BackupListResponse(BaseModel):
    items: list[BackupListItem] = Field(default_factory=list)
    status: BackupStatus = BackupStatus.idle
    last_error: str = ""
    last_success_at: dt | None = None
    config: BackupConfig


class BackupRunResponse(BaseModel):
    manifest: BackupManifest
    message: str = ""


class BackupRestoreResponse(BaseModel):
    success: bool
    message: str
    restart_required: bool = True
    dry_run: bool = False
    checks: list[str] = Field(default_factory=list)


class BackupInstallTokenRequest(BaseModel):
    panel_base_url: str | None = None
    database: str = "timescaledb"
    ttl_hours: int = Field(default=72, ge=1, le=168)


class BackupInstallTokenResponse(BaseModel):
    token: str
    backup_id: str
    filename: str
    expires_at: dt
    restore_url: str
    install_command: str
    note: str = (
        "Keep the old panel online until the new server finishes downloading. "
        "Token expires automatically; treat it like a password."
    )


class BackupInstallTokenListItem(BaseModel):
    token: str
    backup_id: str
    filename: str
    created_at: dt | None = None
    expires_at: dt | None = None
    enabled: bool = True
    revoked: bool = False
    consumed: bool = False
    use_count: int = 0
    last_used_at: dt | None = None
    last_used_ip: str | None = None
    last_used_country: str | None = None
    last_used_country_code: str | None = None
    last_used_city: str | None = None
    last_used_isp: str | None = None
    last_used_asn: str | None = None


class BackupInstallTokensResponse(BaseModel):
    items: list[BackupInstallTokenListItem] = Field(default_factory=list)


class BackupInstallTokenUpdate(BaseModel):
    enabled: bool


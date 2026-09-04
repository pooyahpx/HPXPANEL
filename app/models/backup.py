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

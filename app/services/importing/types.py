"""Shared types for foreign-panel → HPXPANEL import."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ImportSource(StrEnum):
    pasarguard = "pasarguard"
    sanaei = "sanaei"
    unknown = "unknown"


class ConflictPolicy(StrEnum):
    skip = "skip"
    rename = "rename"


@dataclass
class ImportUserDraft:
    username: str
    proxy_settings: dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    data_limit: int | None = None
    used_traffic: int = 0
    expire: datetime | None = None
    note: str | None = None
    on_hold_expire_duration: int | None = None
    data_limit_reset_strategy: str | None = None
    hwid_limit: int | None = None
    ip_limit: int | None = None
    source_group_names: list[str] = field(default_factory=list)
    source_inbound_tags: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImportGroupDraft:
    name: str
    inbound_tags: list[str] = field(default_factory=list)
    is_disabled: bool = False
    source_id: int | None = None


@dataclass
class ImportHostDraft:
    remark: str
    address: set[str] = field(default_factory=set)
    inbound_tag: str | None = None
    port: int | None = None
    sni: set[str] = field(default_factory=set)
    host: set[str] = field(default_factory=set)
    path: str | None = None
    security: str = "inbound_default"
    allowinsecure: bool | None = None
    is_disabled: bool = False
    priority: int = 0
    fingerprint: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImportPlan:
    source: ImportSource
    users: list[ImportUserDraft] = field(default_factory=list)
    groups: list[ImportGroupDraft] = field(default_factory=list)
    hosts: list[ImportHostDraft] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class ImportResult:
    source: ImportSource
    dry_run: bool
    users_created: int = 0
    users_skipped: int = 0
    users_renamed: int = 0
    groups_created: int = 0
    hosts_created: int = 0
    skipped_usernames: list[str] = field(default_factory=list)
    renamed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        mode = "dry-run" if self.dry_run else "applied"
        lines = [
            f"source={self.source.value} mode={mode}",
            f"users: created={self.users_created} skipped={self.users_skipped} renamed={self.users_renamed}",
            f"groups_created={self.groups_created} hosts_created={self.hosts_created}",
        ]
        if self.renamed:
            lines.append("renamed: " + ", ".join(self.renamed[:20]))
        if self.skipped_usernames:
            lines.append("skipped: " + ", ".join(self.skipped_usernames[:20]))
        if self.warnings:
            lines.extend(f"warning: {w}" for w in self.warnings[:30])
        if self.notes:
            lines.extend(f"note: {n}" for n in self.notes[:20])
        if self.errors:
            lines.extend(f"error: {e}" for e in self.errors[:30])
        return lines

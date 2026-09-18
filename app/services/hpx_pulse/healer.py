"""Rule-based auto-heal for HPX Pulse reverse tunnels (no LLM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime as dt, timedelta as td
from enum import Enum

from app.db.models import HpxPulse, HpxPulseStatus
from app.utils.logger import get_logger

logger = get_logger("hpx-pulse-healer")

HEAL_COOLDOWN = td(minutes=5)
HEAL_MAX_PER_HOUR = 3
AGENT_STALE_SECONDS = 180
STUCK_PARTIAL_SECONDS = 300


class PulseHealAction(str, Enum):
    none = "none"
    restart_both = "restart_both"
    restart_iran = "restart_iran"
    restart_abroad = "restart_abroad"
    sync_both = "sync_both"
    unstuck_partial = "unstuck_partial"


@dataclass
class PulseHealIssue:
    code: str
    message: str
    suggested_action: PulseHealAction


@dataclass
class PulseHealResult:
    issues: list[PulseHealIssue] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    repaired: bool = False
    skipped_reason: str | None = None
    marked_unhealthy: bool = False


def _aware(value: dt | None) -> dt | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _agent_stale(last_seen: dt | None, *, threshold: int = AGENT_STALE_SECONDS) -> bool:
    seen = _aware(last_seen)
    if seen is None:
        return True
    return (dt.now(UTC) - seen).total_seconds() > threshold


def _reset_heal_window_if_stale(pulse: HpxPulse) -> None:
    last = _aware(pulse.last_heal_at)
    if last and dt.now(UTC) - last >= td(hours=1):
        pulse.heal_count_window = 0


def _heal_allowed(pulse: HpxPulse) -> tuple[bool, str | None]:
    if not pulse.auto_heal_enabled:
        return False, "auto-heal disabled"
    _reset_heal_window_if_stale(pulse)
    now = dt.now(UTC)
    last = _aware(pulse.last_heal_at)
    if last and now - last < HEAL_COOLDOWN:
        return False, "cooldown active"
    if (pulse.heal_count_window or 0) >= HEAL_MAX_PER_HOUR:
        return False, "hourly heal limit reached"
    return True, None


def diagnose_pulse(pulse: HpxPulse) -> list[PulseHealIssue]:
    issues: list[PulseHealIssue] = []
    iran_claimed = bool(pulse.iran_agent_key_hash)
    abroad_claimed = bool(pulse.abroad_agent_key_hash)

    if pulse.status == HpxPulseStatus.partial and pulse.last_status_change:
        age = (dt.now(UTC) - _aware(pulse.last_status_change)).total_seconds()  # type: ignore[arg-type]
        if age > STUCK_PARTIAL_SECONDS:
            issues.append(
                PulseHealIssue(
                    "stuck_partial",
                    f"Pulse stuck partial for {int(age)}s — one side missing",
                    PulseHealAction.unstuck_partial,
                )
            )

    if iran_claimed and _agent_stale(pulse.iran_agent_last_seen):
        issues.append(
            PulseHealIssue(
                "iran_agent_stale",
                "Iran agent heartbeat is stale",
                PulseHealAction.restart_iran,
            )
        )

    if abroad_claimed and _agent_stale(pulse.abroad_agent_last_seen):
        issues.append(
            PulseHealIssue(
                "abroad_agent_stale",
                "Abroad agent heartbeat is stale",
                PulseHealAction.restart_abroad,
            )
        )

    if (
        pulse.status == HpxPulseStatus.unhealthy
        and iran_claimed
        and abroad_claimed
        and not any(i.code.endswith("_stale") for i in issues)
    ):
        issues.append(
            PulseHealIssue(
                "path_unhealthy",
                pulse.message or "User path reported unhealthy",
                PulseHealAction.restart_both,
            )
        )

    if pulse.status == HpxPulseStatus.error and (iran_claimed or abroad_claimed):
        issues.append(
            PulseHealIssue(
                "pulse_error",
                pulse.message or "Pulse in error state",
                PulseHealAction.sync_both,
            )
        )

    return issues


def apply_heal_commands(pulse: HpxPulse, action: PulseHealAction) -> list[str]:
    taken: list[str] = []
    if (
        action in {PulseHealAction.restart_both, PulseHealAction.restart_iran, PulseHealAction.unstuck_partial}
        and pulse.iran_agent_key_hash
    ):
        pulse.iran_agent_command = "restart"
        taken.append("queued iran restart")
    if (
        action in {PulseHealAction.restart_both, PulseHealAction.restart_abroad, PulseHealAction.unstuck_partial}
        and pulse.abroad_agent_key_hash
    ):
        pulse.abroad_agent_command = "restart"
        taken.append("queued abroad restart")
    if action == PulseHealAction.sync_both and pulse.iran_agent_key_hash:
        pulse.iran_agent_command = "sync"
        taken.append("queued iran sync")
    if action == PulseHealAction.sync_both and pulse.abroad_agent_key_hash:
        pulse.abroad_agent_command = "sync"
        taken.append("queued abroad sync")
    return taken


def evaluate_and_repair(pulse: HpxPulse, *, auto: bool = True) -> PulseHealResult:
    result = PulseHealResult(issues=diagnose_pulse(pulse))
    now = dt.now(UTC)
    pulse.last_health_check = now

    iran_claimed = bool(pulse.iran_agent_key_hash)
    abroad_claimed = bool(pulse.abroad_agent_key_hash)

    # Panel-side stale watchdog: mark unhealthy when claimed agents go silent.
    if pulse.enabled and pulse.status not in {
        HpxPulseStatus.stopped,
        HpxPulseStatus.stopping,
        HpxPulseStatus.pending_claim,
    }:
        stale_parts: list[str] = []
        if iran_claimed and _agent_stale(pulse.iran_agent_last_seen):
            stale_parts.append("Iran agent silent")
        if abroad_claimed and _agent_stale(pulse.abroad_agent_last_seen):
            stale_parts.append("Abroad agent silent")
        if stale_parts and pulse.status != HpxPulseStatus.unhealthy:
            pulse.status = HpxPulseStatus.unhealthy
            pulse.message = "; ".join(stale_parts)
            pulse.last_status_change = now
            result.marked_unhealthy = True

    if not result.issues:
        return result

    if not auto:
        return result

    allowed, reason = _heal_allowed(pulse)
    if not allowed:
        result.skipped_reason = reason
        return result

    stale_codes = {i.code for i in result.issues}
    if "iran_agent_stale" in stale_codes and "abroad_agent_stale" in stale_codes:
        action = PulseHealAction.restart_both
    else:
        priority = [
            PulseHealAction.restart_both,
            PulseHealAction.sync_both,
            PulseHealAction.restart_iran,
            PulseHealAction.restart_abroad,
            PulseHealAction.unstuck_partial,
        ]
        action = PulseHealAction.none
        for candidate in priority:
            if any(i.suggested_action == candidate for i in result.issues):
                action = candidate
                break
        if action == PulseHealAction.none:
            action = result.issues[0].suggested_action

    taken = apply_heal_commands(pulse, action)
    if not taken:
        result.skipped_reason = "no agents to command"
        return result

    pulse.last_heal_at = now
    pulse.last_heal_action = action.value
    pulse.heal_count_window = (pulse.heal_count_window or 0) + 1
    pulse.message = f"Auto-heal: {action.value} ({', '.join(i.code for i in result.issues)})"
    pulse.last_status_change = now
    result.actions_taken = taken
    result.repaired = True
    logger.info("Pulse %s healed with %s: %s", pulse.name, action.value, taken)
    return result

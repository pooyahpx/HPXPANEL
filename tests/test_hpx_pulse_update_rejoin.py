"""Editing a Pulse must tear the running tunnel down (leave + new tokens), not just restart it."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.db.models import HpxPulseStatus
from app.models.hpx_pulse import HpxPulseUpdate
from app.operation import hpx_pulse as pulse_op
from app.operation.hpx_pulse import HARD_CHANGE_MESSAGE, HpxPulseOperation
from app.services.hpx_pulse.config_linker import rewrite_host_ip_change
from app.utils.crypto import hash_api_key

OLD_IRAN = "10.0.0.1"
OLD_ABROAD = "20.0.0.2"
NEW_IRAN = "10.0.0.99"


class FakeDb:
    def __init__(self):
        self.commits = 0

    async def flush(self):
        return None

    async def refresh(self, _obj):
        return None

    async def commit(self):
        self.commits += 1


class FakePulse:
    """Plain attribute bag with everything `_to_response` and the update flow touch."""

    def __init__(self, **overrides):
        self.id = 7
        self.name = "pulse_a"
        self.status = HpxPulseStatus.running
        self.enabled = True
        self.engine = "hpx"
        self.profile_id = "pulse-reverse-tcp-stealth"
        self.goal = "balanced"
        self.tunnel_mode = "reverse_tcp"
        self.carrier = None
        self.preset = "balance"
        self.token_encrypted = "old-token-cipher"
        self.iran_public_ip = OLD_IRAN
        self.abroad_public_ip = OLD_ABROAD
        self.control_port = 9067
        self.local_ip_iran = "10.10.0.1/30"
        self.local_ip_abroad = "10.10.0.2/30"
        self.port_forwards = ["443"]
        self.domain = None
        self.sni_hint = None
        self.advice_json = None
        self.note = None
        self.iran_join_token_hash = None
        self.iran_join_token_expires_at = None
        self.abroad_join_token_hash = None
        self.abroad_join_token_expires_at = None
        self.iran_agent_key_hash = hash_api_key("iran-agent-key")
        self.abroad_agent_key_hash = hash_api_key("abroad-agent-key")
        self.iran_agent_claimed_at = datetime.now(UTC)
        self.abroad_agent_claimed_at = datetime.now(UTC)
        self.iran_agent_last_seen = None
        self.abroad_agent_last_seen = None
        self.iran_agent_host = "iran-host"
        self.abroad_agent_host = "abroad-host"
        self.iran_agent_command = None
        self.abroad_agent_command = None
        self.latency_ms = None
        self.packet_loss_pct = None
        self.message = "HPX tunnel active"
        self.last_status_change = None
        self.auto_restart_interval_minutes = None
        self.last_auto_restart_at = None
        self.auto_heal_enabled = True
        self.last_heal_at = None
        self.last_heal_action = None
        self.last_health_check = None
        self.backup_pulse_id = None
        self.auto_failover = False
        self.auto_failback = True
        self.failover_active = False
        self.priority = 0
        self.last_failover_at = None
        self.diag_report = None
        self.created_at = datetime.now(UTC)
        for key, value in overrides.items():
            setattr(self, key, value)


class FakeHost:
    def __init__(self, id, address, port=443):
        self.id = id
        self.remark = f"host{id}"
        self.address = address
        self.port = port


@pytest.fixture
def harness(monkeypatch):
    state = SimpleNamespace(pulse=FakePulse(), hosts=[], refreshed=[], peers=[])

    async def fake_get_by_id(_db, pulse_id):
        return state.pulse if pulse_id == state.pulse.id else None

    async def fake_update(_db, db_pulse, data):
        for key, value in data.items():
            setattr(db_pulse, key, value)
        return db_pulse

    async def fake_get_pulses(_db, **_kwargs):
        return [state.pulse, *state.peers], 1 + len(state.peers)

    async def fake_get_hosts(_db):
        return state.hosts

    async def fake_add_hosts(_db, hosts):
        state.refreshed.extend(hosts)

    async def fake_panel_url(_self, request_base=None):
        return "https://panel.example.test"

    async def fake_encrypt(_self, _db, token):
        return f"enc::{token}"

    async def fake_iran_cmds(_self, panel_url, token):
        return f"curl iran {token}", f"curl iran-alt {token}"

    monkeypatch.setattr(pulse_op, "get_hpx_pulse_by_id", fake_get_by_id)
    monkeypatch.setattr(pulse_op, "update_hpx_pulse", fake_update)
    monkeypatch.setattr(pulse_op, "get_hpx_pulses", fake_get_pulses)
    monkeypatch.setattr(pulse_op, "get_hosts", fake_get_hosts)
    monkeypatch.setattr(pulse_op.host_manager, "add_hosts", fake_add_hosts)
    monkeypatch.setattr(HpxPulseOperation, "_panel_url", fake_panel_url)
    monkeypatch.setattr(HpxPulseOperation, "_encrypt_token", fake_encrypt)
    monkeypatch.setattr(HpxPulseOperation, "_iran_join_commands", fake_iran_cmds)
    state.op = HpxPulseOperation.__new__(HpxPulseOperation)
    state.db = FakeDb()
    return state


async def _update(state, **fields):
    return await state.op.update_pulse(
        state.db,
        admin=SimpleNamespace(),
        pulse_id=state.pulse.id,
        model=HpxPulseUpdate(**fields),
        panel_url="https://panel.example.test",
    )


@pytest.mark.asyncio
async def test_iran_ip_change_disconnects_agents_and_rotates_everything(harness):
    state = harness
    pulse = state.pulse
    old_cipher = pulse.token_encrypted
    old_iran_key, old_abroad_key = pulse.iran_agent_key_hash, pulse.abroad_agent_key_hash
    state.hosts = [
        FakeHost(1, {OLD_IRAN}),
        FakeHost(2, {OLD_ABROAD}),
        FakeHost(3, {"203.0.113.9"}),
    ]

    res = await _update(state, iran_public_ip=NEW_IRAN)

    # IP is persisted
    assert pulse.iran_public_ip == NEW_IRAN
    assert res.pulse.iran_public_ip == NEW_IRAN
    # new tunnel token => old tunnel can't authenticate any more
    assert pulse.token_encrypted != old_cipher
    assert pulse.token_encrypted.startswith("enc::")
    # agents are told to leave (NOT restart) and keep their keys until the leave ack
    assert pulse.iran_agent_command == "leave"
    assert pulse.abroad_agent_command == "leave"
    assert pulse.iran_agent_key_hash == old_iran_key
    assert pulse.abroad_agent_key_hash == old_abroad_key
    # join tokens rotated and returned for the wizard
    assert pulse.iran_join_token_hash == hash_api_key(res.iran_join_token)
    assert pulse.abroad_join_token_hash == hash_api_key(res.abroad_join_token)
    assert pulse.iran_join_token_expires_at and pulse.abroad_join_token_expires_at
    assert res.iran_join_command and res.abroad_join_command
    assert res.iran_join_expires_at and res.abroad_join_expires_at
    # status/message
    assert pulse.status == HpxPulseStatus.pending_claim
    assert pulse.message == HARD_CHANGE_MESSAGE
    assert res.message.startswith(HARD_CHANGE_MESSAGE)
    # hosts: old iran + old abroad -> new iran, unrelated host untouched
    assert state.hosts[0].address == {NEW_IRAN}
    assert state.hosts[1].address == {NEW_IRAN}
    assert state.hosts[2].address == {"203.0.113.9"}
    assert {h.id for h in state.refreshed} == {1, 2}
    assert state.db.commits == 1


@pytest.mark.asyncio
async def test_unclaimed_pulse_gets_new_tokens_without_leave(harness):
    state = harness
    pulse = state.pulse
    pulse.iran_agent_key_hash = None
    pulse.abroad_agent_key_hash = None

    res = await _update(state, control_port=9100)

    assert pulse.control_port == 9100
    assert pulse.iran_agent_command is None
    assert pulse.abroad_agent_command is None
    assert res.iran_join_token and res.abroad_join_token


@pytest.mark.asyncio
async def test_rotate_keeps_agent_keys_and_never_queues_start(harness):
    state = harness
    pulse = state.pulse
    key_i, key_a = pulse.iran_agent_key_hash, pulse.abroad_agent_key_hash

    await state.op._rotate_join_tokens_keep_agents(state.db, pulse, panel_url=None)

    assert pulse.iran_agent_key_hash == key_i
    assert pulse.abroad_agent_key_hash == key_a
    assert pulse.iran_agent_command is None
    assert pulse.abroad_agent_command is None
    assert pulse.iran_join_token_hash and pulse.abroad_join_token_hash


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fields",
    [
        {"note": "hello"},
        {"auto_restart_interval_minutes": 30},
        {"auto_heal_enabled": False},
        {"auto_failover": True, "priority": 5},
        {"enabled": False},
    ],
)
async def test_soft_update_does_not_leave_or_rotate(harness, fields):
    state = harness
    pulse = state.pulse
    old_cipher = pulse.token_encrypted

    res = await _update(state, **fields)

    assert pulse.token_encrypted == old_cipher
    assert pulse.iran_agent_command is None
    assert pulse.abroad_agent_command is None
    assert pulse.iran_join_token_hash is None
    assert pulse.abroad_join_token_hash is None
    assert res.iran_join_token is None
    assert res.message == "Pulse updated"
    assert pulse.status == HpxPulseStatus.running
    assert state.refreshed == []


@pytest.mark.asyncio
async def test_echoing_unchanged_hard_fields_is_not_a_hard_change(harness):
    state = harness
    pulse = state.pulse
    old_cipher = pulse.token_encrypted

    res = await _update(
        state,
        iran_public_ip=f" {OLD_IRAN} ",
        abroad_public_ip=OLD_ABROAD,
        control_port=9067,
        port_forwards=["443"],
        profile_id=None,
        note="only this changed",
    )

    assert pulse.token_encrypted == old_cipher
    assert pulse.iran_agent_command is None
    assert res.iran_join_token is None


@pytest.mark.asyncio
async def test_soft_update_does_not_override_pending_leave(harness):
    state = harness
    state.pulse.iran_agent_command = "leave"
    state.pulse.abroad_agent_command = "leave"

    await _update(state, name="renamed_pulse")

    assert state.pulse.iran_agent_command == "leave"
    assert state.pulse.abroad_agent_command == "leave"


@pytest.mark.asyncio
async def test_regenerate_queues_leave_new_token_and_keeps_keys(harness):
    state = harness
    pulse = state.pulse
    old_cipher = pulse.token_encrypted
    key_i, key_a = pulse.iran_agent_key_hash, pulse.abroad_agent_key_hash

    res = await state.op.regenerate_tokens(
        state.db, admin=SimpleNamespace(), pulse_id=pulse.id, panel_url="https://panel.example.test"
    )

    assert pulse.token_encrypted != old_cipher
    assert pulse.iran_agent_command == "leave"
    assert pulse.abroad_agent_command == "leave"
    assert pulse.iran_agent_key_hash == key_i
    assert pulse.abroad_agent_key_hash == key_a
    assert pulse.status == HpxPulseStatus.pending_claim
    assert pulse.iran_join_token_hash == hash_api_key(res.iran_join_token)


@pytest.mark.asyncio
async def test_iran_ip_change_leaves_sibling_pulse_hosts_alone(harness):
    state = harness
    sibling = FakePulse(id=8, name="pulse_b", iran_public_ip="10.0.0.50", port_forwards=["8443"])
    state.peers = [sibling]
    state.hosts = [
        FakeHost(1, {OLD_IRAN}),
        FakeHost(2, {"10.0.0.50", OLD_ABROAD}, port=8443),
    ]

    await _update(state, iran_public_ip=NEW_IRAN)

    assert state.hosts[0].address == {NEW_IRAN}
    # sibling Pulse owns this Host (its Iran IP + forward port): untouched
    assert state.hosts[1].address == {"10.0.0.50", OLD_ABROAD}


def test_rewrite_host_ip_change_replaces_old_iran_and_abroad_but_not_protected():
    out = rewrite_host_ip_change(
        {OLD_IRAN, OLD_ABROAD, "85.1.1.1", "9.9.9.9"},
        old_iran=OLD_IRAN,
        old_abroad=OLD_ABROAD,
        new_iran=NEW_IRAN,
        protected_iran_ips={"85.1.1.1"},
    )
    assert out == {NEW_IRAN, "85.1.1.1", "9.9.9.9"}

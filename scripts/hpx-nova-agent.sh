#!/usr/bin/env bash
# HPX Nova agent — NEVER touches Pulse (hpx-pulse-agent / hpx-tunnel-engine).
set -euo pipefail

PANEL_URL="${PANEL_URL:-}"
JOIN_TOKEN="${JOIN_TOKEN:-}"
SIDE="${SIDE:-}"
STATE_DIR="${HPX_NOVA_STATE_DIR:-/var/lib/hpx-nova}"
CONF_DIR="${HPX_NOVA_CONF_DIR:-/etc/hpx-nova}"
RUN_DIR="${HPX_NOVA_RUN_DIR:-/run/hpx-nova}"
ENGINE_BIN="${HPX_NOVA_ENGINE_BIN:-/usr/local/bin/hpx-nova-tunnel-engine}"
UNIT_NAME="hpx-nova-tunnel-engine"
AGENT_KEY_FILE="${STATE_DIR}/agent.key"
SIDE_FILE="${STATE_DIR}/side"
NOVA_ID_FILE="${STATE_DIR}/nova_id"
CONF_FILE="${CONF_DIR}/config.toml"

log() { echo "[hpx-nova-agent] $*"; }
die() { log "ERROR: $*"; exit 1; }

need_root() { [[ "$(id -u)" -eq 0 ]] || die "run as root"; }

api() {
  local method="$1" path="$2"
  shift 2
  curl --http1.1 -fsS -X "$method" \
    -H "Content-Type: application/json" \
    -H "X-HPX-Nova-Side: ${SIDE}" \
    -H "X-HPX-Nova-Agent-Key: $(cat "$AGENT_KEY_FILE" 2>/dev/null || true)" \
    "$@" \
    "${PANEL_URL%/}${path}"
}

install_engine() {
  local script_url="${PANEL_URL%/}/api/hpx_nova/agent/engine-install.sh"
  log "Installing HPX NOVA TUNNEL ENGINE"
  curl --http1.1 -fsSL "$script_url" | env PANEL_URL="$PANEL_URL" bash
  [[ -x "$ENGINE_BIN" ]] || die "engine binary missing at $ENGINE_BIN"
}

write_unit() {
  cat >"/etc/systemd/system/${UNIT_NAME}.service" <<EOF
[Unit]
Description=HPX NOVA TUNNEL ENGINE
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${ENGINE_BIN} -c ${CONF_FILE}
Restart=always
RestartSec=3
LimitNOFILE=1048576
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_RAW
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_RAW

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
}

start_engine() {
  write_unit
  systemctl enable --now "$UNIT_NAME"
}

stop_engine() {
  systemctl stop "$UNIT_NAME" 2>/dev/null || true
  systemctl disable "$UNIT_NAME" 2>/dev/null || true
}

apply_config() {
  local toml="$1"
  mkdir -p "$CONF_DIR" "$RUN_DIR" "$STATE_DIR"
  printf '%s' "$toml" >"$CONF_FILE"
  chmod 600 "$CONF_FILE"
}

claim() {
  [[ -n "$PANEL_URL" && -n "$JOIN_TOKEN" && -n "$SIDE" ]] || die "PANEL_URL, JOIN_TOKEN, SIDE required"
  [[ "$SIDE" == "iran" || "$SIDE" == "abroad" ]] || die "SIDE must be iran or abroad"
  need_root
  mkdir -p "$STATE_DIR" "$CONF_DIR" "$RUN_DIR"
  install_engine
  local host
  host="$(hostname -f 2>/dev/null || hostname || echo unknown)"
  local payload
  payload="$(curl --http1.1 -fsS -X POST \
    -H "Content-Type: application/json" \
    -d "{\"join_token\":\"${JOIN_TOKEN}\",\"side\":\"${SIDE}\",\"host\":\"${host}\"}" \
    "${PANEL_URL%/}/api/hpx_nova/agent/claim")"
  local agent_key nova_id config_toml
  agent_key="$(printf '%s' "$payload" | sed -n 's/.*"agent_key"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
  nova_id="$(printf '%s' "$payload" | sed -n 's/.*"nova_id"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' | head -1)"
  [[ -n "$agent_key" && -n "$nova_id" ]] || die "claim failed"
  printf '%s' "$agent_key" >"$AGENT_KEY_FILE"
  printf '%s' "$SIDE" >"$SIDE_FILE"
  printf '%s' "$nova_id" >"$NOVA_ID_FILE"
  chmod 600 "$AGENT_KEY_FILE"
  # Extract config_toml with python if available (handles escapes); else jq.
  if command -v python3 >/dev/null 2>&1; then
    config_toml="$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin)["config_toml"])')"
  elif command -v jq >/dev/null 2>&1; then
    config_toml="$(printf '%s' "$payload" | jq -r .config_toml)"
  else
    die "python3 or jq required to parse claim response"
  fi
  apply_config "$config_toml"
  start_engine
  log "Nova #${nova_id} claimed on side=${SIDE}"
  loop
}

ack() {
  local cmd="$1"
  curl --http1.1 -fsS -X POST \
    -H "Content-Type: application/json" \
    -H "X-HPX-Nova-Side: ${SIDE}" \
    -H "X-HPX-Nova-Agent-Key: $(cat "$AGENT_KEY_FILE")" \
    -d "{\"command\":\"${cmd}\"}" \
    "${PANEL_URL%/}/api/hpx_nova/agent/ack" >/dev/null || true
}

sync_once() {
  [[ -f "$AGENT_KEY_FILE" && -f "$SIDE_FILE" ]] || die "not claimed"
  SIDE="$(cat "$SIDE_FILE")"
  local host
  host="$(hostname -f 2>/dev/null || hostname || echo unknown)"
  local cfg
  cfg="$(curl --http1.1 -fsS \
    -H "X-HPX-Nova-Side: ${SIDE}" \
    -H "X-HPX-Nova-Agent-Key: $(cat "$AGENT_KEY_FILE")" \
    "${PANEL_URL%/}/api/hpx_nova/agent/config")"
  local toml cmd enabled
  if command -v python3 >/dev/null 2>&1; then
    toml="$(printf '%s' "$cfg" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("config_toml") or "")')"
    cmd="$(printf '%s' "$cfg" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("command") or "")')"
    enabled="$(printf '%s' "$cfg" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("1" if d.get("enabled", True) else "0")')"
  else
    die "python3 required"
  fi
  [[ -n "$toml" ]] && apply_config "$toml"
  case "$cmd" in
    start|restart)
      start_engine
      ack "$cmd"
      ;;
    leave|stop)
      stop_engine
      ack "$cmd"
      ;;
  esac
  if [[ "$enabled" == "0" ]]; then
    stop_engine
  fi
  curl --http1.1 -fsS -X POST \
    -H "Content-Type: application/json" \
    -H "X-HPX-Nova-Side: ${SIDE}" \
    -H "X-HPX-Nova-Agent-Key: $(cat "$AGENT_KEY_FILE")" \
    -d "{\"host\":\"${host}\",\"status\":\"ok\"}" \
    "${PANEL_URL%/}/api/hpx_nova/agent/heartbeat" >/dev/null || true
}

loop() {
  log "heartbeat loop started"
  while true; do
    sync_once || log "sync failed (will retry)"
    sleep 20
  done
}

status() {
  systemctl --no-pager --full status "$UNIT_NAME" || true
  [[ -x "$ENGINE_BIN" ]] && "$ENGINE_BIN" --version 2>/dev/null || true
  [[ -f "$NOVA_ID_FILE" ]] && log "nova_id=$(cat "$NOVA_ID_FILE") side=$(cat "$SIDE_FILE" 2>/dev/null || echo ?)"
}

usage() {
  cat <<EOF
HPX Nova agent (isolated from Pulse)

Usage:
  JOIN_TOKEN=... SIDE=iran|abroad PANEL_URL=https://panel bash $0
  $0 sync
  $0 status
  $0 install-engine
EOF
}

cmd="${1:-}"
if [[ -z "$cmd" && -n "${JOIN_TOKEN:-}" ]]; then
  claim
  exit 0
fi
case "$cmd" in
  ""|join|claim) claim ;;
  sync) need_root; SIDE="$(cat "$SIDE_FILE" 2>/dev/null || true)"; sync_once ;;
  status) status ;;
  install-engine) need_root; [[ -n "$PANEL_URL" ]] || die "PANEL_URL required"; install_engine ;;
  loop) need_root; SIDE="$(cat "$SIDE_FILE")"; loop ;;
  -h|--help|help) usage ;;
  *) usage; exit 1 ;;
esac

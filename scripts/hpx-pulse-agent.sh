#!/usr/bin/env bash
#
# HPX Pulse Agent — installs BackPack L3 config from panel advisor
#
# Iran:
#   curl -fsSL .../hpx-pulse-agent.sh | sudo bash -s -- join TOKEN --panel-url URL --side iran
# Abroad:
#   curl -fsSL .../hpx-pulse-agent.sh | sudo bash -s -- join TOKEN --panel-url URL --side abroad
#
set -euo pipefail

if [ "${1:-}" = "@" ]; then shift; fi

INSTALL_DIR="${INSTALL_DIR:-/opt/hpx-pulse}"
ETC_DIR="${ETC_DIR:-/etc/hpx-pulse}"
ENV_FILE="$ETC_DIR/agent.env"
BIN_LINK="${BIN_LINK:-/usr/local/bin/hpx-pulse-agent}"
SERVICE_NAME="${SERVICE_NAME:-hpx-pulse-agent}"
TIMER_NAME="${TIMER_NAME:-hpx-pulse-agent.timer}"
BACKPACK_INSTALL="bash <(curl -fsSL https://raw.githubusercontent.com/AminMGMT/BackPack/main/install.sh)"

log()  { echo "[+] $*" >&2; }
warn() { echo "[!] $*" >&2; }
die()  { echo "[x] $*" >&2; exit 1; }
has()  { command -v "$1" >/dev/null 2>&1; }

need_root() { [ "$(id -u)" -eq 0 ] || die "run as root (sudo)"; }

fix_hostname_resolution() {
  local hn short
  hn="$(hostname 2>/dev/null || true)"
  [ -n "$hn" ] || return 0
  short="${hn%%.*}"
  if ! grep -Eq "(^|[[:space:]])${hn}([[:space:]]|$)" /etc/hosts 2>/dev/null; then
    echo "127.0.1.1 ${hn}" >> /etc/hosts
  fi
  if [ "$short" != "$hn" ] && ! grep -Eq "(^|[[:space:]])${short}([[:space:]]|$)" /etc/hosts 2>/dev/null; then
    echo "127.0.1.1 ${short}" >> /etc/hosts
  fi
}

ensure_deps() {
  fix_hostname_resolution
  has curl || die "curl required"
  if ! has docker; then
    warn "Docker missing — installing via get.docker.com"
    curl -fsSL https://get.docker.com | sh
  fi
  docker info >/dev/null 2>&1 || die "docker daemon not running"
  if ! has jq; then
    apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq jq >/dev/null 2>&1 || \
      dnf install -y -q jq >/dev/null 2>&1 || die "install jq"
  fi
}

install_self() {
  mkdir -p "$INSTALL_DIR" "$ETC_DIR"
  if [ -f "${BASH_SOURCE[0]:-}" ] && [ -r "${BASH_SOURCE[0]:-}" ] && [ "${BASH_SOURCE[0]:-}" != "bash" ]; then
    cp "${BASH_SOURCE[0]}" "$INSTALL_DIR/hpx-pulse-agent.sh" 2>/dev/null || true
  fi
  if [ ! -s "$INSTALL_DIR/hpx-pulse-agent.sh" ]; then
    curl -fsSL "https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-pulse-agent.sh" \
      -o "$INSTALL_DIR/hpx-pulse-agent.sh"
  fi
  chmod 755 "$INSTALL_DIR/hpx-pulse-agent.sh"
  ln -sfn "$INSTALL_DIR/hpx-pulse-agent.sh" "$BIN_LINK"
}

write_env() {
  cat >"$ENV_FILE" <<EOF
PANEL_URL=${PANEL_URL:-}
AGENT_KEY=${AGENT_KEY:-}
PULSE_SIDE=${PULSE_SIDE:-}
PULSE_ID=${PULSE_ID:-}
CONFIG_HASH=${CONFIG_HASH:-}
EOF
  chmod 600 "$ENV_FILE"
}

load_env() {
  [ -f "$ENV_FILE" ] || die "agent not configured"
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
}

api() {
  local method="$1" path="$2" body="${3:-}"
  local url="${PANEL_URL%/}${path}"
  local args=(-fsSL -X "$method" -H "X-HPX-Pulse-Agent-Key: ${AGENT_KEY}" -H "X-HPX-Pulse-Side: ${PULSE_SIDE}" -H "Accept: application/json")
  [ -n "$body" ] && args+=(-H "Content-Type: application/json" -d "$body")
  curl "${args[@]}" "$url"
}

ensure_backpack() {
  if has backpack; then
    return 0
  fi
  log "Installing BackPack (one-time)..."
  eval "$BACKPACK_INSTALL" </dev/null || die "BackPack install failed"
  has backpack || die "backpack binary not found after install"
}

apply_backpack_toml() {
  local toml="$1"
  local cfg="/etc/backpack/l3-pulse-${PULSE_ID:-0}.toml"
  mkdir -p /etc/backpack
  printf '%s\n' "$toml" >"$cfg"
  chmod 600 "$cfg"
  log "wrote BackPack config $cfg"
  # BackPack reads per-tunnel service; operator starts via backpack CLI
  if backpack --help 2>&1 | grep -qi l3; then
    :
  fi
  systemctl restart "backpack-l3-pulse-${PULSE_ID:-0}" 2>/dev/null || \
    systemctl restart backpack 2>/dev/null || \
    warn "start BackPack manually: sudo backpack (Manage → start tunnel)"
}

install_systemd() {
  cat >"/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=HPX Pulse Agent sync
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=$BIN_LINK sync
Nice=10

[Install]
WantedBy=multi-user.target
EOF
  cat >"/etc/systemd/system/${TIMER_NAME}" <<EOF
[Unit]
Description=HPX Pulse Agent timer

[Timer]
OnBootSec=15s
OnUnitActiveSec=30s
Unit=${SERVICE_NAME}.service

[Install]
WantedBy=timers.target
EOF
  systemctl daemon-reload
  systemctl enable --now "$TIMER_NAME" >/dev/null
}

cmd_join() {
  need_root
  ensure_deps
  local token="" panel_url="" side=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --panel-url) panel_url="${2:-}"; shift 2 ;;
      --panel-url=*) panel_url="${1#*=}"; shift ;;
      --side) side="${2:-}"; shift 2 ;;
      --side=*) side="${1#*=}"; shift ;;
      -*) die "unknown flag $1" ;;
      *) token="$1"; shift ;;
    esac
  done
  [ -n "$token" ] && [ -n "$panel_url" ] && [ -n "$side" ] || die "usage: join TOKEN --panel-url URL --side iran|abroad"
  [ "$side" = "iran" ] || [ "$side" = "abroad" ] || die "side must be iran or abroad"

  PANEL_URL="${panel_url%/}"
  PULSE_SIDE="$side"
  local host body claim
  host="$(hostname -f 2>/dev/null || hostname)"
  body=$(jq -nc --arg t "$token" --arg h "$host" --arg s "$side" '{join_token:$t, host:$h, side:$s}')

  log "claiming pulse token (${side})..."
  claim=$(curl -fsSL -X POST -H "Content-Type: application/json" -d "$body" \
    "${PANEL_URL}/api/hpx_pulse/agent/claim") || die "claim failed"

  AGENT_KEY=$(echo "$claim" | jq -r '.agent_key')
  PULSE_ID=$(echo "$claim" | jq -r '.pulse_id')
  CONFIG_HASH=$(echo "$claim" | jq -r '.config_hash')
  [ -n "$AGENT_KEY" ] && [ "$AGENT_KEY" != "null" ] || die "missing agent_key"

  install_self
  write_env
  ensure_backpack
  apply_backpack_toml "$(echo "$claim" | jq -r '.backpack_toml')"
  install_systemd

  api POST "/api/hpx_pulse/agent/ack" \
    "$(jq -nc '{command:"start", status:"running", message:"pulse joined"}')" >/dev/null || true
  log "Pulse agent ready (${side}) pulse_id=${PULSE_ID}"
}

cmd_sync() {
  need_root
  load_env
  ensure_backpack
  local cfg hash toml command
  cfg=$(api GET "/api/hpx_pulse/agent/config")
  hash=$(echo "$cfg" | jq -r '.config_hash')
  command=$(echo "$cfg" | jq -r '.agent_command // empty')
  toml=$(echo "$cfg" | jq -r '.backpack_toml')

  if [ "$hash" != "${CONFIG_HASH:-}" ]; then
    apply_backpack_toml "$toml"
    CONFIG_HASH="$hash"
    write_env
  fi

  if [ "$command" = "start" ] || [ "$command" = "restart" ]; then
    apply_backpack_toml "$toml"
    api POST "/api/hpx_pulse/agent/ack" \
      "$(jq -nc --arg c "$command" '{command:$c, status:"running", message:"sync applied"}')" >/dev/null || true
  fi

  local running="false"
  has backpack && running="true"
  api POST "/api/hpx_pulse/agent/heartbeat" \
    "$(jq -nc --arg s "running" --arg h "$(hostname -f 2>/dev/null || hostname)" \
      --argjson br "$running" '{status:$s, host:$h, backpack_running:$br}')" >/dev/null || true
}

cmd_status() {
  load_env 2>/dev/null || true
  echo "panel : ${PANEL_URL:-not set}"
  echo "side  : ${PULSE_SIDE:-?}"
  echo "pulse : ${PULSE_ID:-?}"
  has backpack && backpack --version 2>/dev/null || echo "backpack: not installed"
}

usage() {
  cat <<EOF
HPX Pulse Agent
  join TOKEN --panel-url URL --side iran|abroad
  sync | status
EOF
}

main() {
  local cmd="${1:-status}"
  shift || true
  case "$cmd" in
    join) cmd_join "$@" ;;
    sync) cmd_sync ;;
    status) cmd_status ;;
    -h|--help|help) usage ;;
    *) die "unknown: $cmd" ;;
  esac
}

main "$@"

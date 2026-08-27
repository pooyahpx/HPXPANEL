#!/usr/bin/env bash
#
# HPX Pulse Agent — deploys HPX tunnel config from panel advisor (Direct L3 or Reverse)
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
TUNNEL_SERVICE="${TUNNEL_SERVICE:-hpx-pulse-tunnel}"
ENGINE_INSTALL_URL="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-tunnel-engine-install.sh"
ENGINE_BIN="${ENGINE_BIN:-/usr/local/bin/hpx-tunnel-engine}"

log()  { echo "[HPX Pulse] $*" >&2; }
warn() { echo "[HPX Pulse !] $*" >&2; }
die()  { echo "[HPX Pulse x] $*" >&2; exit 1; }
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
TUNNEL_CFG=${TUNNEL_CFG:-}
TUNNEL_MODE=${TUNNEL_MODE:-direct_l3}
CONTROL_PORT=${CONTROL_PORT:-}
IRAN_PUBLIC_IP=${IRAN_PUBLIC_IP:-}
ABROAD_PUBLIC_IP=${ABROAD_PUBLIC_IP:-}
EOF
  chmod 600 "$ENV_FILE"
}

load_env() {
  [ -f "$ENV_FILE" ] || die "agent not configured — run join first"
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

ensure_engine() {
  if [ -x "$ENGINE_BIN" ]; then
    return 0
  fi
  if [ -x /usr/local/bin/backpack ] && [ ! -x "$ENGINE_BIN" ]; then
    ln -sf /usr/local/bin/backpack "$ENGINE_BIN"
    return 0
  fi
  log "Installing HPX tunnel engine (one-time)..."
  bash <(curl -fsSL "$ENGINE_INSTALL_URL") || die "HPX tunnel engine install failed"
  [ -x "$ENGINE_BIN" ] || die "HPX tunnel engine binary missing after install"
}

engine_bin() {
  if [ -x "$ENGINE_BIN" ]; then
    echo "$ENGINE_BIN"
    return
  fi
  if [ -x /usr/local/bin/backpack ]; then
    ln -sf /usr/local/bin/backpack "$ENGINE_BIN" 2>/dev/null || true
    echo "$ENGINE_BIN"
    return
  fi
  die "HPX tunnel engine not installed"
}

tunnel_cfg_path() {
  echo "${ETC_DIR}/l3-pulse-${PULSE_ID:-0}.toml"
}

tunnel_iface_up() {
  ip link show bp0 2>/dev/null | grep -qE 'state (UP|UNKNOWN)' || return 1
}

tunnel_service_active() {
  systemctl is-active --quiet "${TUNNEL_SERVICE}.service" 2>/dev/null
}

tunnel_port_listening() {
  local port="${CONTROL_PORT:-}"
  [ -n "$port" ] || return 1
  if has ss; then
    ss -tlnH "sport = :${port}" 2>/dev/null | grep -q .
    return $?
  fi
  if has netstat; then
    netstat -tln 2>/dev/null | grep -q ":${port} "
    return $?
  fi
  return 1
}

tunnel_link_up() {
  case "${TUNNEL_MODE:-direct_l3}" in
    direct_l3)
      tunnel_iface_up
      ;;
    reverse_*)
      if [ "${PULSE_SIDE:-}" = "iran" ]; then
        tunnel_port_listening
      else
        tunnel_service_active
      fi
      ;;
    *)
      tunnel_service_active
      ;;
  esac
}

install_tunnel_systemd() {
  local cfg="$1"
  local engine_bin
  engine_bin="$(engine_bin)"
  cat >"/etc/systemd/system/${TUNNEL_SERVICE}.service" <<EOF
[Unit]
Description=HPX Pulse tunnel
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${engine_bin} -c ${cfg}
Restart=always
RestartSec=5
Nice=-5

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable "${TUNNEL_SERVICE}.service" >/dev/null
  systemctl restart "${TUNNEL_SERVICE}.service"
}

apply_tunnel_config() {
  local toml="$1"
  local cfg
  cfg="$(tunnel_cfg_path)"
  mkdir -p "$ETC_DIR"
  printf '%s\n' "$toml" >"$cfg"
  chmod 600 "$cfg"
  TUNNEL_CFG="$cfg"
  log "wrote HPX tunnel config $cfg"
  install_tunnel_systemd "$cfg"
  sleep 2
  if tunnel_service_active; then
    log "HPX tunnel service started"
  else
    warn "HPX tunnel service not active yet — check: systemctl status ${TUNNEL_SERVICE}"
  fi
}

install_agent_systemd() {
  cat >"/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=HPX Pulse Agent sync
After=network-online.target docker.service ${TUNNEL_SERVICE}.service
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

# TCP connect RTT in ms (reverse tunnels — ICMP is often blocked on VPS).
measure_tcp_ms() {
  local host="$1" port="$2"
  [ -n "$host" ] && [ -n "$port" ] || return 1
  if has python3; then
    python3 -c "
import socket, time
s = socket.socket(); s.settimeout(3.0)
t = time.time()
try:
    s.connect(('$host', int('$port')))
    print(f'{(time.time() - t) * 1000:.1f}')
except Exception:
    pass
finally:
    s.close()
" 2>/dev/null
    return 0
  fi
  if has python; then
    python -c "
import socket, time
s = socket.socket(); s.settimeout(3.0)
t = time.time()
try:
    s.connect(('$host', int('$port')))
    print('%.1f' % ((time.time() - t) * 1000))
except Exception:
    pass
finally:
    s.close()
" 2>/dev/null
    return 0
  fi
  return 1
}

measure_icmp_ms() {
  local peer="$1"
  [ -n "$peer" ] && has ping || return 1
  ping -c 3 -W 2 "$peer" 2>/dev/null | tail -1 | sed -n 's/.*= \([0-9.]*\)\/.*/\1/p'
}

send_heartbeat() {
  local running="false"
  local link="false"
  local lat="" lat_json="null"
  tunnel_service_active && running="true"
  tunnel_link_up && link="true"

  case "${TUNNEL_MODE:-direct_l3}" in
    direct_l3)
      if [ "$link" = "true" ]; then
        local peer="10.10.0.2"
        [ "${PULSE_SIDE:-}" = "abroad" ] && peer="10.10.0.1"
        lat="$(measure_icmp_ms "$peer" || true)"
      fi
      ;;
    reverse_*)
      # Abroad dials Iran tunnel port — TCP RTT is the real reverse latency.
      # Iran does not measure (avoids null overwriting abroad's value).
      if [ "${PULSE_SIDE:-}" = "abroad" ] && [ "$running" = "true" ] \
        && [ -n "${IRAN_PUBLIC_IP:-}" ] && [ -n "${CONTROL_PORT:-}" ]; then
        lat="$(measure_tcp_ms "$IRAN_PUBLIC_IP" "$CONTROL_PORT" || true)"
      fi
      ;;
  esac

  [ -n "$lat" ] && lat_json="$lat"
  api POST "/api/hpx_pulse/agent/heartbeat" \
    "$(jq -nc \
      --arg s "running" \
      --arg h "$(hostname -f 2>/dev/null || hostname)" \
      --argjson tr "$running" \
      --argjson iu "$link" \
      --argjson lm "$lat_json" \
      '{status:$s, host:$h, tunnel_running:$tr, iface_up:$iu, latency_ms:($lm|tonumber? // null), message:"HPX Pulse sync"}')" \
    >/dev/null || warn "heartbeat to panel failed — check PANEL_URL and firewall"
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

  log "claiming join token (${side})..."
  claim=$(curl -fsSL -X POST -H "Content-Type: application/json" -d "$body" \
    "${PANEL_URL}/api/hpx_pulse/agent/claim") || die "claim failed — check panel URL and token"

  AGENT_KEY=$(echo "$claim" | jq -r '.agent_key')
  PULSE_ID=$(echo "$claim" | jq -r '.pulse_id')
  CONFIG_HASH=$(echo "$claim" | jq -r '.config_hash')
  TUNNEL_MODE=$(echo "$claim" | jq -r '.tunnel_mode // "direct_l3"')
  CONTROL_PORT=$(echo "$claim" | jq -r '.control_port // empty')
  IRAN_PUBLIC_IP=$(echo "$claim" | jq -r '.iran_public_ip // empty')
  ABROAD_PUBLIC_IP=$(echo "$claim" | jq -r '.abroad_public_ip // empty')
  [ -n "$AGENT_KEY" ] && [ "$AGENT_KEY" != "null" ] || die "missing agent_key from panel"

  install_self
  write_env
  ensure_engine
  apply_tunnel_config "$(echo "$claim" | jq -r '.tunnel_toml // .backpack_toml // empty')"
  write_env
  install_agent_systemd

  api POST "/api/hpx_pulse/agent/ack" \
    "$(jq -nc '{command:"start", status:"running", message:"HPX Pulse joined"}')" >/dev/null || true
  send_heartbeat
  log "ready on ${side} — pulse_id=${PULSE_ID} (panel should show agent connected)"
}

cmd_sync() {
  need_root
  load_env
  ensure_engine
  local cfg hash toml command
  cfg=$(api GET "/api/hpx_pulse/agent/config")
  hash=$(echo "$cfg" | jq -r '.config_hash')
  command=$(echo "$cfg" | jq -r '.agent_command // empty')
  toml=$(echo "$cfg" | jq -r '.tunnel_toml // .backpack_toml // empty')
  TUNNEL_MODE=$(echo "$cfg" | jq -r '.tunnel_mode // "direct_l3"')
  CONTROL_PORT=$(echo "$cfg" | jq -r '.control_port // empty')
  IRAN_PUBLIC_IP=$(echo "$cfg" | jq -r '.iran_public_ip // empty')
  ABROAD_PUBLIC_IP=$(echo "$cfg" | jq -r '.abroad_public_ip // empty')

  if [ "$hash" != "${CONFIG_HASH:-}" ] || [ "$command" = "start" ] || [ "$command" = "restart" ]; then
    apply_tunnel_config "$toml"
    CONFIG_HASH="$hash"
    api POST "/api/hpx_pulse/agent/ack" \
      "$(jq -nc --arg c "${command:-start}" '{command:$c, status:"running", message:"HPX config applied"}')" >/dev/null || true
  fi

  write_env
  send_heartbeat
}

cmd_status() {
  load_env 2>/dev/null || true
  echo "HPX Pulse Agent"
  echo "  panel : ${PANEL_URL:-not set}"
  echo "  side  : ${PULSE_SIDE:-?}"
  echo "  mode  : ${TUNNEL_MODE:-direct_l3}"
  echo "  pulse : ${PULSE_ID:-?}"
  echo "  config: ${TUNNEL_CFG:-$(tunnel_cfg_path 2>/dev/null || echo '?')}"
  if tunnel_service_active; then
    echo "  tunnel: running (${TUNNEL_SERVICE})"
  else
    echo "  tunnel: stopped"
  fi
  if [ "${TUNNEL_MODE:-direct_l3}" = "direct_l3" ]; then
    if tunnel_iface_up; then
      echo "  link  : bp0 up"
    else
      echo "  link  : bp0 down"
    fi
  elif [ "${PULSE_SIDE:-}" = "iran" ]; then
    if tunnel_port_listening; then
      echo "  link  : tunnel port ${CONTROL_PORT:-?} listening"
    else
      echo "  link  : tunnel port not listening"
    fi
  else
    echo "  link  : reverse client (check panel ping)"
  fi
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

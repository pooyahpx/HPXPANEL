#!/usr/bin/env bash
#
# HPX ICMP Tunnel Agent — lightweight Iran-side join client
# ----------------------------------------------------------
# Claim a panel-issued join token and run the ICMP tunnel locally.
# No full HPXPANEL install required on the Iran server.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-tunnel-agent.sh \
#     | sudo bash -s -- join <TOKEN> --panel-url https://panel.example.com
#
# Commands: join | sync | status | logs | restart | uninstall
#
set -euo pipefail

if [ "${1:-}" = "@" ]; then shift; fi

INSTALL_DIR="${INSTALL_DIR:-/opt/hpx-tunnel}"
ETC_DIR="${ETC_DIR:-/etc/hpx-tunnel}"
ENV_FILE="$ETC_DIR/agent.env"
STATE_FILE="$ETC_DIR/state.json"
BIN_LINK="${BIN_LINK:-/usr/local/bin/hpx-tunnel-agent}"
SERVICE_NAME="${SERVICE_NAME:-hpx-tunnel-agent}"
TIMER_NAME="${TIMER_NAME:-hpx-tunnel-agent.timer}"
SCRIPT_SRC="${BASH_SOURCE[0]:-$0}"

if [ -t 1 ]; then
  c_grn='\033[0;32m'; c_yel='\033[0;33m'; c_red='\033[0;31m'
  c_cyn='\033[0;36m'; c_bld='\033[1m'; c_dim='\033[2m'; c_off='\033[0m'
else
  c_grn=''; c_yel=''; c_red=''; c_cyn=''; c_bld=''; c_dim=''; c_off=''
fi
log()  { echo -e "${c_grn}[+]${c_off} $*"; }
warn() { echo -e "${c_yel}[!]${c_off} $*"; }
err()  { echo -e "${c_red}[x]${c_off} $*" >&2; }
die()  { err "$*"; exit 1; }
has()  { command -v "$1" >/dev/null 2>&1; }

need_root() {
  [ "$(id -u)" -eq 0 ] || die "run as root (sudo)"
}

ensure_deps() {
  has curl || die "curl is required"
  has docker || die "docker is required"
  docker info >/dev/null 2>&1 || die "docker daemon is not running"
  has jq || {
    warn "jq not found — installing via apt/yum if possible"
    if has apt-get; then
      apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq jq >/dev/null
    elif has dnf; then
      dnf install -y -q jq >/dev/null
    elif has yum; then
      yum install -y -q jq >/dev/null
    else
      die "please install jq"
    fi
  }
}

load_env() {
  [ -f "$ENV_FILE" ] || die "agent not configured ($ENV_FILE missing). Run: join <TOKEN>"
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
  [ -n "${PANEL_URL:-}" ] || die "PANEL_URL missing in $ENV_FILE"
  [ -n "${AGENT_KEY:-}" ] || die "AGENT_KEY missing in $ENV_FILE"
}

api() {
  local method="$1" path="$2" body="${3:-}"
  local url="${PANEL_URL%/}${path}"
  local args=(-fsSL -X "$method" -H "X-HPX-Agent-Key: ${AGENT_KEY}" -H "Accept: application/json")
  if [ -n "$body" ]; then
    args+=(-H "Content-Type: application/json" -d "$body")
  fi
  curl "${args[@]}" "$url"
}

write_env() {
  mkdir -p "$ETC_DIR" "$INSTALL_DIR"
  cat >"$ENV_FILE" <<EOF
PANEL_URL=${PANEL_URL}
AGENT_KEY=${AGENT_KEY}
TUNNEL_ID=${TUNNEL_ID:-}
CONTAINER_NAME=${CONTAINER_NAME:-}
INTERFACE=${INTERFACE:-hpx0}
CONFIG_HASH=${CONFIG_HASH:-}
EOF
  chmod 600 "$ENV_FILE"
}

save_state() {
  echo "$1" >"$STATE_FILE"
  chmod 600 "$STATE_FILE"
}

install_self() {
  mkdir -p "$INSTALL_DIR"
  if [ -f "$SCRIPT_SRC" ] && [ -r "$SCRIPT_SRC" ]; then
    cp "$SCRIPT_SRC" "$INSTALL_DIR/hpx-tunnel-agent.sh"
  else
    # Piped install — re-fetch from GitHub
    curl -fsSL "https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-tunnel-agent.sh" \
      -o "$INSTALL_DIR/hpx-tunnel-agent.sh"
  fi
  chmod 755 "$INSTALL_DIR/hpx-tunnel-agent.sh"
  ln -sfn "$INSTALL_DIR/hpx-tunnel-agent.sh" "$BIN_LINK"
}

install_systemd() {
  cat >"/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=HPX ICMP Tunnel Agent sync
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
Description=HPX ICMP Tunnel Agent sync timer

[Timer]
OnBootSec=30s
OnUnitActiveSec=30s
AccuracySec=5s
Unit=${SERVICE_NAME}.service

[Install]
WantedBy=timers.target
EOF

  systemctl daemon-reload
  systemctl enable --now "$TIMER_NAME" >/dev/null
  log "systemd timer ${TIMER_NAME} enabled (every ~30s)"
}

apply_port_forwards() {
  local json="$1"
  local count
  count=$(echo "$json" | jq 'length')
  [ "$count" -gt 0 ] || return 0
  local i ext ip port
  for i in $(seq 0 $((count - 1))); do
    ext=$(echo "$json" | jq -r ".[$i].external_port")
    ip=$(echo "$json" | jq -r ".[$i].internal_ip")
    port=$(echo "$json" | jq -r ".[$i].internal_port")
    [ -n "$ext" ] && [ -n "$ip" ] && [ -n "$port" ] || continue
    if ! iptables -t nat -C PREROUTING -p tcp --dport "$ext" -j DNAT --to-destination "${ip}:${port}" 2>/dev/null; then
      iptables -t nat -A PREROUTING -p tcp --dport "$ext" -j DNAT --to-destination "${ip}:${port}" || true
    fi
  done
}

assign_interface_ip() {
  local iface="$1" local_ip="$2"
  local cidr="$local_ip"
  [[ "$cidr" == */* ]] || cidr="${local_ip}/24"
  sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true
  ip addr add "$cidr" dev "$iface" 2>/dev/null || true
  ip link set "$iface" up 2>/dev/null || true
}

stop_tunnel_container() {
  local name="$1"
  docker rm -f "$name" >/dev/null 2>&1 || true
}

start_tunnel_from_config() {
  local cfg="$1"
  local image container iface password keepalive remote_ip mtu dscp local_ip port_forwards

  image=$(echo "$cfg" | jq -r '.docker_image')
  container=$(echo "$cfg" | jq -r '.container_name')
  iface=$(echo "$cfg" | jq -r '.interface')
  password=$(echo "$cfg" | jq -r '.password')
  keepalive=$(echo "$cfg" | jq -r '.keepalive')
  remote_ip=$(echo "$cfg" | jq -r '.remote_ip // empty')
  mtu=$(echo "$cfg" | jq -r '.mtu // empty')
  dscp=$(echo "$cfg" | jq -r '.dscp_mark // empty')
  local_ip=$(echo "$cfg" | jq -r '.local_ip')
  port_forwards=$(echo "$cfg" | jq -c '.port_forwards // []')

  [ -n "$remote_ip" ] || die "remote_ip missing in config"
  [ -n "$password" ] || die "password missing in config"

  log "pulling ${image}"
  docker pull "$image" >/dev/null
  stop_tunnel_container "$container"

  local env_args=(-e "INTERFACE=${iface}" -e "PASSWORD=${password}" -e "KEEPALIVE=${keepalive}" -e "REMOTE_IP=${remote_ip}")
  [ -n "$mtu" ] && [ "$mtu" != "null" ] && env_args+=(-e "MTU=${mtu}")
  [ -n "$dscp" ] && [ "$dscp" != "null" ] && env_args+=(-e "DSCP_MARK=${dscp}")

  log "starting container ${container}"
  docker run -d \
    --cap-add=NET_ADMIN \
    --device /dev/net/tun:/dev/net/tun \
    --net=host \
    --restart unless-stopped \
    --name "$container" \
    "${env_args[@]}" \
    "$image" >/dev/null

  sleep 2
  assign_interface_ip "$iface" "$local_ip"
  apply_port_forwards "$port_forwards"

  if ! docker inspect -f '{{.State.Running}}' "$container" 2>/dev/null | grep -qi true; then
    docker logs --tail 30 "$container" || true
    die "container failed to stay running"
  fi

  CONTAINER_NAME="$container"
  INTERFACE="$iface"
  CONFIG_HASH=$(echo "$cfg" | jq -r '.config_hash')
  TUNNEL_ID=$(echo "$cfg" | jq -r '.tunnel_id')
  write_env
  save_state "$cfg"
}

ack_command() {
  local command="$1" status="$2" message="${3:-}"
  local body
  body=$(jq -nc --arg c "$command" --arg s "$status" --arg m "$message" \
    '{command:$c, status:$s, message:(if $m=="" then null else $m end)}')
  api POST "/api/hpx_tunnel/agent/ack" "$body" >/dev/null || true
}

heartbeat() {
  local status="$1" message="${2:-}"
  local running="false" iface_up="false" bytes_up=0 bytes_down=0
  if [ -n "${CONTAINER_NAME:-}" ] && docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null | grep -qi true; then
    running="true"
  fi
  if [ -n "${INTERFACE:-}" ] && [ -d "/sys/class/net/${INTERFACE}" ]; then
    iface_up="true"
    bytes_up=$(cat "/sys/class/net/${INTERFACE}/statistics/tx_bytes" 2>/dev/null || echo 0)
    bytes_down=$(cat "/sys/class/net/${INTERFACE}/statistics/rx_bytes" 2>/dev/null || echo 0)
  fi
  local host
  host="$(hostname -f 2>/dev/null || hostname)"
  local body
  body=$(jq -nc \
    --arg s "$status" \
    --arg h "$host" \
    --arg m "$message" \
    --argjson up "$bytes_up" \
    --argjson down "$bytes_down" \
    --argjson cr "$running" \
    --argjson iu "$iface_up" \
    '{status:$s, host:$h, message:(if $m=="" then null else $m end), bytes_up:$up, bytes_down:$down, container_running:$cr, interface_up:$iu}')
  api POST "/api/hpx_tunnel/agent/heartbeat" "$body"
}

cmd_join() {
  need_root
  ensure_deps
  local token="" panel_url=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --panel-url) panel_url="${2:-}"; shift 2 ;;
      --panel-url=*) panel_url="${1#*=}"; shift ;;
      -*) die "unknown flag: $1" ;;
      *) token="$1"; shift ;;
    esac
  done
  [ -n "$token" ] || die "usage: join <TOKEN> --panel-url https://panel.example.com"
  [ -n "$panel_url" ] || die "--panel-url is required"

  PANEL_URL="${panel_url%/}"
  local host claim_body claim
  host="$(hostname -f 2>/dev/null || hostname)"
  claim_body=$(jq -nc --arg t "$token" --arg h "$host" '{join_token:$t, host:$h}')

  log "claiming join token against ${PANEL_URL}"
  claim=$(curl -fsSL -X POST \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "$claim_body" \
    "${PANEL_URL}/api/hpx_tunnel/agent/claim") || die "claim failed — check token / panel URL"

  AGENT_KEY=$(echo "$claim" | jq -r '.agent_key')
  [ -n "$AGENT_KEY" ] && [ "$AGENT_KEY" != "null" ] || die "claim response missing agent_key"

  install_self
  start_tunnel_from_config "$claim"
  install_systemd
  ack_command "start" "running" "joined and started"
  heartbeat "running" "joined" >/dev/null || true

  echo
  echo -e "${c_bld}${c_cyn}HPX Iran agent ready${c_off}"
  echo "  tunnel id : $(echo "$claim" | jq -r '.tunnel_id')"
  echo "  container : $(echo "$claim" | jq -r '.container_name')"
  echo "  remote    : $(echo "$claim" | jq -r '.remote_ip')"
  echo "  commands  : hpx-tunnel-agent status | logs | sync | restart | uninstall"
  echo
}

cmd_sync() {
  need_root
  ensure_deps
  load_env

  local cfg desired command hash
  cfg=$(api GET "/api/hpx_tunnel/agent/config") || die "failed to pull config"
  desired=$(echo "$cfg" | jq -r '.desired_status')
  command=$(echo "$cfg" | jq -r '.agent_command // empty')
  hash=$(echo "$cfg" | jq -r '.config_hash')
  enabled=$(echo "$cfg" | jq -r '.enabled')

  if [ "$enabled" != "true" ] || [ "$desired" = "stopped" ] || [ "$command" = "stop" ]; then
    stop_tunnel_container "${CONTAINER_NAME:-$(echo "$cfg" | jq -r '.container_name')}"
    ack_command "${command:-stop}" "stopped" "stopped by panel"
    heartbeat "stopped" >/dev/null || true
    CONFIG_HASH="$hash"
    write_env
    return 0
  fi

  local need_restart=0
  if [ "$hash" != "${CONFIG_HASH:-}" ]; then
    need_restart=1
  fi
  if [ "$command" = "start" ] || [ "$command" = "restart" ]; then
    need_restart=1
  fi
  if [ -n "${CONTAINER_NAME:-}" ] && ! docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null | grep -qi true; then
    need_restart=1
  fi

  if [ "$need_restart" -eq 1 ]; then
    start_tunnel_from_config "$cfg"
    ack_command "${command:-restart}" "running" "synced"
  fi

  heartbeat "running" >/dev/null || true
}

cmd_status() {
  if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -a; source "$ENV_FILE"; set +a
  fi
  echo "panel     : ${PANEL_URL:-not set}"
  echo "tunnel id : ${TUNNEL_ID:-?}"
  echo "container : ${CONTAINER_NAME:-?}"
  echo "interface : ${INTERFACE:-?}"
  if [ -n "${CONTAINER_NAME:-}" ] && docker inspect -f '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null; then
    :
  else
    echo "docker    : not running"
  fi
  if [ -n "${INTERFACE:-}" ]; then
    ip -4 -o addr show dev "$INTERFACE" 2>/dev/null || echo "iface     : down"
  fi
}

cmd_logs() {
  load_env
  docker logs --tail "${1:-100}" -f "$CONTAINER_NAME"
}

cmd_restart() {
  need_root
  ensure_deps
  load_env
  local cfg
  cfg=$(api GET "/api/hpx_tunnel/agent/config") || die "failed to pull config"
  start_tunnel_from_config "$cfg"
  ack_command "restart" "running" "manual restart"
  heartbeat "running" >/dev/null || true
  log "restarted"
}

cmd_uninstall() {
  need_root
  if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -a; source "$ENV_FILE"; set +a
    stop_tunnel_container "${CONTAINER_NAME:-}"
  fi
  systemctl disable --now "$TIMER_NAME" 2>/dev/null || true
  systemctl disable --now "$SERVICE_NAME" 2>/dev/null || true
  rm -f "/etc/systemd/system/${SERVICE_NAME}.service" "/etc/systemd/system/${TIMER_NAME}"
  systemctl daemon-reload 2>/dev/null || true
  rm -rf "$ETC_DIR" "$INSTALL_DIR" "$BIN_LINK"
  log "uninstalled"
}

usage() {
  cat <<EOF
HPX ICMP Tunnel Agent

  join <TOKEN> --panel-url URL   Claim token and start tunnel
  sync                           Pull config / apply desired state
  status                         Show local status
  logs [N]                       Tail container logs
  restart                        Force recreate container from panel config
  uninstall                      Remove agent + container

EOF
}

main() {
  local cmd="${1:-}"
  shift || true
  case "$cmd" in
    join) cmd_join "$@" ;;
    sync) cmd_sync "$@" ;;
    status) cmd_status "$@" ;;
    logs) cmd_logs "$@" ;;
    restart) cmd_restart "$@" ;;
    uninstall) cmd_uninstall "$@" ;;
    ""|-h|--help|help) usage ;;
    *) die "unknown command: $cmd" ;;
  esac
}

main "$@"

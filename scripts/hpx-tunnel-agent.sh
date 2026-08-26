#!/usr/bin/env bash
#
# HPX ICMP Tunnel Agent — interactive Iran-side installer
# -------------------------------------------------------
# Lightweight tunnel runner for Iran VPS (Docker only — no full panel).
#
# Interactive (recommended):
#   curl -fsSL https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-tunnel-agent.sh \
#     | sudo bash
#
# Or after install:
#   sudo hpx-tunnel-agent
#
set -euo pipefail

if [ "${1:-}" = "@" ]; then shift; fi

INSTALL_DIR="${INSTALL_DIR:-/opt/hpx-tunnel}"
ETC_DIR="${ETC_DIR:-/etc/hpx-tunnel}"
ENV_FILE="$ETC_DIR/agent.env"
STATE_FILE="$ETC_DIR/state.json"
MANUAL_ENV="$ETC_DIR/manual.env"
BIN_LINK="${BIN_LINK:-/usr/local/bin/hpx-tunnel-agent}"
SERVICE_NAME="${SERVICE_NAME:-hpx-tunnel-agent}"
TIMER_NAME="${TIMER_NAME:-hpx-tunnel-agent.timer}"
SCRIPT_SRC="${BASH_SOURCE[0]:-$0}"
DEFAULT_IMAGE="${DEFAULT_IMAGE:-stormotron/narnia:0.0.3}"
FALLBACK_IMAGE="${FALLBACK_IMAGE:-stormotron/narnia:0.0.3}"
BRANDED_IMAGE="${BRANDED_IMAGE:-ghcr.io/pooyahpx/hpx-icmp:0.0.3}"

if [ -t 1 ]; then
  c_grn='\033[0;32m'; c_yel='\033[0;33m'; c_red='\033[0;31m'
  c_cyn='\033[0;36m'; c_mag='\033[0;35m'; c_bld='\033[1m'; c_dim='\033[2m'; c_off='\033[0m'
else
  c_grn=''; c_yel=''; c_red=''; c_cyn=''; c_mag=''; c_bld=''; c_dim=''; c_off=''
fi
# Logs must go to stderr — stdout is captured by $(pull_image ...)
log()  { echo -e "${c_grn}[+]${c_off} $*" >&2; }
warn() { echo -e "${c_yel}[!]${c_off} $*" >&2; }
err()  { echo -e "${c_red}[x]${c_off} $*" >&2; }
die()  { err "$*"; exit 1; }
has()  { command -v "$1" >/dev/null 2>&1; }
hr()   { echo -e "${c_cyn}------------------------------------------------------------${c_off}" >&2; }

_read() {
  if [ -e /dev/tty ]; then
    read "$@" </dev/tty || true
  else
    read "$@" || true
  fi
}

ask_val() {
  local q="$1" def="${2:-}" ans
  if [ -n "$def" ]; then
    _read -r -p "$(echo -e "${c_bld}${q}${c_off} [${c_dim}${def}${c_off}]: ")" ans
    echo "${ans:-$def}"
  else
    while true; do
      _read -r -p "$(echo -e "${c_bld}${q}${c_off}: ")" ans
      if [ -n "${ans:-}" ]; then echo "$ans"; return; fi
      warn "This field is required."
    done
  fi
}

ask_secret() {
  local q="$1" ans
  while true; do
    _read -r -s -p "$(echo -e "${c_bld}${q}${c_off}: ")" ans
    echo
    if [ -n "${ans:-}" ]; then echo "$ans"; return; fi
    warn "Password is required."
  done
}

ask_yn() {
  local q="$1" def="${2:-y}" ans
  local hint="y/n"
  [ "$def" = "y" ] && hint="Y/n"
  [ "$def" = "n" ] && hint="y/N"
  while true; do
    _read -r -p "$(echo -e "${c_bld}${q}${c_off} (${hint}): ")" ans
    ans="${ans:-$def}"
    case "$ans" in
      [Yy]|[Yy][Ee][Ss]) return 0 ;;
      [Nn]|[Nn][Oo]) return 1 ;;
      *) warn "Please type y or n." ;;
    esac
  done
}

need_root() {
  [ "$(id -u)" -eq 0 ] || die "run as root (sudo)"
}

banner() {
  clear 2>/dev/null || true
  echo
  echo -e "${c_bld}${c_mag}  ██╗  ██╗██████╗ ██╗  ██╗${c_off}"
  echo -e "${c_bld}${c_mag}  ██║  ██║██╔══██╗╚██╗██╔╝${c_off}"
  echo -e "${c_bld}${c_mag}  ███████║██████╔╝ ╚███╔╝ ${c_off}"
  echo -e "${c_bld}${c_mag}  ██╔══██║██╔═══╝  ██╔██╗ ${c_off}"
  echo -e "${c_bld}${c_mag}  ██║  ██║██║     ██╔╝ ██╗${c_off}"
  echo -e "${c_bld}${c_mag}  ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝${c_off}"
  echo -e "  ${c_cyn}ICMP Tunnel Agent${c_off}  ${c_dim}// Iran side only${c_off}"
  hr
  echo -e "  ${c_dim}No full panel UI on this server — just the tunnel.${c_off}"
  echo
}

ensure_deps() {
  has curl || die "curl is required"
  if ! has docker; then
    warn "Docker not found."
    if ask_yn "Try to install Docker via get.docker.com?" "y"; then
      curl -fsSL https://get.docker.com | sh
    else
      die "Docker is required"
    fi
  fi
  docker info >/dev/null 2>&1 || die "docker daemon is not running — start it and retry"
  if ! has jq; then
    warn "jq not found — installing..."
    if has apt-get; then
      apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq jq >/dev/null
    elif has dnf; then
      dnf install -y -q jq >/dev/null
    elif has yum; then
      yum install -y -q jq >/dev/null
    else
      die "please install jq"
    fi
  fi
}

load_env() {
  [ -f "$ENV_FILE" ] || die "agent not configured yet. Run the interactive installer first."
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
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
MODE=${MODE:-panel}
PANEL_URL=${PANEL_URL:-}
AGENT_KEY=${AGENT_KEY:-}
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
  if [ -f "$SCRIPT_SRC" ] && [ -r "$SCRIPT_SRC" ] && [ "${SCRIPT_SRC}" != "bash" ] && [ "${SCRIPT_SRC}" != "-" ]; then
    cp "$SCRIPT_SRC" "$INSTALL_DIR/hpx-tunnel-agent.sh" 2>/dev/null || true
  fi
  if [ ! -s "$INSTALL_DIR/hpx-tunnel-agent.sh" ]; then
    curl -fsSL "https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-tunnel-agent.sh" \
      -o "$INSTALL_DIR/hpx-tunnel-agent.sh"
  fi
  chmod 755 "$INSTALL_DIR/hpx-tunnel-agent.sh"
  ln -sfn "$INSTALL_DIR/hpx-tunnel-agent.sh" "$BIN_LINK"
}

install_systemd() {
  local sync_cmd="$BIN_LINK sync"
  if [ "${MODE:-panel}" = "manual" ]; then
    # Manual mode: keep container alive; no panel sync needed.
    sync_cmd="/bin/true"
  fi
  cat >"/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=HPX ICMP Tunnel Agent
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=$sync_cmd
Nice=10

[Install]
WantedBy=multi-user.target
EOF

  if [ "${MODE:-panel}" = "panel" ]; then
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
    log "panel sync timer enabled (~30s)"
  else
    rm -f "/etc/systemd/system/${TIMER_NAME}"
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME" >/dev/null 2>&1 || true
  fi
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
  [ -n "$name" ] || return 0
  docker rm -f "$name" >/dev/null 2>&1 || true
}

pull_image() {
  local wanted="$1"
  local candidate

  # Prefer an image that already exists locally (e.g. after manual tag).
  for candidate in "$wanted" "$BRANDED_IMAGE" "$FALLBACK_IMAGE" "$DEFAULT_IMAGE"; do
    [ -n "$candidate" ] || continue
    if docker image inspect "$candidate" >/dev/null 2>&1; then
      log "using local image ${candidate}"
      # Keep panel-requested name available for next runs when possible.
      if [ "$candidate" != "$wanted" ]; then
        docker tag "$candidate" "$wanted" 2>/dev/null || true
      fi
      echo "$wanted"
      return 0
    fi
  done

  for candidate in "$wanted" "$FALLBACK_IMAGE" "$DEFAULT_IMAGE"; do
    [ -n "$candidate" ] || continue
    log "pulling ${candidate}"
    if docker pull "$candidate" >/dev/null 2>&1; then
      if [ "$candidate" != "$wanted" ]; then
        docker tag "$candidate" "$wanted" 2>/dev/null || true
        log "tagged ${candidate} -> ${wanted}"
      fi
      echo "$wanted"
      return 0
    fi
    warn "pull denied/failed: ${candidate}"
  done

  die "Cannot download tunnel image (registry denied from this server).

Run these on Iran, then get a NEW join token from the panel:

  docker pull ${FALLBACK_IMAGE}
  docker tag ${FALLBACK_IMAGE} ${wanted}
  docker tag ${FALLBACK_IMAGE} ${BRANDED_IMAGE}

Or in panel → edit IRAN tunnel → set Docker image to:
  ${FALLBACK_IMAGE}
"
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

  [ -n "$remote_ip" ] || die "remote_ip missing"
  [ -n "$password" ] || die "password missing"
  [ -n "$image" ] && [ "$image" != "null" ] || die "docker_image missing"

  image="$(pull_image "$image")"
  [ -n "$image" ] || die "resolved docker image is empty"
  # Guard against polluted image names (spaces/newlines)
  image="$(echo "$image" | tr -d '\r\n' | awk '{print $1}')"
  docker image inspect "$image" >/dev/null 2>&1 || die "image not available locally: ${image}"

  stop_tunnel_container "$container"

  local env_args=(-e "INTERFACE=${iface}" -e "PASSWORD=${password}" -e "KEEPALIVE=${keepalive}" -e "REMOTE_IP=${remote_ip}")
  [ -n "$mtu" ] && [ "$mtu" != "null" ] && env_args+=(-e "MTU=${mtu}")
  [ -n "$dscp" ] && [ "$dscp" != "null" ] && env_args+=(-e "DSCP_MARK=${dscp}")

  log "starting container ${container} (${image})"
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
  CONFIG_HASH=$(echo "$cfg" | jq -r '.config_hash // empty')
  TUNNEL_ID=$(echo "$cfg" | jq -r '.tunnel_id // empty')
  write_env
  save_state "$cfg"
}

ack_command() {
  [ "${MODE:-panel}" = "panel" ] || return 0
  [ -n "${AGENT_KEY:-}" ] || return 0
  local command="$1" status="$2" message="${3:-}"
  local body
  body=$(jq -nc --arg c "$command" --arg s "$status" --arg m "$message" \
    '{command:$c, status:$s, message:(if $m=="" then null else $m end)}')
  api POST "/api/hpx_tunnel/agent/ack" "$body" >/dev/null || true
}

heartbeat() {
  [ "${MODE:-panel}" = "panel" ] || return 0
  [ -n "${AGENT_KEY:-}" ] || return 0
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

# --------------- Interactive flows ---------------

wizard_join_panel() {
  need_root
  ensure_deps
  banner
  echo -e "  ${c_bld}Connect to HPXPANEL (join token)${c_off}"
  echo -e "  ${c_dim}Create an IRAN tunnel in the panel first, then paste the token here.${c_off}"
  echo
  local panel_url token
  panel_url=$(ask_val "Panel URL (example: https://pnl.example.com)")
  panel_url="${panel_url%/}"
  token=$(ask_val "Join token from panel (hpx_...)")

  PANEL_URL="$panel_url"
  MODE="panel"
  local host claim_body claim remote_ip
  host="$(hostname -f 2>/dev/null || hostname)"
  claim_body=$(jq -nc --arg t "$token" --arg h "$host" '{join_token:$t, host:$h}')

  echo
  log "claiming token from ${PANEL_URL} ..."
  claim=$(curl -fsSL -X POST \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "$claim_body" \
    "${PANEL_URL}/api/hpx_tunnel/agent/claim") || die "claim failed — check URL / token / expiry"

  AGENT_KEY=$(echo "$claim" | jq -r '.agent_key')
  [ -n "$AGENT_KEY" ] && [ "$AGENT_KEY" != "null" ] || die "claim response missing agent_key"

  remote_ip=$(echo "$claim" | jq -r '.remote_ip // empty')
  echo
  hr
  echo -e "  ${c_bld}Config from panel${c_off}"
  echo "  name      : $(echo "$claim" | jq -r '.name')"
  echo "  remote IP : ${remote_ip}"
  echo "  interface : $(echo "$claim" | jq -r '.interface')"
  echo "  local IP  : $(echo "$claim" | jq -r '.local_ip')"
  echo "  image     : $(echo "$claim" | jq -r '.docker_image')"
  hr
  if ! ask_yn "Apply this config and start the tunnel?" "y"; then
    die "cancelled"
  fi

  # Optional override of remote IP (still asked like classic tunnel installers)
  if ask_yn "Change remote (FOREIGN) IP before start?" "n"; then
    remote_ip=$(ask_val "FOREIGN server public IP" "$remote_ip")
    claim=$(echo "$claim" | jq --arg ip "$remote_ip" '.remote_ip=$ip')
  fi

  install_self
  start_tunnel_from_config "$claim"
  install_systemd
  ack_command "start" "running" "joined and started"
  heartbeat "running" "joined" >/dev/null || true

  echo
  echo -e "${c_bld}${c_grn}Tunnel is up.${c_off}"
  echo "  remote : ${remote_ip}"
  echo "  later  : sudo hpx-tunnel-agent   (menu)  |  status / logs / uninstall"
  echo
  _read -r -p "Press Enter to continue..." _
}

wizard_manual() {
  need_root
  ensure_deps
  banner
  echo -e "  ${c_bld}Manual tunnel setup (no panel)${c_off}"
  echo -e "  ${c_dim}You will be asked for remote IP, password, and network settings.${c_off}"
  echo

  local remote_ip password iface local_ip keepalive mtu image container
  remote_ip=$(ask_val "FOREIGN server public IP (where the tunnel goes)")
  password=$(ask_secret "Shared tunnel password (same as FOREIGN side)")
  iface=$(ask_val "Tunnel interface name" "hpx0")
  local_ip=$(ask_val "Local tunnel IP on this Iran server" "10.200.200.2")
  keepalive=$(ask_val "Keepalive seconds" "5")
  mtu=$(ask_val "MTU" "1500")
  image=$(ask_val "Docker image" "$DEFAULT_IMAGE")
  container=$(ask_val "Container name" "hpx_tunnel_iran")

  echo
  hr
  echo -e "  ${c_bld}Summary${c_off}"
  echo "  remote IP : ${remote_ip}"
  echo "  interface : ${iface}"
  echo "  local IP  : ${local_ip}"
  echo "  image     : ${image}"
  hr
  if ! ask_yn "Start tunnel with these settings?" "y"; then
    die "cancelled"
  fi

  MODE="manual"
  PANEL_URL=""
  AGENT_KEY=""
  TUNNEL_ID=""
  CONFIG_HASH=""
  CONTAINER_NAME="$container"
  INTERFACE="$iface"

  local cfg
  cfg=$(jq -nc \
    --arg image "$image" \
    --arg container "$container" \
    --arg iface "$iface" \
    --arg password "$password" \
    --argjson keepalive "$keepalive" \
    --arg remote_ip "$remote_ip" \
    --argjson mtu "$mtu" \
    --arg local_ip "$local_ip" \
    '{
      docker_image:$image,
      container_name:$container,
      interface:$iface,
      password:$password,
      keepalive:$keepalive,
      remote_ip:$remote_ip,
      mtu:$mtu,
      local_ip:$local_ip,
      port_forwards:[],
      config_hash:"manual"
    }')

  install_self
  mkdir -p "$ETC_DIR"
  cat >"$MANUAL_ENV" <<EOF
REMOTE_IP=${remote_ip}
PASSWORD=${password}
INTERFACE=${iface}
LOCAL_IP=${local_ip}
KEEPALIVE=${keepalive}
MTU=${mtu}
DOCKER_IMAGE=${image}
CONTAINER_NAME=${container}
EOF
  chmod 600 "$MANUAL_ENV"

  start_tunnel_from_config "$cfg"
  install_systemd

  echo
  echo -e "${c_bld}${c_grn}Manual tunnel is up.${c_off}"
  echo "  remote : ${remote_ip}"
  echo "  later  : sudo hpx-tunnel-agent"
  echo
  _read -r -p "Press Enter to continue..." _
}

cmd_sync() {
  need_root
  ensure_deps
  load_env
  if [ "${MODE:-panel}" = "manual" ]; then
    # Keep manual container running; nothing to sync.
    if [ -n "${CONTAINER_NAME:-}" ] && ! docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null | grep -qi true; then
      [ -f "$MANUAL_ENV" ] || die "manual.env missing"
      # shellcheck disable=SC1090
      set -a; source "$MANUAL_ENV"; set +a
      local cfg
      cfg=$(jq -nc \
        --arg image "${DOCKER_IMAGE}" \
        --arg container "${CONTAINER_NAME}" \
        --arg iface "${INTERFACE}" \
        --arg password "${PASSWORD}" \
        --argjson keepalive "${KEEPALIVE}" \
        --arg remote_ip "${REMOTE_IP}" \
        --argjson mtu "${MTU}" \
        --arg local_ip "${LOCAL_IP}" \
        '{docker_image:$image,container_name:$container,interface:$iface,password:$password,keepalive:$keepalive,remote_ip:$remote_ip,mtu:$mtu,local_ip:$local_ip,port_forwards:[],config_hash:"manual"}')
      start_tunnel_from_config "$cfg"
    fi
    return 0
  fi

  local cfg desired command hash enabled
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
  if [ "$hash" != "${CONFIG_HASH:-}" ]; then need_restart=1; fi
  if [ "$command" = "start" ] || [ "$command" = "restart" ]; then need_restart=1; fi
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
  echo "mode      : ${MODE:-?}"
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
  if [ -t 0 ] && [ -t 1 ]; then
    echo
    _read -r -p "Press Enter..." _
  fi
}

cmd_logs() {
  if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -a; source "$ENV_FILE"; set +a
  fi
  [ -n "${CONTAINER_NAME:-}" ] || die "no container configured"
  docker logs --tail "${1:-100}" -f "$CONTAINER_NAME"
}

cmd_restart() {
  need_root
  ensure_deps
  load_env
  if [ "${MODE:-panel}" = "manual" ]; then
    [ -f "$MANUAL_ENV" ] || die "manual.env missing"
    # shellcheck disable=SC1090
    set -a; source "$MANUAL_ENV"; set +a
    local cfg
    cfg=$(jq -nc \
      --arg image "${DOCKER_IMAGE}" \
      --arg container "${CONTAINER_NAME}" \
      --arg iface "${INTERFACE}" \
      --arg password "${PASSWORD}" \
      --argjson keepalive "${KEEPALIVE}" \
      --arg remote_ip "${REMOTE_IP}" \
      --argjson mtu "${MTU}" \
      --arg local_ip "${LOCAL_IP}" \
      '{docker_image:$image,container_name:$container,interface:$iface,password:$password,keepalive:$keepalive,remote_ip:$remote_ip,mtu:$mtu,local_ip:$local_ip,port_forwards:[],config_hash:"manual"}')
    start_tunnel_from_config "$cfg"
  else
    local cfg
    cfg=$(api GET "/api/hpx_tunnel/agent/config") || die "failed to pull config"
    start_tunnel_from_config "$cfg"
    ack_command "restart" "running" "manual restart"
    heartbeat "running" >/dev/null || true
  fi
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

interactive_menu() {
  need_root
  while true; do
    banner
    echo -e "  ${c_bld}1)${c_off} Connect with panel join token"
    echo -e "  ${c_bld}2)${c_off} Manual setup (ask IP / password)"
    echo -e "  ${c_bld}3)${c_off} Status"
    echo -e "  ${c_bld}4)${c_off} Logs"
    echo -e "  ${c_bld}5)${c_off} Restart tunnel"
    echo -e "  ${c_bld}6)${c_off} Uninstall"
    echo -e "  ${c_bld}0)${c_off} Exit"
    echo
    local choice
    _read -r -p "$(echo -e "${c_bld}Select${c_off} [0-6]: ")" choice
    case "${choice:-}" in
      1) wizard_join_panel ;;
      2) wizard_manual ;;
      3) cmd_status ;;
      4) cmd_logs ;;
      5) cmd_restart; _read -r -p "Press Enter..." _ ;;
      6)
        if ask_yn "Really uninstall agent and stop tunnel?" "n"; then
          cmd_uninstall
          exit 0
        fi
        ;;
      0|q|Q) exit 0 ;;
      *) warn "invalid choice"; sleep 1 ;;
    esac
  done
}

usage() {
  cat <<EOF
HPX ICMP Tunnel Agent (Iran)

Interactive menu (default):
  curl -fsSL https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-tunnel-agent.sh | sudo bash
  sudo hpx-tunnel-agent

Commands:
  menu                         Interactive installer / management
  join [TOKEN] [--panel-url]   Non-interactive panel join (optional flags)
  sync | status | logs | restart | uninstall

EOF
}

# Non-interactive join still supported for automation
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

  if [ -z "$token" ] || [ -z "$panel_url" ]; then
    # Fall back to interactive questions instead of dying
    wizard_join_panel
    return
  fi

  PANEL_URL="${panel_url%/}"
  MODE="panel"
  local host claim_body claim
  host="$(hostname -f 2>/dev/null || hostname)"
  claim_body=$(jq -nc --arg t "$token" --arg h "$host" '{join_token:$t, host:$h}')
  log "claiming join token against ${PANEL_URL}"
  claim=$(curl -fsSL -X POST \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "$claim_body" \
    "${PANEL_URL}/api/hpx_tunnel/agent/claim") || die "claim failed"
  AGENT_KEY=$(echo "$claim" | jq -r '.agent_key')
  [ -n "$AGENT_KEY" ] && [ "$AGENT_KEY" != "null" ] || die "claim response missing agent_key"
  install_self
  start_tunnel_from_config "$claim"
  install_systemd
  ack_command "start" "running" "joined and started"
  heartbeat "running" "joined" >/dev/null || true
  log "ready — remote $(echo "$claim" | jq -r '.remote_ip')"
}

main() {
  local cmd="${1:-}"
  if [ -z "$cmd" ]; then
    interactive_menu
    return
  fi
  shift || true
  case "$cmd" in
    menu|install) interactive_menu ;;
    join) cmd_join "$@" ;;
    sync) cmd_sync "$@" ;;
    status) cmd_status "$@" ;;
    logs) cmd_logs "$@" ;;
    restart) cmd_restart "$@" ;;
    uninstall) cmd_uninstall "$@" ;;
    -h|--help|help) usage ;;
    *) die "unknown command: $cmd (try with no args for interactive menu)" ;;
  esac
}

main "$@"

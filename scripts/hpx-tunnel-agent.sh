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
DEFAULT_IMAGE="${DEFAULT_IMAGE:-hpx-icmp:0.0.3}"
# Upstream runtime — pulled automatically and retagged locally as hpx-icmp.
# No Docker Hub account / docker push required.
UPSTREAM_IMAGE="${UPSTREAM_IMAGE:-stormotron/narnia:0.0.3}"

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

# Fix "sudo: unable to resolve host <name>" (common on Iran VPS like g4).
fix_hostname_resolution() {
  local hn short
  hn="$(hostname 2>/dev/null || true)"
  [ -n "$hn" ] || return 0
  short="${hn%%.*}"
  if ! grep -Eq "(^|[[:space:]])${hn}([[:space:]]|$)" /etc/hosts 2>/dev/null; then
    echo "127.0.1.1 ${hn}" >> /etc/hosts
    log "added ${hn} to /etc/hosts (fixes sudo hostname warning)"
  fi
  if [ "$short" != "$hn" ] && ! grep -Eq "(^|[[:space:]])${short}([[:space:]]|$)" /etc/hosts 2>/dev/null; then
    echo "127.0.1.1 ${short}" >> /etc/hosts
  fi
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
  echo -e "  ${c_cyn}ICMP Tunnel Agent${c_off}  ${c_dim}// IRAN agent · FOREIGN on Node${c_off}"
  hr
  echo -e "  ${c_dim}Docker-only ICMP tunnel (Narnia-compatible). No full panel UI here.${c_off}"
  echo
}

ensure_deps() {
  fix_hostname_resolution
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
  if ! has ip || ! has iptables; then
    warn "installing iproute2 / iptables..."
    if has apt-get; then
      apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq iproute2 iptables >/dev/null
    elif has dnf; then
      dnf install -y -q iproute iptables >/dev/null
    elif has yum; then
      yum install -y -q iproute iptables >/dev/null
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
LOCAL_IP=${LOCAL_IP:-10.200.200.2}
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
OnBootSec=10s
OnUnitActiveSec=15s
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

# Narnia.sh apply_firewall parity — required for reliable tunnel + forwarded traffic.
apply_tunnel_firewall() {
  local role="${1:-iran}" iface="${2:-}"
  local default_if
  sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true
  if ! grep -q '^net.ipv4.ip_forward' /etc/sysctl.conf 2>/dev/null; then
    echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
  else
    sed -i 's/^net.ipv4.ip_forward.*/net.ipv4.ip_forward=1/' /etc/sysctl.conf 2>/dev/null || true
  fi
  default_if=$(ip -4 route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}')
  if [ -n "$default_if" ]; then
    iptables -t nat -C POSTROUTING -o "$default_if" -j MASQUERADE 2>/dev/null \
      || iptables -t nat -A POSTROUTING -o "$default_if" -j MASQUERADE || true
  fi
  if [ "$role" = "iran" ] && [ -n "$iface" ] && [ -n "$default_if" ]; then
    iptables -t nat -C POSTROUTING -o "$iface" -j MASQUERADE 2>/dev/null \
      || iptables -t nat -A POSTROUTING -o "$iface" -j MASQUERADE || true
    iptables -C FORWARD -i "$default_if" -o "$iface" -j ACCEPT 2>/dev/null \
      || iptables -I FORWARD -i "$default_if" -o "$iface" -j ACCEPT || true
    iptables -C FORWARD -i "$iface" -o "$default_if" -j ACCEPT 2>/dev/null \
      || iptables -I FORWARD -i "$iface" -o "$default_if" -j ACCEPT || true
  fi
}

apply_port_forwards() {
  local json="$1"
  local count
  count=$(echo "$json" | jq 'length')
  [ "$count" -gt 0 ] || return 0
  local i ext ip port proto
  for i in $(seq 0 $((count - 1))); do
    ext=$(echo "$json" | jq -r ".[$i].external_port")
    ip=$(echo "$json" | jq -r ".[$i].internal_ip")
    port=$(echo "$json" | jq -r ".[$i].internal_port")
    [ -n "$ext" ] && [ -n "$ip" ] && [ -n "$port" ] || continue
    # Narnia forwards both TCP and UDP for each port.
    for proto in tcp udp; do
      if ! iptables -t nat -C PREROUTING -p "$proto" --dport "$ext" -j DNAT --to-destination "${ip}:${port}" 2>/dev/null; then
        iptables -t nat -A PREROUTING -p "$proto" --dport "$ext" -j DNAT --to-destination "${ip}:${port}" || true
      fi
    done
  done
}

assign_interface_ip() {
  local iface="$1" local_ip="$2" mtu="${3:-}"
  local cidr="$local_ip" i
  [[ "$cidr" == */* ]] || cidr="${local_ip}/24"
  sysctl -w net.ipv4.icmp_echo_ignore_all=1 >/dev/null 2>&1 || true
  sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true

  for i in $(seq 1 40); do
    if ip link show dev "$iface" >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
  if ! ip link show dev "$iface" >/dev/null 2>&1; then
    die "tunnel interface ${iface} did not appear — check docker logs"
  fi

  ip addr flush dev "$iface" 2>/dev/null || true
  ip addr add "$cidr" dev "$iface" 2>/dev/null || ip addr add "$cidr" dev "$iface" || true
  if [ -n "$mtu" ] && [ "$mtu" != "null" ]; then
    ip link set dev "$iface" mtu "$mtu" 2>/dev/null || true
  fi
  ip link set "$iface" up 2>/dev/null || true

  if ! ip -4 -o addr show dev "$iface" 2>/dev/null | grep -q 'inet '; then
    die "failed to assign ${cidr} on ${iface}"
  fi
  log "interface ${iface} ready (${cidr})"
}

peer_tunnel_ip() {
  local ip="$1"
  ip="${ip%%/*}"
  case "$ip" in
    *.1) echo "${ip%.1}.2" ;;
    *.2) echo "${ip%.2}.1" ;;
    *) echo "" ;;
  esac
}

measure_peer_ping() {
  local peer="$1"
  [ -n "$peer" ] || { echo "null null"; return 0; }
  local out avg loss
  out=$(ping -c 3 -W 2 "$peer" 2>/dev/null || true)
  loss=$(echo "$out" | sed -n 's/.* \([0-9.]\+\)% packet loss.*/\1/p' | head -1)
  avg=$(echo "$out" | sed -n 's/.*= [0-9.]\+\/\([0-9.]\+\)\/.*/\1/p' | head -1)
  if [ -z "$avg" ]; then
    echo "null ${loss:-100}"
  else
    echo "${avg} ${loss:-0}"
  fi
}

stop_tunnel_container() {
  local name="$1"
  [ -n "$name" ] || return 0
  docker rm -f "$name" >/dev/null 2>&1 || true
}

# One host = one ICMP tunnel. Kill sibling HPX + legacy Narnia containers.
stop_conflicting_tunnels() {
  local keep="${1:-}" iface="${2:-}"
  local id name env_iface
  if docker inspect narnia_tunnel >/dev/null 2>&1; then
    warn "removing legacy Narnia container narnia_tunnel (ICMP conflict)"
    docker rm -f narnia_tunnel >/dev/null 2>&1 || true
  fi
  for id in $(docker ps -aq --filter name='hpx_tunnel' 2>/dev/null); do
    name=$(docker inspect -f '{{.Name}}' "$id" 2>/dev/null | sed 's#^/##')
    [ -n "$name" ] || continue
    [ "$name" = "$keep" ] && continue
    if [ -n "$iface" ]; then
      env_iface=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$id" 2>/dev/null | sed -n 's/^INTERFACE=//p' | head -1)
      [ -n "$env_iface" ] && [ "$env_iface" != "$iface" ] && continue
    fi
    warn "removing conflicting tunnel container: ${name}"
    docker rm -f "$id" >/dev/null 2>&1 || true
  done
  if [ -n "$iface" ] && ip link show dev "$iface" >/dev/null 2>&1; then
    # Stale TAP left behind after a crashed container.
    if ! docker ps -q --filter name='hpx_tunnel' | grep -q .; then
      ip link delete "$iface" 2>/dev/null || true
    fi
  fi
}


pull_image() {
  local wanted="${1:-$DEFAULT_IMAGE}"
  wanted="$(echo "$wanted" | tr -d '\r\n' | awk '{print $1}')"
  [ -n "$wanted" ] || wanted="$DEFAULT_IMAGE"

  # Always prefer the local HPX brand name for running containers.
  local run_as="$DEFAULT_IMAGE"

  if docker image inspect "$run_as" >/dev/null 2>&1; then
    log "using local image ${run_as}"
    echo "$run_as"
    return 0
  fi

  if docker image inspect "$wanted" >/dev/null 2>&1; then
    docker tag "$wanted" "$run_as" 2>/dev/null || true
    log "using local image ${wanted} (tagged as ${run_as})"
    echo "$run_as"
    return 0
  fi

  if docker image inspect "$UPSTREAM_IMAGE" >/dev/null 2>&1; then
    docker tag "$UPSTREAM_IMAGE" "$run_as" 2>/dev/null || true
    log "using cached runtime (tagged as ${run_as})"
    echo "$run_as"
    return 0
  fi

  log "downloading tunnel runtime (one-time)…"
  if ! docker pull "$UPSTREAM_IMAGE" >/dev/null 2>&1; then
    die "Cannot download tunnel runtime image.
Check Docker Hub access on this server, then retry.
No Docker account or docker push is required."
  fi
  docker tag "$UPSTREAM_IMAGE" "$run_as"
  log "ready: ${run_as}"
  echo "$run_as"
}

start_tunnel_from_config() {
  local cfg="$1"
  local image container iface password keepalive remote_ip mtu dscp local_ip port_forwards role server_listen bw op_mode

  image=$(echo "$cfg" | jq -r '.docker_image // empty')
  container=$(echo "$cfg" | jq -r '.container_name')
  iface=$(echo "$cfg" | jq -r '.interface // "hpx0"')
  password=$(echo "$cfg" | jq -r '.password')
  keepalive=$(echo "$cfg" | jq -r '.keepalive // 20')
  remote_ip=$(echo "$cfg" | jq -r '.remote_ip // empty')
  mtu=$(echo "$cfg" | jq -r '.mtu // empty')
  dscp=$(echo "$cfg" | jq -r '.dscp_mark // empty')
  local_ip=$(echo "$cfg" | jq -r '.local_ip')
  port_forwards=$(echo "$cfg" | jq -c '.port_forwards // []')
  role=$(echo "$cfg" | jq -r '.role // "iran"')
  server_listen=$(echo "$cfg" | jq -r '.server_listen // "0.0.0.0"')
  bw=$(echo "$cfg" | jq -r '.bandwidth_limit // empty')
  op_mode=$(echo "$cfg" | jq -r '.operating_mode // empty')

  [ -n "$password" ] || die "password missing"
  if [ "$role" = "iran" ]; then
    [ -n "$remote_ip" ] || die "remote_ip missing"
  fi
  [ -n "$image" ] && [ "$image" != "null" ] || image="$DEFAULT_IMAGE"

  image="$(pull_image "$image")"
  [ -n "$image" ] || die "resolved docker image is empty"
  # Guard against polluted image names (spaces/newlines)
  image="$(echo "$image" | tr -d '\r\n' | awk '{print $1}')"
  docker image inspect "$image" >/dev/null 2>&1 || die "image not available locally: ${image}"

  fix_hostname_resolution
  stop_tunnel_container "$container"
  stop_conflicting_tunnels "$container" "$iface"
  sysctl -w net.ipv4.icmp_echo_ignore_all=1 >/dev/null 2>&1 || true

  local env_args=(-e "INTERFACE=${iface}" -e "PASSWORD=${password}" -e "KEEPALIVE=${keepalive}")
  if [ "$role" = "foreign" ]; then
    env_args+=(-e "SERVER=${server_listen:-0.0.0.0}")
    [ -n "$op_mode" ] && [ "$op_mode" != "null" ] && env_args+=(-e "OPERATING_MODE=${op_mode}")
    [ -n "$bw" ] && [ "$bw" != "null" ] && env_args+=(-e "BANDWIDTH_LIMIT=${bw}")
  else
    env_args+=(-e "REMOTE_IP=${remote_ip}")
    [ -n "$dscp" ] && [ "$dscp" != "null" ] && env_args+=(-e "DSCP_MARK=${dscp}")
  fi
  [ -n "$mtu" ] && [ "$mtu" != "null" ] && env_args+=(-e "MTU=${mtu}")

  log "starting container ${container} (${image}) role=${role}"
  docker run -d \
    --cap-add=NET_ADMIN \
    --device /dev/net/tun:/dev/net/tun \
    --net=host \
    --restart unless-stopped \
    --name "$container" \
    "${env_args[@]}" \
    "$image" >/dev/null

  # Narnia.sh waits 3s before assigning IP / bringing iface up.
  sleep 3
  apply_tunnel_firewall "$role" "$iface"
  if [[ ! "${op_mode}" =~ ^ip: ]]; then
    assign_interface_ip "$iface" "$local_ip" "$mtu"
  else
    ip link set "$iface" up 2>/dev/null || true
  fi
  if [ "$role" = "iran" ]; then
    apply_port_forwards "$port_forwards"
  fi

  if ! docker inspect -f '{{.State.Running}}' "$container" 2>/dev/null | grep -qi true; then
    docker logs --tail 30 "$container" || true
    die "container failed to stay running"
  fi

  CONTAINER_NAME="$container"
  INTERFACE="$iface"
  LOCAL_IP="$local_ip"
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
  local host latency_ms packet_loss_pct peer
  host="$(hostname -f 2>/dev/null || hostname)"
  peer="$(peer_tunnel_ip "${LOCAL_IP:-}")"
  read -r latency_ms packet_loss_pct <<<"$(measure_peer_ping "$peer")"
  local body
  body=$(jq -nc \
    --arg s "$status" \
    --arg h "$host" \
    --arg m "$message" \
    --argjson up "$bytes_up" \
    --argjson down "$bytes_down" \
    --argjson cr "$running" \
    --argjson iu "$iface_up" \
    --arg lat "$latency_ms" \
    --arg loss "$packet_loss_pct" \
    '{
      status:$s,
      host:$h,
      message:(if $m=="" then null else $m end),
      bytes_up:$up,
      bytes_down:$down,
      container_running:$cr,
      interface_up:$iu,
      latency_ms:(if $lat=="null" or $lat=="" then null else ($lat|tonumber) end),
      packet_loss_pct:(if $loss=="null" or $loss=="" then null else ($loss|tonumber) end)
    }')
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
  keepalive=$(ask_val "Keepalive seconds" "20")
  mtu=$(ask_val "MTU" "1000")
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
      role:"iran",
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
ROLE=iran
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
  echo -e "${c_bld}${c_grn}Manual IRAN tunnel is up.${c_off}"
  echo "  remote : ${remote_ip}"
  echo "  later  : sudo hpx-tunnel-agent"
  echo
  _read -r -p "Press Enter to continue..." _
}

# FOREIGN server on Node VPS — same steps as official Narnia.sh start_logic.
wizard_foreign() {
  need_root
  ensure_deps
  banner
  echo -e "  ${c_bld}FOREIGN tunnel (Node / abroad VPS)${c_off}"
  echo -e "  ${c_dim}Listens for IRAN agent. Stop native narnia_tunnel if it is still running.${c_off}"
  echo

  local password iface local_ip keepalive mtu image container server_listen
  password=$(ask_secret "Shared tunnel password (same as IRAN side)")
  iface=$(ask_val "Tunnel interface name" "hpx0")
  local_ip=$(ask_val "Local tunnel IP on this FOREIGN server" "10.200.200.1")
  server_listen=$(ask_val "Listen address" "0.0.0.0")
  keepalive=$(ask_val "Keepalive seconds" "20")
  mtu=$(ask_val "MTU" "1000")
  image=$(ask_val "Docker image" "$DEFAULT_IMAGE")
  container=$(ask_val "Container name" "hpx_tunnel_foreign")

  echo
  hr
  echo -e "  ${c_bld}Summary${c_off}"
  echo "  role      : FOREIGN (SERVER=${server_listen})"
  echo "  interface : ${iface}"
  echo "  local IP  : ${local_ip}"
  echo "  image     : ${image}"
  hr
  if ! ask_yn "Start FOREIGN tunnel?" "y"; then
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
    --argjson mtu "$mtu" \
    --arg local_ip "$local_ip" \
    --arg listen "$server_listen" \
    '{
      role:"foreign",
      docker_image:$image,
      container_name:$container,
      interface:$iface,
      password:$password,
      keepalive:$keepalive,
      mtu:$mtu,
      local_ip:$local_ip,
      server_listen:$listen,
      port_forwards:[],
      config_hash:"manual-foreign"
    }')

  install_self
  mkdir -p "$ETC_DIR"
  cat >"$MANUAL_ENV" <<EOF
ROLE=foreign
SERVER_LISTEN=${server_listen}
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
  echo -e "${c_bld}${c_grn}FOREIGN tunnel is up.${c_off}"
  echo "  local  : ${local_ip}  iface=${iface}"
  echo "  IRAN remote_ip must be THIS server's public IP"
  echo "  later  : sudo hpx-tunnel-agent"
  echo
  _read -r -p "Press Enter to continue..." _
}

cmd_foreign() {
  need_root
  ensure_deps
  local password="" iface="hpx0" local_ip="10.200.200.1" keepalive="20" mtu="1000" listen="0.0.0.0" container="hpx_tunnel_foreign"
  while [ $# -gt 0 ]; do
    case "$1" in
      --password) password="${2:-}"; shift 2 ;;
      --password=*) password="${1#*=}"; shift ;;
      --interface) iface="${2:-}"; shift 2 ;;
      --interface=*) iface="${1#*=}"; shift ;;
      --local-ip) local_ip="${2:-}"; shift 2 ;;
      --local-ip=*) local_ip="${1#*=}"; shift ;;
      --keepalive) keepalive="${2:-}"; shift 2 ;;
      --keepalive=*) keepalive="${1#*=}"; shift ;;
      --mtu) mtu="${2:-}"; shift 2 ;;
      --mtu=*) mtu="${1#*=}"; shift ;;
      --listen) listen="${2:-}"; shift 2 ;;
      --listen=*) listen="${1#*=}"; shift ;;
      --container) container="${2:-}"; shift 2 ;;
      --container=*) container="${1#*=}"; shift ;;
      -*) die "unknown flag: $1" ;;
      *) die "unexpected arg: $1" ;;
    esac
  done
  [ -n "$password" ] || die "foreign requires --password"

  MODE="manual"
  PANEL_URL=""
  AGENT_KEY=""
  local cfg
  cfg=$(jq -nc \
    --arg image "$DEFAULT_IMAGE" \
    --arg container "$container" \
    --arg iface "$iface" \
    --arg password "$password" \
    --argjson keepalive "$keepalive" \
    --argjson mtu "$mtu" \
    --arg local_ip "$local_ip" \
    --arg listen "$listen" \
    '{
      role:"foreign",
      docker_image:$image,
      container_name:$container,
      interface:$iface,
      password:$password,
      keepalive:$keepalive,
      mtu:$mtu,
      local_ip:$local_ip,
      server_listen:$listen,
      port_forwards:[],
      config_hash:"manual-foreign"
    }')
  install_self
  mkdir -p "$ETC_DIR"
  cat >"$MANUAL_ENV" <<EOF
ROLE=foreign
SERVER_LISTEN=${listen}
PASSWORD=${password}
INTERFACE=${iface}
LOCAL_IP=${local_ip}
KEEPALIVE=${keepalive}
MTU=${mtu}
DOCKER_IMAGE=${DEFAULT_IMAGE}
CONTAINER_NAME=${container}
EOF
  chmod 600 "$MANUAL_ENV"
  start_tunnel_from_config "$cfg"
  install_systemd
  log "FOREIGN up — ${local_ip} on ${iface}"
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
        --arg remote_ip "${REMOTE_IP:-}" \
        --argjson mtu "${MTU}" \
        --arg local_ip "${LOCAL_IP}" \
        --arg role "${ROLE:-iran}" \
        --arg listen "${SERVER_LISTEN:-0.0.0.0}" \
        '{role:$role,docker_image:$image,container_name:$container,interface:$iface,password:$password,keepalive:$keepalive,remote_ip:$remote_ip,mtu:$mtu,local_ip:$local_ip,server_listen:$listen,port_forwards:[],config_hash:"manual"}')
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

  # Panel doctor: full remote heal on Iran host (allowlisted steps only).
  if [ "$command" = "smart_fix" ] || [ "$command" = "diagnose" ]; then
    local container iface remote_ip local_ip peer loss_info
    container=$(echo "$cfg" | jq -r '.container_name')
    iface=$(echo "$cfg" | jq -r '.interface')
    remote_ip=$(echo "$cfg" | jq -r '.remote_ip // empty')
    local_ip=$(echo "$cfg" | jq -r '.local_ip // empty')
    sysctl -w net.ipv4.icmp_echo_ignore_all=1 >/dev/null 2>&1 || true
    sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true
    stop_conflicting_tunnels "$container" "$iface"
    if [ "$command" = "smart_fix" ]; then
      start_tunnel_from_config "$cfg"
      peer="$(peer_tunnel_ip "$local_ip")"
      loss_info="$(measure_peer_ping "$peer")"
      ack_command "smart_fix" "running" "doctor: narnia-parity restart peer=${peer} ping=${loss_info}"
      heartbeat "running" "doctor smart_fix ok" >/dev/null || true
    else
      apply_tunnel_firewall "iran" "$iface"
      peer="$(peer_tunnel_ip "${LOCAL_IP:-$local_ip}")"
      loss_info="$(measure_peer_ping "$peer")"
      local running="false" icmp_ignore
      icmp_ignore="$(sysctl -n net.ipv4.icmp_echo_ignore_all 2>/dev/null || echo '?')"
      if [ -n "${CONTAINER_NAME:-$container}" ] && docker inspect -f '{{.State.Running}}' "${CONTAINER_NAME:-$container}" 2>/dev/null | grep -qi true; then
        running="true"
      fi
      ack_command "diagnose" "running" "doctor diagnose: running=${running} icmp_ignore=${icmp_ignore} remote=${remote_ip} peer=${peer} ping=${loss_info}"
      heartbeat "running" >/dev/null || true
    fi
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
    stop_conflicting_tunnels "$(echo "$cfg" | jq -r '.container_name')" "$(echo "$cfg" | jq -r '.interface')"
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
      --arg remote_ip "${REMOTE_IP:-}" \
      --argjson mtu "${MTU}" \
      --arg local_ip "${LOCAL_IP}" \
      --arg role "${ROLE:-iran}" \
      --arg listen "${SERVER_LISTEN:-0.0.0.0}" \
      '{role:$role,docker_image:$image,container_name:$container,interface:$iface,password:$password,keepalive:$keepalive,remote_ip:$remote_ip,mtu:$mtu,local_ip:$local_ip,server_listen:$listen,port_forwards:[],config_hash:"manual"}')
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
    echo -e "  ${c_bld}1)${c_off} Connect with panel join token ${c_dim}(IRAN)${c_off}"
    echo -e "  ${c_bld}2)${c_off} Manual IRAN setup (ask IP / password)"
    echo -e "  ${c_bld}3)${c_off} FOREIGN setup on this Node VPS ${c_dim}(Narnia parity)${c_off}"
    echo -e "  ${c_bld}4)${c_off} Status"
    echo -e "  ${c_bld}5)${c_off} Logs"
    echo -e "  ${c_bld}6)${c_off} Restart tunnel"
    echo -e "  ${c_bld}7)${c_off} Uninstall"
    echo -e "  ${c_bld}0)${c_off} Exit"
    echo
    local choice
    _read -r -p "$(echo -e "${c_bld}Select${c_off} [0-7]: ")" choice
    case "${choice:-}" in
      1) wizard_join_panel ;;
      2) wizard_manual ;;
      3) wizard_foreign ;;
      4) cmd_status ;;
      5) cmd_logs ;;
      6) cmd_restart; _read -r -p "Press Enter..." _ ;;
      7)
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
HPX ICMP Tunnel Agent (IRAN + FOREIGN)

Interactive menu (default):
  curl -fsSL https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-tunnel-agent.sh | sudo bash
  sudo hpx-tunnel-agent

Commands:
  menu                         Interactive installer / management
  join [TOKEN] [--panel-url]   Non-interactive panel join (IRAN)
  foreign --password SECRET    Start FOREIGN on this Node (Narnia parity)
  sync | status | logs | restart | uninstall

FOREIGN one-liner (Node VPS):
  curl -fsSL .../hpx-tunnel-agent.sh | sudo bash -s -- foreign --password 'YOUR_PASSWORD'

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
    foreign) cmd_foreign "$@" ;;
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

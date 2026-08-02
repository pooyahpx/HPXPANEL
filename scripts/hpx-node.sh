#!/usr/bin/env bash
#
# HPXPANEL Node — edge installer
# -----------------------------
# Installs an HPX-compatible multi-backend node (Xray / WireGuard / OpenVPN / IKEv2)
# as a Docker container, then prints Address + Port + API key + Server CA for
# HPXPANEL -> Nodes.
#
# One-liner (Linux):
#   sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXNODE/raw/main/scripts/install.sh)" @ install -y
#
# Interactive menu:
#   sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXNODE/raw/main/scripts/install.sh)"
#
set -euo pipefail

# When invoked as: bash -c "$(curl ...)" @ install ...
# the "@" is arg noise from one-liners — strip it.
if [ "${1:-}" = "@" ]; then shift; fi

PANEL_DOCS="${PANEL_DOCS:-https://pooyahpx.github.io/HPXPANEL/}"
PANEL_REPO="${PANEL_REPO:-https://github.com/pooyahpx/HPXPANEL}"
REPO="${REPO:-https://github.com/pooyahpx/HPXNODE}"
IMAGE="${IMAGE:-ghcr.io/pooyahpx/hpx-node:latest}"
FALLBACK_IMAGE="${FALLBACK_IMAGE:-ghcr.io/pooyahpx/hpx-node:latest}"
BRANCH="${BRANCH:-main}"

SERVICE="${SERVICE:-hpx-node}"
NODE_NAME="${NODE_NAME:-}"
INSTALL_DIR="${INSTALL_DIR:-/opt/hpx-node}"
COMPOSE_FILE="$INSTALL_DIR/docker-compose.yml"
DATA_DIR="${DATA_DIR:-/var/lib/hpx-node}"
CONTAINER_DATA="/var/lib/hpx-node"

SERVICE_PORT="${SERVICE_PORT:-62050}"
API_KEY=""
BUILD_FROM_SOURCE=0
ASSUME_YES=0
QUIET="${QUIET:-0}"

XRAY_ON=1; OVPN_ON=1; WG_ON=1; IKEV2_ON=1

if [ -t 1 ]; then
  c_grn='\033[0;32m'; c_yel='\033[0;33m'; c_red='\033[0;31m'
  c_cyn='\033[0;36m'; c_mag='\033[0;35m'; c_blu='\033[0;34m'
  c_bld='\033[1m'; c_dim='\033[2m'; c_off='\033[0m'
  c_amb='\033[38;5;214m'
else
  c_grn=''; c_yel=''; c_red=''; c_cyn=''; c_mag=''; c_blu=''
  c_bld=''; c_dim=''; c_off=''; c_amb=''
fi
log()  { echo -e "${c_grn}[+]${c_off} $*"; }
warn() { echo -e "${c_yel}[!]${c_off} $*"; }
err()  { echo -e "${c_red}[x]${c_off} $*" >&2; }
die()  { err "$*"; exit 1; }
hr()   { echo -e "${c_cyn}------------------------------------------------------------${c_off}"; }
has()  { command -v "$1" >/dev/null 2>&1; }

_read() { if [ -e /dev/tty ]; then read "$@" </dev/tty || true; else read "$@" || true; fi; }

STEP_LOG="/tmp/hpx-node-install.log"

run_step() {
  local msg="$1"; shift
  echo -ne "  ${c_cyn}>${c_off} ${msg} ${c_dim}...${c_off} "
  if "$@" >>"$STEP_LOG" 2>&1; then
    echo -e "${c_grn}done${c_off}"
  else
    echo -e "${c_red}failed${c_off}"
    err "step failed: ${msg}"; err "last lines of ${STEP_LOG}:"; tail -n 12 "$STEP_LOG" >&2 || true
    exit 1
  fi
}

_rule() { echo -e "${c_dim}    ------------------------------------------------${c_off}"; }

_stream() {
  local fd rc
  if [ -t 1 ]; then
    "$@"; rc=$?
  else
    exec {fd}> >(tee -a "$STEP_LOG" | sed "s/^/    /")
    "$@" >&"$fd" 2>&1
    rc=$?
    exec {fd}>&-
    wait 2>/dev/null || true
  fi
  return $rc
}

run_step_live() {
  local msg="$1"; shift
  if [ "${QUIET:-0}" = "1" ]; then run_step "$msg" "$@"; return; fi
  echo -e "  ${c_cyn}>${c_off} ${c_bld}${msg}${c_off}"
  _rule
  if _stream "$@"; then
    _rule; echo -e "  ${c_grn}OK${c_off} ${msg}"
  else
    _rule; echo -e "  ${c_red}FAIL${c_off} ${msg}"
    err "step failed: ${msg} (full log: ${STEP_LOG})"
    exit 1
  fi
}

run_step_live_soft() {
  local msg="$1"; shift
  if [ "${QUIET:-0}" = "1" ]; then run_step_soft "$msg" "$@"; return; fi
  echo -e "  ${c_cyn}>${c_off} ${c_bld}${msg}${c_off}"
  _rule
  if _stream "$@"; then
    echo -e "  ${c_grn}OK${c_off} ${msg}"; return 0
  else
    echo -e "  ${c_yel}skip${c_off} ${msg}"; return 1
  fi
}

run_step_soft() {
  local msg="$1"; shift
  echo -ne "  ${c_cyn}>${c_off} ${msg} ${c_dim}...${c_off} "
  if "$@" >>"$STEP_LOG" 2>&1; then echo -e "${c_grn}done${c_off}"; return 0
  else echo -e "${c_yel}skipped${c_off}"; return 1; fi
}

ask_yn() {
  local q="$1" ans
  while true; do
    _read -r -p "$(echo -e "${c_bld}${q}${c_off} (y/n, Enter = no): ")" ans
    case "${ans:-n}" in
      [Yy]|[Yy][Ee][Ss]) return 0 ;;
      [Nn]|[Nn][Oo])     return 1 ;;
      *) warn "Please type only 'y' or 'n'." ;;
    esac
  done
}
ask_val() {
  local q="$1" def="$2" ans
  _read -r -p "$(echo -e "${c_bld}${q}${c_off}${def:+ [${def}]}: ")" ans
  echo "${ans:-$def}"
}
ask_num() {
  local q="$1" def="$2" ans
  while true; do
    _read -r -p "$(echo -e "${c_bld}${q}${c_off} [${def}]: ")" ans
    ans="${ans:-$def}"
    if [[ "$ans" =~ ^[0-9]+$ ]] && [ "$ans" -ge 1 ] && [ "$ans" -le 65535 ]; then echo "$ans"; return; fi
    warn "Please enter a port between 1 and 65535."
  done
}

require_root() { [ "$(id -u)" -eq 0 ] || die "run as root (sudo)"; }
gen_uuid() { [ -r /proc/sys/kernel/random/uuid ] && cat /proc/sys/kernel/random/uuid || (has uuidgen && uuidgen) || die "cannot generate a UUID"; }

COMPOSE_CMD=""
detect_compose() {
  if docker compose version >/dev/null 2>&1; then COMPOSE_CMD="docker compose"
  elif has docker-compose; then COMPOSE_CMD="docker-compose"
  else return 1; fi
}
dc() { ( cd "$INSTALL_DIR" && $COMPOSE_CMD -p "$SERVICE" -f "$COMPOSE_FILE" "$@" ); }

# Sanitize --name and map paths so many nodes can live on one host.
apply_instance() {
  if [ -z "$NODE_NAME" ]; then
    SERVICE="${SERVICE:-hpx-node}"
  else
    NODE_NAME="$(echo "$NODE_NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9-]+/-/g; s/^-+//; s/-+$//; s/-+/-/g')"
    [ -n "$NODE_NAME" ] || die "invalid --name"
    case "$NODE_NAME" in
      hpx-node|hpx-node-*) SERVICE="$NODE_NAME" ;;
      *) SERVICE="hpx-node-${NODE_NAME}" ;;
    esac
  fi
  INSTALL_DIR="/opt/${SERVICE}"
  DATA_DIR="/var/lib/${SERVICE}"
  COMPOSE_FILE="$INSTALL_DIR/docker-compose.yml"
}

port_in_use_by_other_instance() {
  local port="$1" dir f other
  for dir in /opt/hpx-node /opt/hpx-node-*; do
    [ -d "$dir" ] || continue
    f="$dir/docker-compose.yml"
    [ -f "$f" ] || continue
    other="$(basename "$dir")"
    [ "$other" = "$SERVICE" ] && continue
    if grep -E "SERVICE_PORT:[[:space:]]*${port}([[:space:]]|$)" "$f" >/dev/null 2>&1; then
      echo "$other"
      return 0
    fi
  done
  return 1
}

assert_port_free() {
  local conflict
  conflict="$(port_in_use_by_other_instance "$SERVICE_PORT" || true)"
  if [ -n "$conflict" ]; then
    die "Node port ${SERVICE_PORT} is already used by instance '${conflict}'. Pick another --service-port."
  fi
  if has ss; then
    if ss -lntu 2>/dev/null | awk '{print $5}' | grep -E "[:.]${SERVICE_PORT}\$" >/dev/null 2>&1; then
      warn "Port ${SERVICE_PORT} looks busy on this host — install may still work if it is the same container being replaced."
    fi
  fi
}

install_compose_binary() {
  local arch bin_url bin_path
  arch="$(uname -m)"
  case "$arch" in
    x86_64|amd64) arch="x86_64" ;;
    aarch64|arm64) arch="aarch64" ;;
    armv7l) arch="armv7" ;;
    *)
      warn "Unsupported arch for Compose binary: $(uname -m)"
      return 1
      ;;
  esac
  has curl || return 1
  bin_path="/usr/local/lib/docker/cli-plugins/docker-compose"
  mkdir -p "$(dirname "$bin_path")"
  bin_url="https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-${arch}"
  log "Downloading Compose v2 plugin (no apt needed)..."
  if curl -fsSL "$bin_url" -o "$bin_path"; then
    chmod +x "$bin_path"
    ln -sfn "$bin_path" /usr/local/bin/docker-compose 2>/dev/null || true
    return 0
  fi
  return 1
}

ensure_compose() {
  if detect_compose; then return 0; fi

  log "Docker Compose plugin missing — installing..."

  # Never wait on apt here — binary install is enough.
  if apt_busy 2>/dev/null; then
    warn "apt is busy ($(apt_holder 2>/dev/null || echo locked)) — using binary Compose install"
  fi
  install_compose_binary || true
  if detect_compose; then
    log "Docker Compose ready ($COMPOSE_CMD)"
    return 0
  fi

  if has apt-get && ! apt_busy; then
    DEBIAN_FRONTEND=noninteractive apt-get update -y >/dev/null 2>&1 || true
    DEBIAN_FRONTEND=noninteractive apt-get install -y docker-compose-plugin >/dev/null 2>&1 \
      || DEBIAN_FRONTEND=noninteractive apt-get install -y docker-compose-v2 >/dev/null 2>&1 \
      || true
  elif has dnf; then
    dnf install -y docker-compose-plugin >/dev/null 2>&1 || true
  elif has yum; then
    yum install -y docker-compose-plugin >/dev/null 2>&1 || true
  elif has apk; then
    apk add --no-cache docker-cli-compose >/dev/null 2>&1 || true
  fi

  if detect_compose; then
    log "Docker Compose ready ($COMPOSE_CMD)"
    return 0
  fi

  die "docker compose plugin not available. Run:
  sudo mkdir -p /usr/local/lib/docker/cli-plugins
  sudo curl -fsSL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
  sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose"
}

force_free_apt() {
  systemctl stop unattended-upgrades.service 2>/dev/null || true
  systemctl stop unattended-upgrades.timer 2>/dev/null || true
  systemctl kill --kill-who=all unattended-upgrades.service 2>/dev/null || true

  # IMPORTANT: never `pkill -f <pattern>` — when installed via
  #   bash -c "$(curl ... install.sh)"
  # the whole script text is in cmdline, so -f matches and kills THIS installer.
  local pid
  if has pgrep; then
    for pid in $(pgrep -x apt-get 2>/dev/null; pgrep -x apt 2>/dev/null; pgrep -x dpkg 2>/dev/null); do
      [ "$pid" = "$$" ] && continue
      [ "$pid" = "$PPID" ] && continue
      kill -9 "$pid" 2>/dev/null || true
    done
    # unattended-upgrade is often a python process — match by exact comm when possible
    for pid in $(pgrep -f '^/usr/bin/unattended-upgrade' 2>/dev/null; pgrep -x unattended-upgrade 2>/dev/null); do
      [ "$pid" = "$$" ] && continue
      kill -9 "$pid" 2>/dev/null || true
    done
  fi

  rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock \
    /var/lib/apt/lists/lock /var/cache/apt/archives/lock \
    /var/cache/apt/archives/lock.bin 2>/dev/null || true
  DEBIAN_FRONTEND=noninteractive dpkg --configure -a >/dev/null 2>&1 || true
}

# No sleeping / no multi-second waits — unlock once or skip apt entirely.
wait_for_apt() {
  has apt-get || return 0
  apt_busy || return 0
  warn "apt busy ($(apt_holder)) — unlocking immediately (no wait)"
  force_free_apt
  apt_busy && return 1
  return 0
}

install_docker_static() {
  local arch tarball url ver="27.5.1" tmp
  arch="$(uname -m)"
  case "$arch" in
    x86_64|amd64) arch="x86_64" ;;
    aarch64|arm64) arch="aarch64" ;;
    *)
      warn "No static Docker package for arch $(uname -m)"
      return 1
      ;;
  esac
  has curl || return 1
  ver="${DOCKER_STATIC_VERSION:-$ver}"
  url="https://download.docker.com/linux/static/stable/${arch}/docker-${ver}.tgz"
  tmp="$(mktemp -d)"
  log "Installing Docker from static binaries (instant path, no apt)..."
  if ! curl -fsSL "$url" -o "$tmp/docker.tgz"; then
    rm -rf "$tmp"
    return 1
  fi
  tar -xzf "$tmp/docker.tgz" -C "$tmp"
  cp -f "$tmp"/docker/* /usr/bin/ 2>/dev/null || cp -f "$tmp"/docker/docker* /usr/bin/
  rm -rf "$tmp"

  if [ -d /run/systemd/system ] && [ ! -f /etc/systemd/system/docker.service ] && [ ! -f /lib/systemd/system/docker.service ]; then
    cat > /etc/systemd/system/docker.service <<'UNIT'
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStart=/usr/bin/dockerd
ExecReload=/bin/kill -s HUP $MAINPID
LimitNOFILE=1048576
LimitNPROC=infinity
LimitCORE=infinity
Delegate=yes
KillMode=process
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
UNIT
    systemctl daemon-reload 2>/dev/null || true
  fi
  systemctl enable --now docker 2>/dev/null || dockerd >/var/log/dockerd.log 2>&1 &
  # brief readiness poll (max ~3s total), not an apt wait
  local i
  for i in 1 2 3 4 5 6; do
    docker info >/dev/null 2>&1 && return 0
    sleep 0.5
  done
  has docker
}

install_docker() {
  if has docker; then
    systemctl enable --now docker 2>/dev/null || true
    ensure_compose
    return 0
  fi

  # Instant path: never call apt / get.docker.com (those stall on VPS unattended-upgrades).
  if apt_busy; then
    warn "apt busy — unlocking and using static Docker (no wait)"
    force_free_apt
  fi
  if ! install_docker_static; then
    warn "static Docker failed — last resort get.docker.com"
    force_free_apt
    curl -fsSL https://get.docker.com | sh || true
    systemctl enable --now docker 2>/dev/null || true
  fi

  has docker || die "Docker engine is not installed"
  ensure_compose
}

apt_busy() {
  local f
  for f in /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock \
           /var/lib/apt/lists/lock /var/cache/apt/archives/lock; do
    [ -e "$f" ] || continue
    if has fuser; then
      fuser "$f" >/dev/null 2>&1 && return 0
    elif has lsof; then
      lsof "$f" >/dev/null 2>&1 && return 0
    fi
  done
  if has pgrep; then
    pgrep -x apt >/dev/null 2>&1 && return 0
    pgrep -x apt-get >/dev/null 2>&1 && return 0
    pgrep -x dpkg >/dev/null 2>&1 && return 0
    pgrep -f unattended-upgr >/dev/null 2>&1 && return 0
    pgrep -f 'apt.systemd.daily' >/dev/null 2>&1 && return 0
  fi
  return 1
}

apt_holder() {
  local f p
  for f in /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock \
           /var/lib/apt/lists/lock /var/cache/apt/archives/lock; do
    [ -e "$f" ] || continue
    if has fuser; then
      p=$(fuser "$f" 2>/dev/null | tr -s ' ' '\n' | grep -E '^[0-9]+$' | head -1)
      [ -n "$p" ] && { ps -o comm= -p "$p" 2>/dev/null | tail -1; return; }
    elif has lsof; then
      p=$(lsof -t "$f" 2>/dev/null | head -1)
      [ -n "$p" ] && { ps -o comm= -p "$p" 2>/dev/null | tail -1; return; }
    fi
  done
  if has pgrep; then
    for p in unattended-upgr apt-get apt dpkg; do
      if pgrep -x "$p" >/dev/null 2>&1 || pgrep -f "$p" >/dev/null 2>&1; then
        echo "$p"; return
      fi
    done
  fi
  echo "stale-or-unknown-lock"
}

banner() {
  clear 2>/dev/null || true
  echo
  echo -e "  ${c_cyn}${c_bld}+----------------------------------------------------------+${c_off}"
  echo -e "  ${c_cyn}${c_bld}|${c_off}  ${c_amb}${c_bld}HPX${c_off}${c_bld}PANEL${c_off}  ${c_dim}//${c_off}  ${c_cyn}NODE DEPLOY${c_off}                         ${c_cyn}${c_bld}|${c_off}"
  echo -e "  ${c_cyn}${c_bld}+----------------------------------------------------------+${c_off}"
  echo
  echo -e "  ${c_dim}Edge node for${c_off} ${c_bld}HPXPANEL${c_off}${c_dim}. After install, paste Address / Port / API key / CA into the panel.${c_off}"
  echo
}

features_panel() {
  echo -e "  ${c_bld}Backends${c_off}"
  echo -e "  ${c_dim}- Xray         VLESS / VMess / Trojan / SS / REALITY${c_off}"
  echo -e "  ${c_dim}- WireGuard    kernel WG + host NAT${c_off}"
  echo -e "  ${c_dim}- OpenVPN      optional tunnel${c_off}"
  echo -e "  ${c_dim}- IKEv2/IPsec  strongSwan${c_off}"
  echo -e "  ${c_dim}- Panel sync   gRPC -> HPXPANEL Nodes${c_off}"
  echo
}

usage() {
  cat <<EOF
HPXPANEL Node — Docker installer (hpx-node)

Usage:
  sudo bash install.sh [command] [options]
  sudo bash -c "\$(curl -fsSL ${REPO}/raw/main/scripts/install.sh)" @ install -y

Commands:
  (none) / menu     Interactive menu
  install           Install / reinstall (use -y for no prompts)
  list              List all node instances on this server
  update | restart | status | logs
  uninstall

Install options:
  --name <id>        Instance name for multi-node on one server
                     (paths: /opt/hpx-node-<id> , CLI: hpx-node --name <id>)
  --disable <list>   xray,openvpn,wireguard,ikev2 (comma)
  --api-key <uuid>   (default: auto-generate)
  --service-port <n> panel "Node Port" (default: ${SERVICE_PORT})
  --image <ref>      pull image (default: ${IMAGE})
  --build            build from source instead of pull
  --branch <name> | --repo <url>
  -y, --yes          non-interactive install
  -q, --quiet
  -h, --help

Multi-node examples (same server, different gRPC ports — sell as separate panel nodes):
  sudo bash install.sh install -y --name shop1 --service-port 62051
  sudo bash install.sh install -y --name shop2 --service-port 62052
  sudo bash install.sh list
  sudo bash install.sh --name shop1 status

Note: host networking is shared. Give each panel node different inbound/VPN ports
in HPXPANEL so WireGuard / OpenVPN / IKEv2 do not collide on this host.

Docs: ${PANEL_DOCS}
Log : ${STEP_LOG}
EOF
}

parse_install_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --name|--instance)
        NODE_NAME="$2"; shift 2 ;;
      --disable)
        local d=",$2,"
        echo "$d" | grep -qi ",xray,"      && XRAY_ON=0
        echo "$d" | grep -qi ",openvpn,"   && OVPN_ON=0
        echo "$d" | grep -qi ",wireguard," && WG_ON=0
        echo "$d" | grep -qi ",ikev2,"     && IKEV2_ON=0
        shift 2 ;;
      --api-key) API_KEY="$2"; shift 2 ;;
      --service-port|--port) SERVICE_PORT="$2"; shift 2 ;;
      --image) IMAGE="$2"; shift 2 ;;
      --build) BUILD_FROM_SOURCE=1; shift ;;
      --branch) BRANCH="$2"; shift 2 ;;
      --repo) REPO="$2"; shift 2 ;;
      -y|--yes) ASSUME_YES=1; shift ;;
      -q|--quiet) QUIET=1; shift ;;
      -h|--help) usage; exit 0 ;;
      *) die "unknown option: $1 (see --help)" ;;
    esac
  done
  apply_instance
}

onoff() { if [ "${1:-0}" -eq 1 ]; then echo -e "${c_grn}${c_bld}ON${c_off}"; else echo -e "${c_dim}off${c_off}"; fi; }
press_enter() { echo; _read -r -p "$(echo -e "  ${c_dim}Press Enter to return...${c_off}")" _; }

menu_command() {
  require_root
  if [ ! -e /dev/tty ] && [ ! -t 0 ]; then
    die "no terminal for the menu — use:
  sudo bash install.sh install -y --name shop1 --service-port 62051"
  fi
  apply_instance
  local status="not installed"
  has docker && docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$SERVICE" && \
    status="installed ($(docker inspect -f '{{.State.Status}}' "$SERVICE" 2>/dev/null))"

  while true; do
    banner
    features_panel
    echo -e "  ${c_dim}Instance:${c_off} ${c_bld}${SERVICE}${c_off}   ${c_dim}Port:${c_off} ${c_cyn}${SERVICE_PORT}${c_off}"
    echo -e "  ${c_dim}State:${c_off} ${c_bld}${status}${c_off}"
    echo -e "  ${c_dim}Image:${c_off} $([ "$BUILD_FROM_SOURCE" = 1 ] && echo 'build from source' || echo "$IMAGE")"
    echo
    echo -e "  ${c_bld}BACKENDS${c_off} ${c_dim}(toggle)${c_off}"
    printf "    ${c_bld}1${c_off}  %-24s %b\n" "Xray"               "$(onoff "$XRAY_ON")"
    printf "    ${c_bld}2${c_off}  %-24s %b\n" "OpenVPN"            "$(onoff "$OVPN_ON")"
    printf "    ${c_bld}3${c_off}  %-24s %b\n" "WireGuard"          "$(onoff "$WG_ON")"
    printf "    ${c_bld}4${c_off}  %-24s %b\n" "IKEv2 / IPsec"      "$(onoff "$IKEV2_ON")"
    echo
    echo -e "  ${c_bld}LINK TO PANEL${c_off}"
    printf "    ${c_bld}5${c_off}  %-24s ${c_cyn}%s${c_off}\n" "Node port (gRPC)" "$SERVICE_PORT"
    printf "    ${c_bld}6${c_off}  %-24s ${c_cyn}%s${c_off}\n" "API key"          "${API_KEY:-auto-generate}"
    printf "    ${c_bld}7${c_off}  %-24s ${c_cyn}%s${c_off}\n" "Image source"     "$([ "$BUILD_FROM_SOURCE" = 1 ] && echo 'build from source' || echo 'pull')"
    printf "    ${c_bld}8${c_off}  %-24s ${c_cyn}%s${c_off}\n" "Instance name"    "${NODE_NAME:-default}"
    echo -e "    ${c_dim}VPN ports come from HPXPANEL core config. Multi-node = unique gRPC + VPN ports.${c_off}"
    echo
    echo -e "  ${c_bld}ACTIONS${c_off}"
    echo -e "    ${c_grn}${c_bld}i${c_off}  ${c_bld}Install / reinstall${c_off}   ${c_dim}<-- type i then Enter${c_off}"
    echo -e "    ${c_bld}u${c_off} Update   ${c_bld}s${c_off} Status   ${c_bld}l${c_off} Logs   ${c_bld}r${c_off} Restart   ${c_bld}p${c_off} List"
    echo -e "    ${c_red}x${c_off} Uninstall   ${c_bld}q${c_off} Quit"
    echo
    local choice
    _read -r -p "$(echo -e "  ${c_bld}Select${c_off} ${c_dim}(number / letter)${c_off} > ")" choice
    case "$choice" in
      1) XRAY_ON=$((1 - XRAY_ON)) ;;
      2) OVPN_ON=$((1 - OVPN_ON)) ;;
      3) WG_ON=$((1 - WG_ON)) ;;
      4) IKEV2_ON=$((1 - IKEV2_ON)) ;;
      5) SERVICE_PORT="$(ask_num "Node port (gRPC — panel Node Port)" "$SERVICE_PORT")" ;;
      6) API_KEY="$(ask_val "API key (blank = auto-generate)" "$API_KEY")" ;;
      7) BUILD_FROM_SOURCE=$((1 - BUILD_FROM_SOURCE)) ;;
      8)
        NODE_NAME="$(ask_val "Instance name (blank = default single node)" "$NODE_NAME")"
        apply_instance
        status="not installed"
        has docker && docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$SERVICE" && \
          status="installed ($(docker inspect -f '{{.State.Status}}' "$SERVICE" 2>/dev/null))"
        ;;
      i|I) echo; run_install; break ;;
      u|U) echo; update_command; press_enter ;;
      s|S) echo; status_command; press_enter ;;
      l|L) echo; logs_command ;;
      r|R) echo; restart_command; press_enter ;;
      p|P) echo; list_command; press_enter ;;
      x|X) echo; uninstall_command; press_enter; status="not installed" ;;
      q|Q) echo; exit 0 ;;
      "") : ;;
      *) warn "Unknown: '${choice}' — type ${c_bld}i${c_off} to install"; sleep 1 ;;
    esac
  done
}

write_compose() {
  mkdir -p "$INSTALL_DIR" "$DATA_DIR"
  chmod 700 "$DATA_DIR" 2>/dev/null || true
  {
    echo "services:"
    echo "  node:"
    if [ "$BUILD_FROM_SOURCE" = 1 ]; then
      echo "    build: ${REPO}.git#${BRANCH}"
    else
      echo "    image: ${IMAGE}"
    fi
    echo "    container_name: ${SERVICE}"
    echo "    restart: always"
    echo "    network_mode: host"
    echo "    cap_add:"
    echo "      - NET_ADMIN"
    echo "      - SYS_MODULE"
    echo "    devices:"
    echo "      - /dev/net/tun"
    echo "    environment:"
    echo "      API_KEY: \"${API_KEY}\""
    echo "      SERVICE_PORT: ${SERVICE_PORT}"
    echo "      SERVICE_PROTOCOL: \"grpc\""
    echo "      HPX_NODE_WG_HOST_ROUTING: \"1\""
    [ "$XRAY_ON"  -eq 0 ] && echo "      HPX_NODE_DISABLE_XRAY: \"1\""
    [ "$OVPN_ON"  -eq 0 ] && echo "      HPX_NODE_DISABLE_OPENVPN: \"1\""
    [ "$WG_ON"    -eq 0 ] && echo "      HPX_NODE_DISABLE_WIREGUARD: \"1\""
    [ "$IKEV2_ON" -eq 0 ] && echo "      HPX_NODE_DISABLE_IKEV2: \"1\""
    echo "    volumes:"
    echo "      - /lib/modules:/lib/modules:ro"
    echo "      - ${DATA_DIR}:${CONTAINER_DATA}"
  } > "$COMPOSE_FILE"
}

compose_up() { dc up -d $([ "$BUILD_FROM_SOURCE" = 1 ] && echo --build); }
pull_image() { dc pull; }

print_summary() {
  local ca="" i cert_file="$DATA_DIR/certs/ssl_cert.pem"
  echo
  echo -e "  ${c_cyn}>${c_off} ${c_bld}Waiting for Server CA${c_off} ${c_dim}(first boot)${c_off}"
  for i in $(seq 1 30); do
    [ -s "$cert_file" ] && { ca="$(cat "$cert_file")"; break; }
    sleep 1
  done
  local ip
  ip="$(curl -fsS4 --max-time 5 https://api.ipify.org 2>/dev/null \
     || curl -fsS4 --max-time 5 https://ifconfig.io 2>/dev/null \
     || echo '<server-ip>')"
  local backends=""
  [ "$XRAY_ON"  -eq 1 ] && backends="${backends} xray"
  [ "$OVPN_ON"  -eq 1 ] && backends="${backends} openvpn"
  [ "$WG_ON"    -eq 1 ] && backends="${backends} wireguard"
  [ "$IKEV2_ON" -eq 1 ] && backends="${backends} ikev2"

  echo
  echo -e "  ${c_amb}${c_bld}+----------------------------------------------------------+${c_off}"
  echo -e "  ${c_amb}${c_bld}|${c_off}  ${c_grn}${c_bld}HPX NODE ONLINE${c_off}  ${c_dim}— register in HPXPANEL -> Nodes${c_off}   ${c_amb}${c_bld}|${c_off}"
  echo -e "  ${c_amb}${c_bld}+----------------------------------------------------------+${c_off}"
  echo
  echo -e "  Container   : ${SERVICE} ($(docker inspect -f '{{.State.Status}}' "$SERVICE" 2>/dev/null))"
  echo -e "  Instance    : ${c_bld}${NODE_NAME:-default}${c_off}"
  echo -e "  Backends    : ${c_bld}${backends# }${c_off}"
  echo -e "  ${c_bld}Address${c_off}     : ${c_cyn}${c_bld}${ip}${c_off}"
  echo -e "  ${c_bld}Node port${c_off}   : ${c_cyn}${c_bld}${SERVICE_PORT}${c_off}   ${c_dim}(panel field: Node Port)${c_off}"
  echo -e "  ${c_yel}${c_bld}API key${c_off}     : ${c_bld}${API_KEY}${c_off}"
  echo -e "  Data        : ${DATA_DIR}"
  echo -e "  Compose     : ${COMPOSE_FILE}"
  echo
  echo -e "  ${c_dim}In HPXPANEL create a node with the same Address / Port / API key.${c_off}"
  echo -e "  ${c_dim}More instances on this host: install -y --name other --service-port <free-port>${c_off}"
  echo -e "  ${c_dim}Docs: ${PANEL_DOCS}${c_off}"
  echo
  if [ -n "$ca" ]; then
    echo -e "  Paste this ${c_yel}${c_bld}Server CA${c_off} into the node's Server CA field:"
    echo
    echo "$ca"
  else
    warn "Server CA not ready yet — run:"
    echo -e "  ${c_dim}cat ${cert_file}${c_off}"
  fi
  echo
  echo -e "  ${c_dim}Logs:${c_off}  sudo ${SERVICE} logs   ${c_dim}or${c_off}  $COMPOSE_CMD -f ${COMPOSE_FILE} logs -f"
  warn "Open SERVICE_PORT (${SERVICE_PORT}) and your VPN ports on any cloud firewall."
  hr
}

install_cli_wrapper() {
  mkdir -p "$INSTALL_DIR"
  if [ -f "$0" ] && [ -r "$0" ] && [[ "$0" != *"bash"* ]]; then
    cp -f "$0" "$INSTALL_DIR/hpx-node.sh" 2>/dev/null || true
  fi
  if [ ! -s "$INSTALL_DIR/hpx-node.sh" ]; then
    curl -fsSL "${REPO}/raw/main/scripts/install.sh" -o "$INSTALL_DIR/hpx-node.sh" 2>/dev/null || true
  fi
  chmod +x "$INSTALL_DIR/hpx-node.sh" 2>/dev/null || true

  # Global dispatcher — always hpx-node (supports --name for multi-instance).
  cat > /usr/local/bin/hpx-node <<EOF
#!/usr/bin/env bash
SCRIPT="${INSTALL_DIR}/hpx-node.sh"
# Prefer newest script from any instance / default path.
for cand in /opt/hpx-node/hpx-node.sh /opt/hpx-node-*/hpx-node.sh; do
  [ -f "\$cand" ] || continue
  SCRIPT="\$cand"
  break
done
if [ -f "\$SCRIPT" ]; then
  exec bash "\$SCRIPT" "\$@"
fi
exec bash -c "\$(curl -fsSL ${REPO}/raw/main/scripts/install.sh)" @ "\$@"
EOF
  chmod +x /usr/local/bin/hpx-node 2>/dev/null || true

  # Per-instance shortcut: hpx-node-shop1 status
  if [ -n "$NODE_NAME" ]; then
    cat > "/usr/local/bin/${SERVICE}" <<EOF
#!/usr/bin/env bash
exec /usr/local/bin/hpx-node --name "${NODE_NAME}" "\$@"
EOF
    chmod +x "/usr/local/bin/${SERVICE}" 2>/dev/null || true
  fi
}

run_install() {
  require_root
  apply_instance
  assert_port_free
  : > "$STEP_LOG"
  [ -z "$API_KEY" ] && API_KEY="$(gen_uuid)"
  local quiet_note=""; [ "${QUIET:-0}" = "1" ] && quiet_note=" — quiet mode"

  banner
  features_panel
  echo -e "${c_bld}Deploying HPX node${c_off} ${c_dim}${SERVICE}${c_off} ${c_dim}(log: ${STEP_LOG}${quiet_note})${c_off}"
  echo

  run_step_live "Installing Docker"          install_docker
  run_step      "Writing docker-compose.yml" write_compose
  if [ "$BUILD_FROM_SOURCE" = 0 ]; then
    if ! run_step_live_soft "Pulling image ${IMAGE}" pull_image; then
      if [ "$IMAGE" != "$FALLBACK_IMAGE" ]; then
        warn "primary image failed — trying fallback ${FALLBACK_IMAGE}"
        IMAGE="$FALLBACK_IMAGE"
        run_step "Rewriting compose for fallback" write_compose
        if ! run_step_live_soft "Pulling fallback ${IMAGE}" pull_image; then
          warn "pull failed — building from source (takes a few minutes)"
          BUILD_FROM_SOURCE=1
          run_step "Rewriting compose for build" write_compose
        fi
      else
        warn "image pull failed — building from source"
        BUILD_FROM_SOURCE=1
        run_step "Rewriting compose for build" write_compose
      fi
    fi
  fi
  run_step_live "Starting HPX node container" compose_up
  run_step      "Installing hpx-node CLI"     install_cli_wrapper
  print_summary
}

install_command() {
  parse_install_args "$@"
  require_root
  run_install
}

list_command() {
  echo -e "  ${c_bld}HPX node instances on this host${c_off}"
  echo
  local dir name port status
  local found=0
  for dir in /opt/hpx-node /opt/hpx-node-*; do
    [ -d "$dir" ] || continue
    [ -f "$dir/docker-compose.yml" ] || continue
    found=1
    name="$(basename "$dir")"
    port="$(grep -E 'SERVICE_PORT:' "$dir/docker-compose.yml" 2>/dev/null | head -1 | awk '{print $2}')"
    status="$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null || echo missing)"
    printf "  %-28s  port %-6s  %s\n" "$name" "${port:--}" "$status"
  done
  if [ "$found" -eq 0 ]; then
    echo -e "  ${c_dim}(none yet)${c_off}"
  fi
  echo
}

update_command() {
  require_root; apply_instance
  detect_compose || install_docker
  [ -f "$COMPOSE_FILE" ] || die "no install found at $COMPOSE_FILE (try --name <id>)"
  : > "$STEP_LOG"
  echo -e "${c_bld}Updating ${SERVICE}${c_off}"
  if grep -q "build:" "$COMPOSE_FILE"; then
    run_step_live "Rebuilding image" bash -c "cd '$INSTALL_DIR' && $COMPOSE_CMD -p '$SERVICE' -f '$COMPOSE_FILE' build --pull"
  else
    run_step_live "Pulling latest image" pull_image
  fi
  run_step_live "Recreating container" bash -c "cd '$INSTALL_DIR' && $COMPOSE_CMD -p '$SERVICE' -f '$COMPOSE_FILE' up -d"
  log "Updated ($(docker inspect -f '{{.State.Status}}' "$SERVICE" 2>/dev/null))"
}

need_compose() {
  apply_instance
  detect_compose || { warn "Docker / compose not found — install first."; return 1; }
  [ -f "$COMPOSE_FILE" ] || { warn "no install at $COMPOSE_FILE (try --name <id>)"; return 1; }
}
restart_command()  { require_root; need_compose || return 0; dc restart; log "restarted $SERVICE"; }
status_command()   { need_compose || return 0; dc ps; }
logs_command()     { need_compose || return 0; dc logs -f; }
uninstall_command() {
  require_root; apply_instance
  detect_compose || true
  warn "Removing HPX node container (${SERVICE})"
  [ -f "$COMPOSE_FILE" ] && dc down 2>/dev/null || docker rm -f "$SERVICE" 2>/dev/null || true
  rm -f "$COMPOSE_FILE"
  if [ "$ASSUME_YES" = 1 ] || ask_yn "Also remove data (certs + generated configs) in $DATA_DIR?"; then rm -rf "$DATA_DIR"; fi
  [ -n "$NODE_NAME" ] && rm -f "/usr/local/bin/${SERVICE}" 2>/dev/null || true
  log "Uninstalled $SERVICE"
}

# Parse leading global --name before the subcommand.
parse_global_name_args() {
  local out=()
  while [ $# -gt 0 ]; do
    case "$1" in
      --name|--instance)
        NODE_NAME="$2"; shift 2 ;;
      *)
        out+=("$1"); shift ;;
    esac
  done
  # shellcheck disable=SC2068
  set -- ${out[@]+"${out[@]}"}
  GLOBAL_ARGS=("${out[@]}")
}

main() {
  GLOBAL_ARGS=()
  parse_global_name_args "$@"
  if [ ${#GLOBAL_ARGS[@]} -gt 0 ]; then
    set -- "${GLOBAL_ARGS[@]}"
  else
    set --
  fi

  local cmd="menu"
  case "${1:-}" in
    menu) cmd="menu"; shift ;;
    install|update|uninstall|restart|status|logs|list) cmd="$1"; shift ;;
    -h|--help) usage; exit 0 ;;
    "") cmd="menu" ;;
    -*) cmd="install" ;;
    *) die "unknown command: $1 (see --help)" ;;
  esac

  case "$cmd" in
    menu)      menu_command ;;
    install)   install_command "$@" ;;
    list)      list_command ;;
    update)    parse_install_args "$@"; update_command ;;
    uninstall) parse_install_args "$@"; uninstall_command ;;
    restart)   parse_install_args "$@"; restart_command ;;
    status)    parse_install_args "$@"; status_command ;;
    logs)      parse_install_args "$@"; logs_command ;;
  esac
}

main "$@"

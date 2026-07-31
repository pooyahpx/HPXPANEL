#!/usr/bin/env bash
#
# HPXPANEL Node â€” command-deck edge installer
# ------------------------------------------
# Installs an HPX-compatible multi-backend node (Xray / WireGuard / OpenVPN / IKEv2)
# as a Docker container, then prints the Address + Port + API key + Server CA that
# you paste into HPXPANEL â†’ Nodes.
#
# One-liner (Linux):
#   sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXNODE/raw/main/scripts/install.sh)" @ install
#
# Interactive menu:
#   sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXNODE/raw/main/scripts/install.sh)"
#
# Local:
#   sudo bash scripts/hpx-node.sh install -y
#   sudo bash scripts/hpx-node.sh menu
#
set -euo pipefail

# When invoked as: bash -c "$(curl â€¦)" @ install â€¦
# the "@" is $0-style arg noise from one-liners â€” strip it.
if [ "${1:-}" = "@" ]; then shift; fi

# ---- defaults (override via flags / env) -----------------------------------
PANEL_DOCS="${PANEL_DOCS:-https://pooyahpx.github.io/HPXPANEL/}"
PANEL_REPO="${PANEL_REPO:-https://github.com/pooyahpx/HPXPANEL}"
# Multi-backend image (Xray + WG + OpenVPN + IKEv2). Override with --image / IMAGE=.
REPO="${REPO:-https://github.com/pooyahpx/HPXNODE}"
IMAGE="${IMAGE:-ghcr.io/pooyahpx/hpx-node:latest}"
FALLBACK_IMAGE="${FALLBACK_IMAGE:-ghcr.io/pooyahpx/hpx-node:latest}"
BRANCH="${BRANCH:-main}"

SERVICE="${SERVICE:-hpx-node}"
INSTALL_DIR="${INSTALL_DIR:-/opt/hpx-node}"
COMPOSE_FILE="$INSTALL_DIR/docker-compose.yml"
DATA_DIR="${DATA_DIR:-/var/lib/hpx-node}"
# Container still expects the classic data path internally.
CONTAINER_DATA="/var/lib/hpx-node"

SERVICE_PORT="${SERVICE_PORT:-62050}"
API_KEY=""
BUILD_FROM_SOURCE=0
ASSUME_YES=0
QUIET="${QUIET:-0}"

XRAY_ON=1; OVPN_ON=1; WG_ON=1; IKEV2_ON=1

# ---- colors ----------------------------------------------------------------
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
hr()   { echo -e "${c_cyn}â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€${c_off}"; }
has()  { command -v "$1" >/dev/null 2>&1; }

_read() { if [ -e /dev/tty ]; then read "$@" </dev/tty || true; else read "$@" || true; fi; }

STEP_LOG="/tmp/hpx-node-install.log"

run_step() {
  local msg="$1"; shift
  echo -ne "  ${c_cyn}â–¶${c_off} ${msg} ${c_dim}...${c_off} "
  if "$@" >>"$STEP_LOG" 2>&1; then
    echo -e "${c_grn}done${c_off}"
  else
    echo -e "${c_red}failed${c_off}"
    err "step failed: ${msg}"; err "last lines of ${STEP_LOG}:"; tail -n 12 "$STEP_LOG" >&2 || true
    exit 1
  fi
}

_rule() { echo -e "${c_dim}    â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„â”„${c_off}"; }

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
  echo -e "  ${c_cyn}â–¶${c_off} ${c_bld}${msg}${c_off}"
  _rule
  if _stream "$@"; then
    _rule; echo -e "  ${c_grn}âœ”${c_off} ${msg}"
  else
    _rule; echo -e "  ${c_red}âœ˜${c_off} ${msg}"
    err "step failed: ${msg} (full log: ${STEP_LOG})"
    exit 1
  fi
}

run_step_live_soft() {
  local msg="$1"; shift
  if [ "${QUIET:-0}" = "1" ]; then run_step_soft "$msg" "$@"; return; fi
  echo -e "  ${c_cyn}â–¶${c_off} ${c_bld}${msg}${c_off}"
  _rule
  if _stream "$@"; then
    echo -e "  ${c_grn}âœ”${c_off} ${msg}"; return 0
  else
    echo -e "  ${c_yel}â–·${c_off} ${msg} â€” ${c_yel}skipped${c_off}"; return 1
  fi
}

run_step_soft() {
  local msg="$1"; shift
  echo -ne "  ${c_cyn}â–¶${c_off} ${msg} ${c_dim}...${c_off} "
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
dc() { ( cd "$INSTALL_DIR" && $COMPOSE_CMD "$@" ); }

apt_busy() {
  local f
  for f in /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock \
           /var/lib/apt/lists/lock /var/cache/apt/archives/lock; do
    [ -e "$f" ] || continue
    if has fuser && fuser "$f" >/dev/null 2>&1; then return 0; fi
  done
  if has pgrep; then
    local p
    for p in apt apt-get dpkg; do
      pgrep -x "$p" >/dev/null 2>&1 && return 0
    done
    pgrep -f unattended-upgr >/dev/null 2>&1 && return 0
  fi
  return 1
}

apt_holder() {
  local f p
  for f in /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock \
           /var/lib/apt/lists/lock /var/cache/apt/archives/lock; do
    [ -e "$f" ] || continue
    has fuser || break
    p=$(fuser "$f" 2>/dev/null | tr -s ' ' '\n' | grep -E '^[0-9]+$' | head -1)
    [ -n "$p" ] && { ps -o comm= -p "$p" 2>/dev/null | tail -1; return; }
  done
  if has pgrep; then
    for p in unattended-upgr apt apt-get dpkg; do
      pgrep -x "$p" >/dev/null 2>&1 && { echo "$p"; return; }
    done
  fi
  echo "another apt/dpkg process"
}

wait_for_apt() {
  has apt-get || return 0
  apt_busy || return 0
  local waited=0 max="${APT_LOCK_TIMEOUT:-900}"
  log "apt/dpkg is busy ($(apt_holder)) â€” waiting up to $((max / 60))m..."
  while apt_busy; do
    if [ "$waited" -ge "$max" ]; then
      warn "apt still locked after $((max / 60))m (holder: $(apt_holder))."
      return 1
    fi
    sleep 3; waited=$((waited + 3))
    [ $((waited % 30)) -eq 0 ] && log "  still waiting... ${waited}s (holder: $(apt_holder))"
  done
  log "apt is free (waited ${waited}s)"
}

install_docker() {
  if ! has docker; then
    wait_for_apt || die "apt is locked â€” retry later"
    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker 2>/dev/null || true
  fi
  detect_compose || die "docker compose plugin not available after install"
}

# ---- banner / features ------------------------------------------------------
banner() {
  clear 2>/dev/null || true
  echo
  echo -e "  ${c_cyn}${c_bld}â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”“${c_off}"
  echo -e "  ${c_cyn}${c_bld}â”ƒ${c_off}  ${c_amb}${c_bld}HPX${c_off}${c_bld}PANEL${c_off}  ${c_dim}//${c_off}  ${c_cyn}NODE DEPLOY${c_off}  ${c_dim}Â· COMMAND DECK${c_off}     ${c_cyn}${c_bld}â”ƒ${c_off}"
  echo -e "  ${c_cyn}${c_bld}â”—â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”›${c_off}"
  echo
  echo -e "  ${c_dim}Edge node for${c_off} ${c_bld}HPXPANEL${c_off} ${c_dim}â€” paste Address / Port / API key / CA into the panel.${c_off}"
  echo
}

features_panel() {
  echo -e "  ${c_bld}HPX NODE CAPABILITIES${c_off}"
  echo -e "  ${c_dim}â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”${c_off}"
  echo -e "  ${c_dim}â”‚${c_off}  ${c_cyn}â—†${c_off} Xray stack     ${c_dim}VLESS / VMess / Trojan / SS / REALITY${c_off}"
  echo -e "  ${c_dim}â”‚${c_off}  ${c_cyn}â—†${c_off} WireGuard      ${c_dim}kernel WG + host NAT routing${c_off}"
  echo -e "  ${c_dim}â”‚${c_off}  ${c_cyn}â—†${c_off} OpenVPN        ${c_dim}optional tunnel backend${c_off}"
  echo -e "  ${c_dim}â”‚${c_off}  ${c_amb}â—†${c_off} IKEv2 / IPsec  ${c_dim}native strongSwan (HPX special)${c_off}"
  echo -e "  ${c_dim}â”‚${c_off}  ${c_grn}â—†${c_off} Panel sync     ${c_dim}gRPC â†’ HPXPANEL Nodes UI${c_off}"
  echo -e "  ${c_dim}â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜${c_off}"
  echo
}

usage() {
  cat <<EOF
HPXPANEL Node â€” Docker installer (hpx-node)

Usage:
  sudo bash hpx-node.sh [command] [options]
  sudo bash -c "\$(curl -fsSL ${PANEL_REPO}/raw/main/scripts/hpx-node.sh)" @ install -y

Commands:
  (none) / menu     Interactive HUD menu
  install           Install / reinstall
  update | restart | status | logs
  uninstall

Install options:
  --disable <list>   xray,openvpn,wireguard,ikev2 (comma)
  --api-key <uuid>   (default: auto-generate)
  --service-port <n> panel "Node Port" (default: ${SERVICE_PORT})
  --image <ref>      pull image (default: ${IMAGE})
  --build            build from source instead of pull
  --branch <name> | --repo <url>
  -y, --yes          non-interactive
  -q, --quiet
  -h, --help

Docs: ${PANEL_DOCS}
Log : ${STEP_LOG}
EOF
}

parse_install_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
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
}

onoff() { if [ "${1:-0}" -eq 1 ]; then echo -e "${c_grn}${c_bld}â— ON${c_off}"; else echo -e "${c_dim}â—‹ off${c_off}"; fi; }
press_enter() { echo; _read -r -p "$(echo -e "  ${c_dim}Press Enter to return to the deckâ€¦${c_off}")" _; }

menu_command() {
  require_root
  if [ ! -e /dev/tty ] && [ ! -t 0 ]; then
    die "no terminal for the menu â€” use:
  sudo bash hpx-node.sh install --disable openvpn -y"
  fi
  local status="not installed"
  has docker && docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$SERVICE" && \
    status="installed ($(docker inspect -f '{{.State.Status}}' "$SERVICE" 2>/dev/null))"

  while true; do
    banner
    features_panel
    echo -e "  ${c_dim}State:${c_off} ${c_bld}${status}${c_off}"
    echo -e "  ${c_dim}Image:${c_off} $([ "$BUILD_FROM_SOURCE" = 1 ] && echo 'build from source' || echo "$IMAGE")"
    echo
    echo -e "  ${c_bld}BACKENDS${c_off} ${c_dim}(toggle what this edge runs)${c_off}"
    printf "    ${c_bld}1${c_off}  %-24s %b\n" "Xray"               "$(onoff "$XRAY_ON")"
    printf "    ${c_bld}2${c_off}  %-24s %b\n" "OpenVPN"            "$(onoff "$OVPN_ON")"
    printf "    ${c_bld}3${c_off}  %-24s %b\n" "WireGuard"          "$(onoff "$WG_ON")"
    printf "    ${c_bld}4${c_off}  %-24s %b\n" "IKEv2 / IPsec"      "$(onoff "$IKEV2_ON")"
    echo
    echo -e "  ${c_bld}LINK TO PANEL${c_off}"
    printf "    ${c_bld}5${c_off}  %-24s ${c_cyn}%s${c_off}\n" "Node port (gRPC)" "$SERVICE_PORT"
    printf "    ${c_bld}6${c_off}  %-24s ${c_cyn}%s${c_off}\n" "API key"          "${API_KEY:-auto-generate}"
    printf "    ${c_bld}7${c_off}  %-24s ${c_cyn}%s${c_off}\n" "Image source"     "$([ "$BUILD_FROM_SOURCE" = 1 ] && echo 'build from source' || echo 'pull')"
    echo -e "    ${c_dim}VPN listener ports come from HPXPANEL core config. IKEv2 uses 500/4500.${c_off}"
    echo
    echo -e "  ${c_bld}ACTIONS${c_off}"
    echo -e "    ${c_grn}${c_bld}i${c_off}  Install / reinstall"
    echo -e "    ${c_bld}u${c_off} Update   ${c_bld}s${c_off} Status   ${c_bld}l${c_off} Logs   ${c_bld}r${c_off} Restart"
    echo -e "    ${c_red}x${c_off} Uninstall   ${c_bld}q${c_off} Quit"
    echo
    local choice
    _read -r -p "$(echo -e "  ${c_bld}Select${c_off} ${c_dim}(number / letter)${c_off} ${c_amb}â¯${c_off} ")" choice
    case "$choice" in
      1) XRAY_ON=$((1 - XRAY_ON)) ;;
      2) OVPN_ON=$((1 - OVPN_ON)) ;;
      3) WG_ON=$((1 - WG_ON)) ;;
      4) IKEV2_ON=$((1 - IKEV2_ON)) ;;
      5) SERVICE_PORT="$(ask_num "Node port (gRPC â€” panel Node Port)" "$SERVICE_PORT")" ;;
      6) API_KEY="$(ask_val "API key (blank = auto-generate)" "$API_KEY")" ;;
      7) BUILD_FROM_SOURCE=$((1 - BUILD_FROM_SOURCE)) ;;
      i|I) echo; run_install; break ;;
      u|U) echo; update_command; press_enter ;;
      s|S) echo; status_command; press_enter ;;
      l|L) echo; logs_command ;;
      r|R) echo; restart_command; press_enter ;;
      x|X) echo; uninstall_command; press_enter; status="not installed" ;;
      q|Q) echo; exit 0 ;;
      "") : ;;
      *) warn "Unknown: '${choice}'"; sleep 1 ;;
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
  echo -e "  ${c_cyn}â–¶${c_off} ${c_bld}Waiting for Server CA${c_off} ${c_dim}(first boot)${c_off}"
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
  echo -e "  ${c_amb}${c_bld}â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”“${c_off}"
  echo -e "  ${c_amb}${c_bld}â”ƒ${c_off}  ${c_grn}${c_bld}HPX NODE ONLINE${c_off}  ${c_dim}â€” register in HPXPANEL â†’ Nodes${c_off}   ${c_amb}${c_bld}â”ƒ${c_off}"
  echo -e "  ${c_amb}${c_bld}â”—â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”›${c_off}"
  echo
  echo -e "  Container   : ${SERVICE} ($(docker inspect -f '{{.State.Status}}' "$SERVICE" 2>/dev/null))"
  echo -e "  Backends    : ${c_bld}${backends# }${c_off}"
  echo -e "  ${c_bld}Address${c_off}     : ${c_cyn}${c_bld}${ip}${c_off}"
  echo -e "  ${c_bld}Node port${c_off}   : ${c_cyn}${c_bld}${SERVICE_PORT}${c_off}   ${c_dim}(panel field: Node Port)${c_off}"
  echo -e "  ${c_yel}${c_bld}API key${c_off}     : ${c_bld}${API_KEY}${c_off}"
  echo -e "  Data        : ${DATA_DIR}"
  echo -e "  Compose     : ${COMPOSE_FILE}"
  echo
  echo -e "  ${c_dim}In HPXPANEL create a node with the same Address / Port / API key.${c_off}"
  echo -e "  ${c_dim}Docs: ${PANEL_DOCS}${c_off}"
  echo
  if [ -n "$ca" ]; then
    echo -e "  Paste this ${c_yel}${c_bld}Server CA${c_off} into the node's Server CA field:"
    echo
    echo "$ca"
  else
    warn "Server CA not ready yet â€” run:"
    echo -e "  ${c_dim}cat ${cert_file}${c_off}"
  fi
  echo
  echo -e "  ${c_dim}Logs:${c_off}  sudo ${SERVICE} logs   ${c_dim}or${c_off}  $COMPOSE_CMD -f ${COMPOSE_FILE} logs -f"
  warn "Open SERVICE_PORT (${SERVICE_PORT}) and your VPN ports on any cloud firewall."
  hr
}

install_cli_wrapper() {
  # Convenience: `hpx-node status` after install
  cat > "/usr/local/bin/${SERVICE}" <<EOF
#!/usr/bin/env bash
exec bash -c "\$(curl -fsSL ${PANEL_REPO}/raw/main/scripts/hpx-node.sh 2>/dev/null || cat ${INSTALL_DIR}/hpx-node.sh 2>/dev/null)" @ "\$@"
EOF
  # Prefer local copy when present (offline-safe)
  if [ -f "$0" ] && [ -r "$0" ]; then
    cp -f "$0" "$INSTALL_DIR/hpx-node.sh" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/hpx-node.sh" 2>/dev/null || true
    cat > "/usr/local/bin/${SERVICE}" <<EOF
#!/usr/bin/env bash
exec bash "${INSTALL_DIR}/hpx-node.sh" "\$@"
EOF
  fi
  chmod +x "/usr/local/bin/${SERVICE}" 2>/dev/null || true
}

run_install() {
  require_root
  : > "$STEP_LOG"
  [ -z "$API_KEY" ] && API_KEY="$(gen_uuid)"
  local quiet_note=""; [ "${QUIET:-0}" = "1" ] && quiet_note=" â€” quiet mode"

  banner
  features_panel
  echo -e "${c_bld}Deploying HPX node${c_off} ${c_dim}(log: ${STEP_LOG}${quiet_note})${c_off}"
  echo

  run_step_live "Installing Docker"          install_docker
  run_step      "Writing docker-compose.yml" write_compose
  if [ "$BUILD_FROM_SOURCE" = 0 ]; then
    if ! run_step_live_soft "Pulling image ${IMAGE}" pull_image; then
      if [ "$IMAGE" != "$FALLBACK_IMAGE" ]; then
        warn "primary image failed â€” trying fallback ${FALLBACK_IMAGE}"
        IMAGE="$FALLBACK_IMAGE"
        run_step "Rewriting compose for fallback" write_compose
        if ! run_step_live_soft "Pulling fallback ${IMAGE}" pull_image; then
          warn "pull failed â€” building from source (takes a few minutes)"
          BUILD_FROM_SOURCE=1
          run_step "Rewriting compose for build" write_compose
        fi
      else
        warn "image pull failed â€” building from source"
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
  if [ "$ASSUME_YES" -eq 1 ]; then run_install; else menu_command; fi
}

update_command() {
  require_root; detect_compose || install_docker
  [ -f "$COMPOSE_FILE" ] || die "no install found at $COMPOSE_FILE"
  : > "$STEP_LOG"
  echo -e "${c_bld}Updating HPX node${c_off}"
  if grep -q "build:" "$COMPOSE_FILE"; then
    run_step_live "Rebuilding image" bash -c "cd '$INSTALL_DIR' && $COMPOSE_CMD build --pull"
  else
    run_step_live "Pulling latest image" pull_image
  fi
  run_step_live "Recreating container" bash -c "cd '$INSTALL_DIR' && $COMPOSE_CMD up -d"
  log "Updated ($(docker inspect -f '{{.State.Status}}' "$SERVICE" 2>/dev/null))"
}

need_compose() {
  detect_compose || { warn "Docker / compose not found â€” install first."; return 1; }
  [ -f "$COMPOSE_FILE" ] || { warn "no install at $COMPOSE_FILE"; return 1; }
}
restart_command()  { require_root; need_compose || return 0; dc restart; log "restarted"; }
status_command()   { need_compose || return 0; dc ps; }
logs_command()     { need_compose || return 0; dc logs -f; }
uninstall_command() {
  require_root; detect_compose || true
  warn "Removing HPX node container (${SERVICE})"
  [ -f "$COMPOSE_FILE" ] && dc down 2>/dev/null || docker rm -f "$SERVICE" 2>/dev/null || true
  rm -f "$COMPOSE_FILE"
  if ask_yn "Also remove data (certs + generated configs) in $DATA_DIR?"; then rm -rf "$DATA_DIR"; fi
  log "Uninstalled"
}

main() {
  local cmd="menu"
  case "${1:-}" in
    menu) cmd="menu"; shift ;;
    install|update|uninstall|restart|status|logs) cmd="$1"; shift ;;
    -h|--help) usage; exit 0 ;;
    "") cmd="menu" ;;
    -*) cmd="install" ;;
    *) die "unknown command: $1 (see --help)" ;;
  esac
  case "$cmd" in
    menu)      menu_command ;;
    install)   install_command "$@" ;;
    update)    update_command ;;
    uninstall) uninstall_command ;;
    restart)   restart_command ;;
    status)    status_command ;;
    logs)      logs_command ;;
  esac
}

main "$@"

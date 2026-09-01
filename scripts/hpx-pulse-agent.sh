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
AGENTS_DIR="${ETC_DIR}/agents"
ENV_FILE="$ETC_DIR/agent.env"
BIN_LINK="${BIN_LINK:-/usr/local/bin/hpx-pulse-agent}"
SERVICE_NAME="${SERVICE_NAME:-hpx-pulse-agent}"
TIMER_NAME="${TIMER_NAME:-hpx-pulse-agent.timer}"
LEGACY_TUNNEL_SERVICE="hpx-pulse-tunnel"
TUNNEL_SERVICE="${TUNNEL_SERVICE:-$LEGACY_TUNNEL_SERVICE}"
ENGINE_INSTALL_URL="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-tunnel-engine-install.sh"
ENGINE_BIN="${ENGINE_BIN:-/usr/local/bin/hpx-tunnel-engine}"

log()  { echo "[HPX Pulse] $*" >&2; }
warn() { echo "[HPX Pulse !] $*" >&2; }
die()  { echo "[HPX Pulse x] $*" >&2; exit 1; }
has()  { command -v "$1" >/dev/null 2>&1; }

# HTTP/1.1 avoids curl error 92 (PROTOCOL_ERROR) on some filtered routes (e.g. Iran).
hp_curl() {
  curl --http1.1 --connect-timeout 30 --max-time 120 --retry 3 --retry-delay 2 -fsSL "$@"
}

# Shorter timeout for panel mirror — fall back to GitHub quickly when panel port is blocked.
hp_panel_curl() {
  curl --http1.1 --connect-timeout 15 --max-time 120 --retry 1 --retry-delay 2 -fsSL "$@"
}

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
  if ! has jq; then
    if has timeout; then
      timeout 90 apt-get update -qq \
        && DEBIAN_FRONTEND=noninteractive timeout 120 apt-get install -y -qq jq >/dev/null 2>&1 \
        || dnf install -y -q jq >/dev/null 2>&1 \
        || die "install jq (apt/dnf timed out or unavailable)"
    else
      apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq jq >/dev/null 2>&1 || \
        dnf install -y -q jq >/dev/null 2>&1 || die "install jq"
    fi
  fi
}

install_self() {
  mkdir -p "$INSTALL_DIR" "$ETC_DIR"
  if [ -f "${BASH_SOURCE[0]:-}" ] && [ -r "${BASH_SOURCE[0]:-}" ] && [ "${BASH_SOURCE[0]:-}" != "bash" ]; then
    cp "${BASH_SOURCE[0]}" "$INSTALL_DIR/hpx-pulse-agent.sh" 2>/dev/null || true
  fi
  if [ ! -s "$INSTALL_DIR/hpx-pulse-agent.sh" ]; then
    if hp_curl "https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-pulse-agent.sh" \
        -o "$INSTALL_DIR/hpx-pulse-agent.sh"; then
      :
    elif [ -n "${PANEL_URL:-}" ] \
      && hp_curl "${PANEL_URL%/}/api/hpx_pulse/agent/hpx-pulse-agent.sh" \
        -o "$INSTALL_DIR/hpx-pulse-agent.sh"; then
      :
    else
      die "HPX Pulse agent script download failed"
    fi
  fi
  chmod 755 "$INSTALL_DIR/hpx-pulse-agent.sh"
  ln -sfn "$INSTALL_DIR/hpx-pulse-agent.sh" "$BIN_LINK"
}

write_env_file() {
  local dest="$1"
  cat >"$dest" <<EOF
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
PORT_FORWARDS=${PORT_FORWARDS:-}
HPX_AGENT_ASSETS_BASE=${HPX_AGENT_ASSETS_BASE:-}
EOF
  chmod 600 "$dest"
}

write_env() {
  write_env_file "$ENV_FILE"
  if [ -n "${PULSE_ID:-}" ] && [ "${PULSE_ID}" != "0" ]; then
    mkdir -p "$AGENTS_DIR"
    write_env_file "${AGENTS_DIR}/${PULSE_ID}.env"
  fi
}

load_env_file() {
  local file="$1"
  [ -f "$file" ] || return 1
  # shellcheck disable=SC1090
  set -a; source "$file"; set +a
  return 0
}

load_env() {
  load_env_file "$ENV_FILE" || die "agent not configured — run join first"
}

for_each_pulse_env() {
  local fn="$1" ran=0 env_file
  if [ -d "$AGENTS_DIR" ]; then
    for env_file in "$AGENTS_DIR"/*.env; do
      [ -f "$env_file" ] || continue
      load_env_file "$env_file" || continue
      "$fn"
      ran=1
    done
  fi
  if [ "$ran" = 0 ]; then
    load_env
    "$fn"
  fi
}

tunnel_service_name() {
  if [ -n "${PULSE_ID:-}" ] && [ "${PULSE_ID}" != "0" ]; then
    echo "hpx-pulse-tunnel-${PULSE_ID}"
  else
    echo "${TUNNEL_SERVICE}"
  fi
}

collect_forward_listen_ports() {
  local raw="$1" pf left ports=()
  raw="${raw//[\[\]\"]/}"
  IFS=',' read -ra pf <<< "$raw"
  for left in "${pf[@]}"; do
    left="${left%%=*}"
    left="${left// /}"
    [[ "$left" =~ ^[0-9]+$ ]] && ports+=("$left")
  done
  printf '%s\n' "${ports[@]}"
}

check_local_forward_conflicts() {
  [ "${PULSE_SIDE:-}" = "iran" ] || return 0
  [ -d "$AGENTS_DIR" ] || return 0
  local env_file existing_id port new_port
  while IFS= read -r new_port; do
    [ -n "$new_port" ] || continue
    for env_file in "$AGENTS_DIR"/*.env; do
      [ -f "$env_file" ] || continue
      existing_id="$(basename "$env_file" .env)"
      [ "$existing_id" = "${PULSE_ID:-}" ] && continue
      while IFS= read -r port; do
        [ -n "$port" ] || continue
        if [ "$port" = "$new_port" ]; then
          die "Iran listen port ${port} already used by pulse ${existing_id} on this server — use one pulse with multiple forwards, or different external ports"
        fi
      done < <(collect_forward_listen_ports "$(grep '^PORT_FORWARDS=' "$env_file" | cut -d= -f2-)")
    done
  done < <(collect_forward_listen_ports "${PORT_FORWARDS:-}")
}

migrate_legacy_agent_registration() {
  [ -n "${PULSE_ID:-}" ] && [ "${PULSE_ID}" != "0" ] || return 0
  mkdir -p "$AGENTS_DIR"
  if [ ! -f "${AGENTS_DIR}/${PULSE_ID}.env" ]; then
    write_env_file "${AGENTS_DIR}/${PULSE_ID}.env"
    log "registered pulse ${PULSE_ID} for multi-tunnel sync"
  fi
  local cfg id
  for cfg in "$ETC_DIR"/l3-pulse-*.toml; do
    [ -f "$cfg" ] || continue
    id="${cfg##*/l3-pulse-}"
    id="${id%.toml}"
    [ -f "${AGENTS_DIR}/${id}.env" ] && continue
    warn "tunnel config pulse ${id} exists but no agent registration — re-join Iran token for pulse ${id}"
  done
}

panel_api_bases() {
  local u="${PANEL_URL%/}" seen="|"
  _emit_base() {
    local b="${1%/}"
    [ -n "$b" ] || return 0
    case "$seen" in *"|${b}|"*) return 0 ;; esac
    seen="${seen}${b}|"
    printf '%s\n' "$b"
  }
  _emit_base "$u"
  [ -n "${PANEL_URL_FALLBACK:-}" ] && _emit_base "${PANEL_URL_FALLBACK}"
  # Iran VPS often cannot reach panel :8000 — try same host on 443 (nginx → panel).
  if [[ "$u" =~ ^(https?://[^:/]+):8000$ ]]; then
    _emit_base "${BASH_REMATCH[1]}"
  fi
}

api() {
  local method="$1" path="$2" body="${3:-}"
  local base url attempt resp
  while IFS= read -r base; do
    [ -n "$base" ] || continue
    url="${base%/}${path}"
    for attempt in 1 2 3; do
      local args=(--http1.1 --connect-timeout 15 --max-time 90 -fsSL -X "$method"
        -H "X-HPX-Pulse-Agent-Key: ${AGENT_KEY}" -H "X-HPX-Pulse-Side: ${PULSE_SIDE}" -H "Accept: application/json")
      [ -n "$body" ] && args+=(-H "Content-Type: application/json" -d "$body")
      if resp=$(curl "${args[@]}" "$url" 2>/dev/null); then
        if [ "$base" != "${PANEL_URL%/}" ]; then
          log "panel API reachable at ${base} (was ${PANEL_URL}) — updating PANEL_URL"
          PANEL_URL="$base"
        fi
        printf '%s' "$resp"
        return 0
      fi
      [ "$attempt" -lt 3 ] && sleep 2
    done
  done < <(panel_api_bases)
  return 1
}

ensure_engine() {
  if [ -x "$ENGINE_BIN" ] && [ "${HPX_ENGINE_FORCE:-0}" != "1" ]; then
    return 0
  fi
  if [ "${HPX_ENGINE_FORCE:-0}" = "1" ]; then
    rm -f "$ENGINE_BIN"
  fi
  if [ -x /usr/local/bin/backpack ] && [ ! -x "$ENGINE_BIN" ] && [ "${HPX_ENGINE_FORCE:-0}" != "1" ]; then
    ln -sf /usr/local/bin/backpack "$ENGINE_BIN"
    return 0
  fi
  log "Installing HPX tunnel engine..."
  local installer panel_install_url prefer_github
  installer="$(mktemp)"
  panel_install_url=""
  prefer_github="${HPX_PREFER_GITHUB:-}"
  if [ -z "$prefer_github" ] && [ "${PULSE_SIDE:-}" = "iran" ]; then
    prefer_github=1
    log "Iran side — downloading engine from GitHub first (panel mirror often blocked)"
  fi
  if [ -n "${PANEL_URL:-}" ]; then
    panel_install_url="${PANEL_URL%/}/api/hpx_pulse/agent/engine-install.sh"
  elif [ -n "${HPX_AGENT_ASSETS_BASE:-}" ]; then
    panel_install_url="${HPX_AGENT_ASSETS_BASE%/}/engine-install.sh"
  fi
  if hp_curl "$ENGINE_INSTALL_URL" -o "$installer"; then
    log "Using GitHub-hosted engine installer"
  elif [ -n "$panel_install_url" ] && hp_panel_curl "$panel_install_url" -o "$installer"; then
    log "Using panel-hosted engine installer"
  else
    rm -f "$installer"
    die "HPX tunnel engine install script download failed"
  fi
  chmod 755 "$installer"
  local install_ok=0
  run_engine_install() {
    HPX_PANEL_URL="${PANEL_URL:-}" HPX_AGENT_ASSETS_BASE="${HPX_AGENT_ASSETS_BASE:-}" \
      HPX_PREFER_GITHUB="${1:-0}" \
      HPX_ENGINE_FORCE="${HPX_ENGINE_FORCE:-0}" \
      HPX_NO_GITHUB_FALLBACK="${HPX_NO_GITHUB_FALLBACK:-0}" bash "$installer"
  }
  if run_engine_install "${prefer_github:-0}"; then
    install_ok=1
  elif [ "${prefer_github:-0}" != "1" ]; then
    log "panel engine mirror failed — retrying from GitHub..."
    if run_engine_install 1; then
      install_ok=1
    fi
  fi
  rm -f "$installer"
  [ "$install_ok" = 1 ] || die "HPX tunnel engine install failed — see README: HPX Pulse engine manual install"
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
  systemctl is-active --quiet "$(tunnel_service_name).service" 2>/dev/null
}

retire_legacy_tunnel_service() {
  local svc="$1"
  [ "$svc" = "$LEGACY_TUNNEL_SERVICE" ] && return 0
  if [ -f "/etc/systemd/system/${LEGACY_TUNNEL_SERVICE}.service" ]; then
    systemctl stop "${LEGACY_TUNNEL_SERVICE}.service" 2>/dev/null || true
    systemctl disable "${LEGACY_TUNNEL_SERVICE}.service" 2>/dev/null || true
  fi
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
  local cfg="$1" engine_bin svc
  engine_bin="$(engine_bin)"
  svc="$(tunnel_service_name)"
  retire_legacy_tunnel_service "$svc"
  cat >"/etc/systemd/system/${svc}.service" <<EOF
[Unit]
Description=HPX Pulse tunnel (pulse ${PULSE_ID:-?})
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
  systemctl enable "${svc}.service" >/dev/null
  systemctl restart "${svc}.service"
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
  open_iran_firewall
  install_tunnel_systemd "$cfg"
  sleep 2
  if tunnel_service_active; then
    log "HPX tunnel service started ($(tunnel_service_name))"
  else
    warn "HPX tunnel service not active yet — check: systemctl status $(tunnel_service_name)"
  fi
  check_abroad_backends
}

# Open tunnel + forwarded ports on Iran (required for Reverse).
open_iran_firewall() {
  [ "${PULSE_SIDE:-}" = "iran" ] || return 0
  case "${TUNNEL_MODE:-}" in reverse_*) ;; *) return 0 ;; esac

  local ports=()
  [ -n "${CONTROL_PORT:-}" ] && ports+=("$CONTROL_PORT")
  local raw pf left
  raw="${PORT_FORWARDS:-}"
  raw="${raw//[\[\]\"]/}"
  IFS=',' read -ra pf <<< "$raw"
  for left in "${pf[@]}"; do
    left="${left%%=*}"
    left="${left// /}"
    [[ "$left" =~ ^[0-9]+$ ]] && ports+=("$left")
  done
  for p in "${ports[@]}"; do
    if has ufw && ufw status 2>/dev/null | grep -qi "Status: active"; then
      ufw allow "${p}/tcp" >/dev/null 2>&1 || true
      log "ufw allow ${p}/tcp"
    elif has firewall-cmd; then
      firewall-cmd --permanent --add-port="${p}/tcp" >/dev/null 2>&1 || true
      firewall-cmd --reload >/dev/null 2>&1 || true
      log "firewalld allow ${p}/tcp"
    elif has iptables; then
      iptables -C INPUT -p tcp --dport "$p" -j ACCEPT 2>/dev/null \
        || iptables -I INPUT -p tcp --dport "$p" -j ACCEPT
      log "iptables allow ${p}/tcp"
    else
      warn "open firewall manually: allow TCP ${p}"
    fi
  done
}

# Abroad must have the target service listening (e.g. Xray on 127.0.0.1:443).
check_abroad_backends() {
  [ "${PULSE_SIDE:-}" = "abroad" ] || return 0
  case "${TUNNEL_MODE:-}" in reverse_*) ;; *) return 0 ;; esac

  local raw pf entry target host port
  raw="${PORT_FORWARDS:-}"
  raw="${raw//[\[\]\"]/}"
  [ -n "$raw" ] || return 0
  IFS=',' read -ra pf <<< "$raw"
  for entry in "${pf[@]}"; do
    entry="${entry// /}"
    [ -n "$entry" ] || continue
    if [[ "$entry" == *"="* ]]; then
      target="${entry#*=}"
    else
      target="127.0.0.1:${entry}"
    fi
    if [[ "$target" != *:* ]]; then
      target="127.0.0.1:${target}"
    fi
    host="${target%:*}"
    port="${target##*:}"
    if has ss; then
      if ! ss -tlnH "sport = :${port}" 2>/dev/null | grep -q .; then
        warn "nothing listening on ${host}:${port} — start Xray/panel inbound there or host ping will be -1"
      else
        log "backend OK: ${host}:${port} listening"
      fi
    fi
  done
}

install_agent_systemd() {
  cat >"/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=HPX Pulse Agent sync
After=network-online.target
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

  # Live ping every 5s (heartbeat only — no full sync).
  cat >"/etc/systemd/system/${SERVICE_NAME}-ping.service" <<EOF
[Unit]
Description=HPX Pulse live ping
After=network-online.target

[Service]
Type=oneshot
ExecStart=$BIN_LINK ping
Nice=10
EOF
  cat >"/etc/systemd/system/${SERVICE_NAME}-ping.timer" <<EOF
[Unit]
Description=HPX Pulse live ping timer

[Timer]
OnBootSec=5s
OnUnitActiveSec=5s
AccuracySec=1s
Unit=${SERVICE_NAME}-ping.service

[Install]
WantedBy=timers.target
EOF

  systemctl daemon-reload
  systemctl enable --now "$TIMER_NAME" >/dev/null
  systemctl enable --now "${SERVICE_NAME}-ping.timer" >/dev/null
}

cmd_ping() {
  need_root
  for_each_pulse_env send_heartbeat
}

sync_pulse_from_panel() {
  local cfg hash toml command
  cfg=$(api GET "/api/hpx_pulse/agent/config")
  hash=$(echo "$cfg" | jq -r '.config_hash')
  command=$(echo "$cfg" | jq -r '.agent_command // empty')
  toml=$(echo "$cfg" | jq -r '.tunnel_toml // .backpack_toml // empty')
  TUNNEL_MODE=$(echo "$cfg" | jq -r '.tunnel_mode // "direct_l3"')
  CONTROL_PORT=$(echo "$cfg" | jq -r '.control_port // empty')
  IRAN_PUBLIC_IP=$(echo "$cfg" | jq -r '.iran_public_ip // empty')
  ABROAD_PUBLIC_IP=$(echo "$cfg" | jq -r '.abroad_public_ip // empty')
  PORT_FORWARDS=$(echo "$cfg" | jq -c '.port_forwards // []')

  if [ "$hash" != "${CONFIG_HASH:-}" ] || [ "$command" = "start" ] || [ "$command" = "restart" ]; then
    apply_tunnel_config "$toml"
    CONFIG_HASH="$hash"
    api POST "/api/hpx_pulse/agent/ack" \
      "$(jq -nc --arg c "${command:-start}" '{command:$c, status:"running", message:"HPX config applied"}')" >/dev/null || true
  else
    open_iran_firewall
    check_abroad_backends
  fi
  write_env
  send_heartbeat
}

# TCP connect RTT in ms (reverse tunnels — ICMP is often blocked on VPS).
measure_tcp_ms() {
  local host="$1" port="$2"
  [ -n "$host" ] && [ -n "$port" ] || return 1
  local out=""
  if has python3; then
    out=$(python3 -c "
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
" 2>/dev/null || true)
  elif has python; then
    out=$(python -c "
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
" 2>/dev/null || true)
  elif has bash; then
    local start end ms
    start=$(date +%s%N 2>/dev/null || echo 0)
    if timeout 3 bash -c "echo >/dev/tcp/${host}/${port}" 2>/dev/null; then
      end=$(date +%s%N 2>/dev/null || echo 0)
      if [ "$start" != 0 ] && [ "$end" != 0 ]; then
        ms=$(( (end - start) / 1000000 ))
        out="$ms"
      fi
    fi
  fi
  [ -n "$out" ] && echo "$out"
}

measure_icmp_ms() {
  local peer="$1"
  [ -n "$peer" ] && has ping || return 1
  ping -c 3 -W 2 "$peer" 2>/dev/null | tail -1 | sed -n 's/.*= \([0-9.]*\)\/.*/\1/p'
}

first_forward_listen_port() {
  echo "${PORT_FORWARDS:-}" | tr -d '[]"' | cut -d',' -f1 | cut -d'=' -f1 | tr -d ' '
}

send_heartbeat() {
  local running="false"
  local link="false"
  local lat="" lat_json="null"
  local msg="HPX Pulse sync"
  local fwd_json="null"
  local control_lat="" forward_lat="" fwd_port=""
  local hb_ok=0
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
      # Abroad measures live user-path: Iran public IP + forwarded port (e.g. 443).
      # Control-port-only ping looked "up" while real configs still got -1.
      if [ "${PULSE_SIDE:-}" = "abroad" ] && [ "$running" = "true" ] \
        && [ -n "${IRAN_PUBLIC_IP:-}" ]; then
        fwd_port="$(first_forward_listen_port)"
        if [ -n "${CONTROL_PORT:-}" ]; then
          control_lat="$(measure_tcp_ms "$IRAN_PUBLIC_IP" "$CONTROL_PORT" || true)"
        fi
        if [ -n "$fwd_port" ]; then
          forward_lat="$(measure_tcp_ms "$IRAN_PUBLIC_IP" "$fwd_port" || true)"
        fi
        if [ -n "$forward_lat" ]; then
          lat="$forward_lat"
          fwd_json="true"
          msg="user path OK (Iran:${fwd_port})"
        elif [ -n "$control_lat" ]; then
          # Tunnel control works but 443 path dead — configs will show -1
          lat="$control_lat"
          fwd_json="false"
          msg="control OK but Iran:${fwd_port:-443} closed — open firewall + Xray on abroad 127.0.0.1:${fwd_port:-443}"
        else
          fwd_json="false"
          msg="cannot reach Iran tunnel/control — check Iran IP/firewall"
        fi
      fi
      ;;
  esac

  [ -n "$lat" ] && lat_json="$lat"
  # Iran must not overwrite abroad's diagnostic message every 5s.
  if [ "${PULSE_SIDE:-}" = "iran" ] && [[ "${TUNNEL_MODE:-}" == reverse_* ]]; then
    api POST "/api/hpx_pulse/agent/heartbeat" \
      "$(jq -nc \
        --arg s "running" \
        --arg h "$(hostname -f 2>/dev/null || hostname)" \
        --argjson tr "$running" \
        --argjson iu "$link" \
        '{status:$s, host:$h, tunnel_running:$tr, iface_up:$iu}')" \
      >/dev/null && hb_ok=1
  else
    api POST "/api/hpx_pulse/agent/heartbeat" \
      "$(jq -nc \
        --arg s "running" \
        --arg h "$(hostname -f 2>/dev/null || hostname)" \
        --arg m "$msg" \
        --argjson tr "$running" \
        --argjson iu "$link" \
        --argjson lm "$lat_json" \
        --argjson fo "$fwd_json" \
        '{status:$s, host:$h, tunnel_running:$tr, iface_up:$iu, latency_ms:($lm|tonumber? // null), forward_ok:$fo, message:$m}')" \
      >/dev/null && hb_ok=1
  fi
  [ "$hb_ok" = 1 ] || warn "heartbeat to panel failed — try: hpx-pulse-agent set-panel-url https://domain (no :8000)"
  [ "$hb_ok" = 1 ]
}

cmd_join() {
  need_root
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
  if [ "${#token}" -lt 8 ]; then
    die "join token too short (${#token} chars) — copy the real hpxpi_/hpxpa_ token from panel (Tokens button), not the word TOKEN"
  fi
  case "$token" in
    TOKEN|TOKEN_IRAN|TOKEN_ABROAD)
      die "replace TOKEN with the real hpxpi_/hpxpa_ value from panel (Tokens button)"
      ;;
    hpxpi_*|hpxpa_*) ;;
    *)
      warn "token should start with hpxpi_ (iran) or hpxpa_ (abroad) — double-check you copied from panel"
      ;;
  esac

  PANEL_URL="${panel_url%/}"
  PULSE_SIDE="$side"
  log "join starting (side=${side})..."

  ensure_deps
  local host body claim
  host="$(hostname -f 2>/dev/null || hostname)"
  body=$(jq -nc --arg t "$token" --arg h "$host" --arg s "$side" '{join_token:$t, host:$h, side:$s}')

  log "claiming join token (${side})..."
  local claim_tmp http_code base claim=""
  claim_tmp="$(mktemp)"
  while IFS= read -r base; do
    [ -n "$base" ] || continue
    http_code=$(curl --http1.1 --connect-timeout 15 --max-time 90 -sS -w "%{http_code}" -o "$claim_tmp" \
      -X POST -H "Content-Type: application/json" -d "$body" \
      "${base}/api/hpx_pulse/agent/claim" 2>/dev/null) || http_code="000"
    if [ "$http_code" = "200" ]; then
      claim="$(cat "$claim_tmp")"
      [ "$base" != "${PANEL_URL%/}" ] && log "panel claim OK at ${base} (using this for agent)"
      PANEL_URL="$base"
      break
    fi
  done < <(panel_api_bases)
  rm -f "$claim_tmp"
  if [ -z "$claim" ]; then
    die "claim failed — use real token from panel Tokens button; if Iran cannot reach :8000 use --panel-url https://domain (443)"
  fi

  AGENT_KEY=$(echo "$claim" | jq -r '.agent_key')
  PULSE_ID=$(echo "$claim" | jq -r '.pulse_id')
  CONFIG_HASH=$(echo "$claim" | jq -r '.config_hash')
  TUNNEL_MODE=$(echo "$claim" | jq -r '.tunnel_mode // "direct_l3"')
  CONTROL_PORT=$(echo "$claim" | jq -r '.control_port // empty')
  IRAN_PUBLIC_IP=$(echo "$claim" | jq -r '.iran_public_ip // empty')
  ABROAD_PUBLIC_IP=$(echo "$claim" | jq -r '.abroad_public_ip // empty')
  PORT_FORWARDS=$(echo "$claim" | jq -c '.port_forwards // []')
  HPX_AGENT_ASSETS_BASE=$(echo "$claim" | jq -r '.agent_assets_base // empty')
  [ -n "$AGENT_KEY" ] && [ "$AGENT_KEY" != "null" ] || die "missing agent_key from panel"

  install_self
  write_env
  check_local_forward_conflicts
  ensure_engine
  apply_tunnel_config "$(echo "$claim" | jq -r '.tunnel_toml // .backpack_toml // empty')"
  write_env
  install_agent_systemd

  api POST "/api/hpx_pulse/agent/ack" \
    "$(jq -nc '{command:"start", status:"running", message:"HPX Pulse joined"}')" >/dev/null || true
  if send_heartbeat; then
    write_env
    log "ready on ${side} — pulse_id=${PULSE_ID} (panel shows agent connected)"
  else
    write_env
    warn "tunnel is running locally but panel heartbeat failed at ${PANEL_URL}"
    warn "from Iran, port :8000 is often blocked — try:"
    warn "  sudo hpx-pulse-agent set-panel-url https://YOUR_DOMAIN"
    warn "  (no :8000 if nginx serves panel on 443) then: sudo hpx-pulse-agent sync"
    log "ready on ${side} — pulse_id=${PULSE_ID} (fix PANEL_URL so panel shows connected)"
  fi
}

cmd_sync() {
  need_root
  load_env 2>/dev/null || {
    local f
    for f in "$AGENTS_DIR"/*.env; do
      [ -f "$f" ] && load_env_file "$f" && break
    done
  }
  # Pull latest agent script once so firewall/ping fixes apply without re-join.
  if hp_curl "https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-pulse-agent.sh" \
      -o "$INSTALL_DIR/hpx-pulse-agent.sh.new" 2>/dev/null \
    || { [ -n "${PANEL_URL:-}" ] \
      && hp_curl "${PANEL_URL%/}/api/hpx_pulse/agent/hpx-pulse-agent.sh" \
        -o "$INSTALL_DIR/hpx-pulse-agent.sh.new" 2>/dev/null; }; then
    if [ -s "$INSTALL_DIR/hpx-pulse-agent.sh.new" ] \
      && ! cmp -s "$INSTALL_DIR/hpx-pulse-agent.sh.new" "$INSTALL_DIR/hpx-pulse-agent.sh" 2>/dev/null; then
      mv "$INSTALL_DIR/hpx-pulse-agent.sh.new" "$INSTALL_DIR/hpx-pulse-agent.sh"
      chmod 755 "$INSTALL_DIR/hpx-pulse-agent.sh"
      ln -sfn "$INSTALL_DIR/hpx-pulse-agent.sh" "$BIN_LINK"
      log "agent updated from GitHub — re-exec sync"
      exec "$BIN_LINK" sync
    fi
    rm -f "$INSTALL_DIR/hpx-pulse-agent.sh.new"
  fi
  ensure_engine
  load_env 2>/dev/null || true
  migrate_legacy_agent_registration
  for_each_pulse_env sync_pulse_from_panel
}

cmd_set_panel_url() {
  need_root
  local url="${1:-}"
  [ -n "$url" ] || die "usage: set-panel-url https://your-panel-domain"
  url="${url%/}"
  load_env 2>/dev/null || true
  PANEL_URL="$url"
  write_env
  local env_file
  if [ -d "$AGENTS_DIR" ]; then
    for env_file in "$AGENTS_DIR"/*.env; do
      [ -f "$env_file" ] || continue
      sed -i "s|^PANEL_URL=.*|PANEL_URL=${PANEL_URL}|" "$env_file"
    done
  fi
  log "PANEL_URL set to ${PANEL_URL}"
  for_each_pulse_env send_heartbeat && log "heartbeat OK — panel should show connected" \
    || warn "still cannot reach panel — open port 443 from Iran or set PANEL_URL_FALLBACK"
}

cmd_uninstall_engine() {
  need_root
  echo ""
  echo "  ┌────────────────────────────────────────┐"
  echo "  │  HPX TUNNEL ENGINE — uninstall          │"
  echo "  └────────────────────────────────────────┘"
  echo ""
  if [ -e "$ENGINE_BIN" ] || [ -L "$ENGINE_BIN" ]; then
    rm -f "$ENGINE_BIN"
    log "removed ${ENGINE_BIN}"
  else
    warn "not installed at ${ENGINE_BIN}"
  fi
  echo ""
  echo "  ╔════════════════════════════════════════╗"
  echo "  ║       ✓  ENGINE REMOVED                ║"
  echo "  ╚════════════════════════════════════════╝"
  echo ""
  log "Reinstall: sudo hpx-pulse-agent install-engine --force"
  log "Or: curl .../hpx-tunnel-engine-install.sh | sudo env HPX_PREFER_GITHUB=1 bash"
  echo ""
}

cmd_install_engine() {
  need_root
  local force=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --force|-f) force=1; shift ;;
      *) die "usage: install-engine [--force]" ;;
    esac
  done
  load_env 2>/dev/null || true
  if [ -z "${HPX_PREFER_GITHUB:-}" ] && { [ "${PULSE_SIDE:-}" = "iran" ] || [ -z "${PULSE_SIDE:-}" ]; }; then
    HPX_PREFER_GITHUB=1
  fi
  export HPX_PREFER_GITHUB
  [ "$force" = 1 ] && export HPX_ENGINE_FORCE=1
  ensure_engine
  [ -x "$ENGINE_BIN" ] || die "engine install failed"
  log "HPX tunnel engine ready: $(engine_bin)"
}

cmd_status() {
  local env_file svc
  echo "HPX Pulse Agent"
  if [ -d "$AGENTS_DIR" ] && compgen -G "$AGENTS_DIR/*.env" >/dev/null; then
    for env_file in "$AGENTS_DIR"/*.env; do
      [ -f "$env_file" ] || continue
      load_env_file "$env_file" || continue
      svc="$(tunnel_service_name)"
      echo "  --- pulse ${PULSE_ID:-?} ---"
      echo "  panel : ${PANEL_URL:-not set}"
      echo "  side  : ${PULSE_SIDE:-?}"
      echo "  mode  : ${TUNNEL_MODE:-direct_l3}"
      echo "  config: ${TUNNEL_CFG:-$(tunnel_cfg_path 2>/dev/null || echo '?')}"
      echo "  forwards: ${PORT_FORWARDS:-[]}"
      if tunnel_service_active; then
        echo "  tunnel: running (${svc})"
      else
        echo "  tunnel: stopped (${svc})"
      fi
      if [ "${PULSE_SIDE:-}" = "iran" ] && [[ "${TUNNEL_MODE:-}" == reverse_* ]]; then
        if tunnel_port_listening; then
          echo "  link  : control port ${CONTROL_PORT:-?} listening"
        else
          echo "  link  : control port not listening"
        fi
      fi
    done
    return
  fi
  load_env 2>/dev/null || true
  echo "  panel : ${PANEL_URL:-not set}"
  echo "  side  : ${PULSE_SIDE:-?}"
  echo "  mode  : ${TUNNEL_MODE:-direct_l3}"
  echo "  pulse : ${PULSE_ID:-?}"
  echo "  config: ${TUNNEL_CFG:-$(tunnel_cfg_path 2>/dev/null || echo '?')}"
  if tunnel_service_active; then
    echo "  tunnel: running ($(tunnel_service_name))"
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
  set-panel-url URL       when :8000 is blocked from Iran, use https://domain (443)
  install-engine [--force]  install hpx-tunnel-engine (GitHub-first on Iran)
  uninstall-engine        remove engine binary (for reinstall tests)
  sync | ping | status

Engine manual install (if join hangs on panel mirror):
  curl --http1.1 -fsSL .../hpx-tunnel-engine-install.sh | sudo env HPX_PREFER_GITHUB=1 bash
  sudo hpx-pulse-agent sync

Engine reinstall test:
  sudo hpx-pulse-agent uninstall-engine
  sudo hpx-pulse-agent install-engine --force
  # or one-liner:
  HPX_ENGINE_FORCE=1 curl .../hpx-tunnel-engine-install.sh | sudo env HPX_PREFER_GITHUB=1 bash
EOF
}

main() {
  local cmd="${1:-status}"
  shift || true
  case "$cmd" in
    join) cmd_join "$@" ;;
    set-panel-url) cmd_set_panel_url "$@" ;;
    install-engine) shift; cmd_install_engine "$@" ;;
    uninstall-engine) cmd_uninstall_engine ;;
    sync) cmd_sync ;;
    ping) cmd_ping ;;
    status) cmd_status ;;
    -h|--help|help) usage ;;
    *) die "unknown: $cmd" ;;
  esac
}

main "$@"

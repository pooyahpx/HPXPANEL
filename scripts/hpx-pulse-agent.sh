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

# Set HPX_INSECURE=1 (or pass --insecure) when panel TLS cert is self-signed / wrong host / IP URL.
CURL_INSECURE_ARGS=()

refresh_curl_insecure() {
  if [ "${HPX_INSECURE:-0}" = "1" ] || [ "${HPX_INSECURE:-}" = "true" ]; then
    CURL_INSECURE_ARGS=(-k)
  else
    CURL_INSECURE_ARGS=()
  fi
}

refresh_curl_insecure

# Survives command-substitution subshells (set -u safe). Written by curl_panel_post.
CURL_LAST_ERR=""
CURL_ERR_STATE="${TMPDIR:-/tmp}/.hpx_pulse_curl_err.$$"

# HTTP/1.1 avoids curl error 92 (PROTOCOL_ERROR) on some filtered routes (e.g. Iran).
hp_curl() {
  curl --http1.1 --connect-timeout 30 --max-time 120 --retry 3 --retry-delay 2 -fsSL "${CURL_INSECURE_ARGS[@]}" "$@"
}

# Shorter timeout for panel mirror — fall back to GitHub quickly when panel port is blocked.
hp_panel_curl() {
  curl --http1.1 --connect-timeout 15 --max-time 120 --retry 1 --retry-delay 2 -fsSL "${CURL_INSECURE_ARGS[@]}" "$@"
}

_curl_panel_post_save_err() {
  local err_tmp="$1"
  CURL_LAST_ERR="$(tr '\n' ' ' <"$err_tmp" 2>/dev/null | sed 's/[[:space:]]\+/ /g' | cut -c1-220)"
  printf '%s' "${CURL_LAST_ERR}" >"$CURL_ERR_STATE" 2>/dev/null || true
}

curl_panel_post() {
  # Usage: curl_panel_post OUTFILE BODY URL
  # Prints http_code; stores stderr in CURL_ERR_STATE (readable after $() subshell).
  local outfile="$1" body="$2" url="$3"
  local err_tmp http_code
  err_tmp="$(mktemp)"
  CURL_LAST_ERR=""
  : >"$CURL_ERR_STATE" 2>/dev/null || true
  http_code=$(curl --http1.1 --connect-timeout 15 --max-time 90 -sS -w "%{http_code}" -o "$outfile" \
    "${CURL_INSECURE_ARGS[@]}" \
    -X POST -H "Content-Type: application/json" -d "$body" \
    "$url" 2>"$err_tmp") || http_code="000"
  _curl_panel_post_save_err "$err_tmp"
  rm -f "$err_tmp"
  if [ "$http_code" = "000" ] && [ "${#CURL_INSECURE_ARGS[@]}" -eq 0 ]; then
    case "${CURL_LAST_ERR,,}" in
      *ssl*|*certificate*|*tls*|*schannel*|*handshake*)
        warn "TLS verify failed for ${url} — retrying with -k (HPX_INSECURE)"
        err_tmp="$(mktemp)"
        http_code=$(curl --http1.1 --connect-timeout 15 --max-time 90 -sS -k -w "%{http_code}" -o "$outfile" \
          -X POST -H "Content-Type: application/json" -d "$body" \
          "$url" 2>"$err_tmp") || http_code="000"
        _curl_panel_post_save_err "$err_tmp"
        rm -f "$err_tmp"
        if [ "$http_code" != "000" ]; then
          CURL_INSECURE_ARGS=(-k)
          export HPX_INSECURE=1
        fi
        ;;
    esac
  fi
  printf '%s' "$http_code"
}

read_curl_last_err() {
  CURL_LAST_ERR="$(cat "$CURL_ERR_STATE" 2>/dev/null || true)"
}

probe_panel_reachability() {
  # Prefer unauthenticated /health (200). /api/system returns 401 without JWT and
  # was scaring operators even when the panel was fine.
  local base="${1%/}" code err_tmp
  err_tmp="$(mktemp)"
  code=$(curl --http1.1 --connect-timeout 8 --max-time 12 -sS -o /dev/null -w "%{http_code}" \
    "${CURL_INSECURE_ARGS[@]}" "${base}/health" 2>"$err_tmp") || code="000"
  if [ "$code" = "000" ] && [ "${#CURL_INSECURE_ARGS[@]}" -eq 0 ]; then
    code=$(curl --http1.1 --connect-timeout 8 --max-time 12 -sS -k -o /dev/null -w "%{http_code}" \
      "${base}/health" 2>"$err_tmp") || code="000"
  fi
  # Legacy panels / reversed proxies: accept any HTTP response as "reachable".
  if [ "$code" = "000" ]; then
    code=$(curl --http1.1 --connect-timeout 8 --max-time 12 -sS -o /dev/null -w "%{http_code}" \
      "${CURL_INSECURE_ARGS[@]}" "${base}/api/system" 2>"$err_tmp") || code="000"
  fi
  if [ "$code" = "000" ]; then
    warn "cannot reach panel at ${base} ($(tr '\n' ' ' <"$err_tmp" | cut -c1-160))"
    warn "from this VPS run: curl -v --connect-timeout 10 ${base}/health"
    warn "fix: route blocked, wrong DNS, or host firewall — panel must answer from THIS host"
  elif [ "$code" = "401" ] || [ "$code" = "403" ]; then
    log "panel reachable at ${base} ✓"
  elif [ "$code" = "200" ] || [ "$code" = "204" ]; then
    log "panel reachable at ${base} ✓"
  else
    log "panel reachable at ${base} ✓ (HTTP ${code})"
  fi
  rm -f "$err_tmp"
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
HPX_INSECURE=${HPX_INSECURE:-0}
EOF
  chmod 600 "$dest"
}

write_env() {
  # Per-pulse file is authoritative for multi-tunnel hosts. Never clobber the
  # global agent.env with another pulse's AGENT_KEY while siblings exist —
  # that caused CLI/heartbeat confusion and delete/leave races.
  if [ -n "${PULSE_ID:-}" ] && [ "${PULSE_ID}" != "0" ]; then
    mkdir -p "$AGENTS_DIR"
    write_env_file "${AGENTS_DIR}/${PULSE_ID}.env"
    local n=0
    n="$(find "$AGENTS_DIR" -maxdepth 1 -type f -name '*.env' 2>/dev/null | wc -l | tr -d ' ')"
    if [ "${n:-0}" -le 1 ]; then
      write_env_file "$ENV_FILE"
    elif [ ! -f "$ENV_FILE" ]; then
      write_env_file "$ENV_FILE"
    fi
    return 0
  fi
  write_env_file "$ENV_FILE"
}

load_env_file() {
  local file="$1"
  [ -f "$file" ] || return 1
  # shellcheck disable=SC1090
  set -a; source "$file"; set +a
  refresh_curl_insecure
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

is_port_listening() {
  local port="$1"
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

pulse_registration_active() {
  local pid="$1"
  local env_file="${AGENTS_DIR}/${pid}.env"
  [ -f "$env_file" ] || return 1
  (
    load_env_file "$env_file"
    PULSE_ID="$pid"
    case "${TUNNEL_MODE:-direct_l3}" in
      direct_l3)
        tunnel_service_active && exit 0
        tunnel_iface_up && exit 0
        ;;
      reverse_*)
        tunnel_service_active && exit 0
        ;;
      *)
        tunnel_service_active && exit 0
        ;;
    esac
    exit 1
  )
}

remove_pulse_local_state() {
  local pid="$1" svc saved_pulse_id saved_side port
  [ -n "$pid" ] || return 0
  saved_pulse_id="${PULSE_ID:-}"
  saved_side="${PULSE_SIDE:-}"
  if [ -f "${AGENTS_DIR}/${pid}.env" ]; then
    load_env_file "${AGENTS_DIR}/${pid}.env"
    PULSE_ID="$pid"
    while IFS= read -r port; do
      [ -n "$port" ] || continue
      free_orphan_listen_port "$port" || true
      # Drop leftover ACCEPT rules this agent inserted (panel delete does not wipe iptables).
      if has iptables; then
        iptables -D INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null || true
        iptables -D INPUT -p udp --dport "$port" -j ACCEPT 2>/dev/null || true
      fi
    done < <(collect_forward_listen_ports "${PORT_FORWARDS:-}")
    if [ -n "${CONTROL_PORT:-}" ] && has iptables; then
      iptables -D INPUT -p tcp --dport "$CONTROL_PORT" -j ACCEPT 2>/dev/null || true
      iptables -D INPUT -p udp --dport "$CONTROL_PORT" -j ACCEPT 2>/dev/null || true
    fi
  fi
  svc="$(tunnel_service_name)"
  systemctl stop "${svc}.service" 2>/dev/null || true
  systemctl disable "${svc}.service" 2>/dev/null || true
  rm -f "/etc/systemd/system/${svc}.service"
  rm -f "${AGENTS_DIR}/${pid}.env"
  rm -f "${ETC_DIR}/l3-pulse-${pid}.toml"
  # Defer daemon-reload so deleting one pulse does not stall sibling tunnels.
  PURGE_NEED_RELOAD=1
  PULSE_ID="$saved_pulse_id"
  PULSE_SIDE="$saved_side"
}

prune_stale_agent_registrations() {
  [ -d "$AGENTS_DIR" ] || return 0
  local env_file existing_id toml
  for env_file in "$AGENTS_DIR"/*.env; do
    [ -f "$env_file" ] || continue
    existing_id="$(basename "$env_file" .env)"
    [ "$existing_id" = "${PULSE_ID:-}" ] && continue
    toml="${ETC_DIR}/l3-pulse-${existing_id}.toml"
    # Intact multi-tunnel peer (env+toml) — never wipe during a brief restart/join race.
    if [ -f "$toml" ]; then
      continue
    fi
    if pulse_registration_active "$existing_id"; then
      continue
    fi
    log "removing stale local registration for pulse ${existing_id} (no toml / inactive)"
    remove_pulse_local_state "$existing_id"
  done
}

free_orphan_listen_port() {
  local port="$1" env_file existing_id
  is_port_listening "$port" || return 0
  for env_file in "$AGENTS_DIR"/*.env; do
    [ -f "$env_file" ] || continue
    existing_id="$(basename "$env_file" .env)"
    [ "$existing_id" = "${PULSE_ID:-}" ] && continue
    pulse_registration_active "$existing_id" || continue
    load_env_file "$env_file"
    while IFS= read -r p; do
      if [ "$p" = "$port" ]; then
        warn "port ${port} still held by active pulse ${existing_id}"
        return 1
      fi
    done < <(collect_forward_listen_ports "${PORT_FORWARDS:-}")
  done
  warn "port ${port} held by orphan process — releasing for new join (this port only)"
  if has fuser; then
    fuser -k "${port}/tcp" 2>/dev/null || true
  elif has ss; then
    # Kill only the listener on this port — NEVER pkill all hpx-tunnel-engine (wipes sibling pulses).
    local pid
    pid="$(ss -tlnp "sport = :${port}" 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | head -1)"
    if [ -n "$pid" ]; then
      kill "$pid" 2>/dev/null || true
    fi
  fi
  sleep 1
  return 0
}

check_local_forward_conflicts() {
  [ "${PULSE_SIDE:-}" = "iran" ] || return 0
  [ -d "$AGENTS_DIR" ] || return 0
  prune_stale_agent_registrations
  local env_file existing_id port new_port
  while IFS= read -r new_port; do
    [ -n "$new_port" ] || continue
    for env_file in "$AGENTS_DIR"/*.env; do
      [ -f "$env_file" ] || continue
      existing_id="$(basename "$env_file" .env)"
      [ "$existing_id" = "${PULSE_ID:-}" ] && continue
      pulse_registration_active "$existing_id" || continue
      while IFS= read -r port; do
        [ -n "$port" ] || continue
        if [ "$port" = "$new_port" ]; then
          die "Iran listen port ${port} already used by active pulse ${existing_id} — stop it (sudo hpx-pulse-agent leave ${existing_id}) or use different external ports"
        fi
      done < <(collect_forward_listen_ports "$(grep '^PORT_FORWARDS=' "$env_file" | cut -d= -f2-)")
    done
    free_orphan_listen_port "$new_port" || die "Iran listen port ${new_port} already in use — run: sudo hpx-pulse-agent leave ${existing_id:-ID}"
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
  # If join command has :8000, also try bare host (nginx/caddy on 443).
  if [[ "$u" =~ ^(https?://[^:/]+):8000$ ]]; then
    _emit_base "${BASH_REMATCH[1]}"
  fi
  # Only probe :8000 for plain http hosts — https on default 443 must not fall back to :8000
  # (that 000 overwrites a real 401 claim error and confuses operators).
  if [[ "$u" =~ ^(http://[^:/]+)$ ]]; then
    _emit_base "${u}:8000"
  fi
}

API_LAST_HTTP_CODE="000"
API_LAST_BODY=""
# Consecutive confirmed 401s before wiping local tunnel (avoids panel-upgrade false positives).
REVOKE_STREAK_DIR="${ETC_DIR}/.revoke-streak"
REVOKE_CONFIRM_HITS=3

panel_registration_revoked() {
  # Only a real "Invalid agent key" 401 means the pulse was deleted / tokens regenerated.
  # Never treat 404/502/503/000 as revoke — those happen during panel restarts and would
  # permanently destroy tunnels on every upgrade (seen on multi-server fleets).
  # Also ignore generic CDN/WAF 401s that are not from the panel agent auth check.
  [ "$API_LAST_HTTP_CODE" = "401" ] || return 1
  case "${API_LAST_BODY:-}" in
    *[Ii]nvalid*[Aa]gent*[Kk]ey*|*"Invalid agent key"*|*"invalid agent key"*) return 0 ;;
  esac
  return 1
}

_revoke_streak_path() {
  local pid="${1:-${PULSE_ID:-0}}"
  mkdir -p "$REVOKE_STREAK_DIR" 2>/dev/null || true
  echo "${REVOKE_STREAK_DIR}/${pid}.hits"
}

_reset_revoke_streak() {
  rm -f "$(_revoke_streak_path "${1:-${PULSE_ID:-}}")" 2>/dev/null || true
}

_bump_revoke_streak() {
  local pid="${1:-${PULSE_ID:-}}" path hits
  [ -n "$pid" ] || return 1
  path="$(_revoke_streak_path "$pid")"
  hits=0
  [ -f "$path" ] && hits="$(cat "$path" 2>/dev/null || echo 0)"
  hits=$((hits + 1))
  printf '%s' "$hits" >"$path" 2>/dev/null || true
  [ "$hits" -ge "$REVOKE_CONFIRM_HITS" ]
}

cleanup_revoked_pulse() {
  local pid="${1:-${PULSE_ID:-}}"
  [ -n "$pid" ] || return 0
  if ! _bump_revoke_streak "$pid"; then
    warn "pulse ${pid} got HTTP 401 (invalid agent key) — will remove local tunnel after ${REVOKE_CONFIRM_HITS} confirms (not yet)"
    return 0
  fi
  log "pulse ${pid} confirmed gone on panel (repeated 401) — removing local tunnel (${PULSE_SIDE:-?})"
  _reset_revoke_streak "$pid"
  remove_pulse_local_state "$pid"
}

api_request() {
  local method="$1" path="$2" body="${3:-}"
  local base url attempt tmp http_code resp
  API_LAST_HTTP_CODE="000"
  API_LAST_BODY=""
  while IFS= read -r base; do
    [ -n "$base" ] || continue
    url="${base%/}${path}"
    for attempt in 1 2 3; do
      tmp="$(mktemp)"
      local args=(--http1.1 --connect-timeout 15 --max-time 90 -sS -X "$method"
        -H "X-HPX-Pulse-Agent-Key: ${AGENT_KEY}" -H "X-HPX-Pulse-Side: ${PULSE_SIDE}" -H "Accept: application/json"
        -w "%{http_code}" -o "$tmp" "${CURL_INSECURE_ARGS[@]}")
      [ -n "$body" ] && args+=(-H "Content-Type: application/json" -d "$body")
      http_code=$(curl "${args[@]}" "$url" 2>/dev/null) || http_code="000"
      API_LAST_HTTP_CODE="$http_code"
      API_LAST_BODY="$(tr -d '\r' <"$tmp" 2>/dev/null | head -c 400 || true)"
      if [ "$http_code" = "200" ]; then
        resp=$(cat "$tmp")
        rm -f "$tmp"
        if [ "$base" != "${PANEL_URL%/}" ]; then
          log "panel API reachable at ${base} (was ${PANEL_URL}) — updating PANEL_URL"
          PANEL_URL="$base"
        fi
        printf '%s' "$resp"
        return 0
      fi
      rm -f "$tmp"
      [ "$http_code" != "000" ] && return 1
      [ "$attempt" -lt 3 ] && sleep 2
    done
  done < <(panel_api_bases)
  return 1
}

api() {
  api_request "$@"
}

verify_registrations_with_panel() {
  [ -d "$AGENTS_DIR" ] || return 0
  local env_file pid saved_panel saved_key saved_side saved_id cfg command
  local skip_revoke="${SKIP_REVOKE_FOR_PULSE:-}"
  saved_panel="${PANEL_URL:-}"
  saved_key="${AGENT_KEY:-}"
  saved_side="${PULSE_SIDE:-}"
  saved_id="${PULSE_ID:-}"
  for env_file in "$AGENTS_DIR"/*.env; do
    [ -f "$env_file" ] || continue
    load_env_file "$env_file" || continue
    pid="$(basename "$env_file" .env)"
    PULSE_ID="$pid"
    if cfg=$(api_request GET "/api/hpx_pulse/agent/config"); then
      _reset_revoke_streak "$pid"
      command=$(echo "$cfg" | jq -r '.agent_command // empty' 2>/dev/null || true)
      if [ "$command" = "leave" ] || [ "$command" = "uninstall" ]; then
        log "panel requested local removal for pulse ${pid} only (siblings untouched)"
        _reset_revoke_streak "$pid"
        # Ack before wiping keys so panel soft-delete can reap this side.
        api POST "/api/hpx_pulse/agent/ack" \
          "$(jq -nc --arg c "$command" '{command:$c, status:"stopped", message:"local tunnel removed"}')" \
          >/dev/null || true
        remove_pulse_local_state "$pid"
      fi
      continue
    fi
    if panel_registration_revoked; then
      if [ -n "$skip_revoke" ] && [ "$pid" = "$skip_revoke" ]; then
        warn "pulse ${pid} got 401 right after join claim — not wiping (will retry on next sync)"
      else
        cleanup_revoked_pulse "$pid"
      fi
    elif [ "${API_LAST_HTTP_CODE:-000}" = "000" ]; then
      # Brief blip while joining another pulse on the same host — keep quiet.
      :
    else
      warn "pulse ${pid} config fetch failed (HTTP ${API_LAST_HTTP_CODE:-?}) — keeping local tunnel (panel may be restarting)"
    fi
  done
  if [ "${PURGE_NEED_RELOAD:-0}" = 1 ]; then
    systemctl daemon-reload 2>/dev/null || true
    PURGE_NEED_RELOAD=0
  fi
  PANEL_URL="$saved_panel"
  AGENT_KEY="$saved_key"
  PULSE_SIDE="$saved_side"
  PULSE_ID="$saved_id"
}

prune_orphan_configs() {
  # Full sweep: crash-loop units (missing toml), orphans, stray configs.
  purge_stale_tunnel_units
}

_pulse_id_from_tunnel_unit() {
  local u="$1"
  u="${u%.service}"
  u="${u#hpx-pulse-tunnel-}"
  [[ "$u" =~ ^[0-9]+$ ]] && echo "$u"
}

remove_tunnel_unit_fully() {
  local id="$1" svc
  [ -n "$id" ] || return 0
  svc="hpx-pulse-tunnel-${id}"
  log "purging leftover tunnel unit ${svc} (missing config)"
  systemctl stop "${svc}.service" 2>/dev/null || true
  systemctl reset-failed "${svc}.service" 2>/dev/null || true
  systemctl disable "${svc}.service" 2>/dev/null || true
  rm -f "/etc/systemd/system/${svc}.service"
  rm -f "${ETC_DIR}/l3-pulse-${id}.toml"
  rm -f "${AGENTS_DIR}/${id}.env"
  # Caller batches daemon-reload — avoid reload storms that disrupt sibling tunnels.
  PURGE_NEED_RELOAD=1
}

# Safe multi-tunnel purge:
# - Intact peers (env+toml) are NEVER touched (leave/soft-delete only).
# - toml missing → crash-loop → remove.
# - env missing but toml present + unit active → Sync/join race → leave alone.
# - env missing + unit idle → stale leftover → remove.
purge_stale_tunnel_units() {
  local mine_id="${PULSE_ID:-}" unit id toml envf
  local purged=0
  PURGE_NEED_RELOAD=0
  mkdir -p "$ETC_DIR" "$AGENTS_DIR" 2>/dev/null || true

  _peer_should_purge() {
    local pid="$1" t e
    t="${ETC_DIR}/l3-pulse-${pid}.toml"
    e="${AGENTS_DIR}/${pid}.env"
    if [ ! -f "$t" ]; then
      return 0
    fi
    if [ -f "$e" ]; then
      return 1
    fi
    # toml without env: only purge if the unit is not running (avoid Sync race).
    if systemctl is-active --quiet "hpx-pulse-tunnel-${pid}.service" 2>/dev/null; then
      warn "pulse ${pid} toml present, env pending — not purging (multi-tunnel Sync race)"
      return 1
    fi
    return 0
  }

  while IFS= read -r unit; do
    [ -n "$unit" ] || continue
    id="$(_pulse_id_from_tunnel_unit "$unit")"
    [ -n "$id" ] || continue
    toml="${ETC_DIR}/l3-pulse-${id}.toml"
    envf="${AGENTS_DIR}/${id}.env"

    if [ -n "$mine_id" ] && [ "$id" = "$mine_id" ]; then
      if [ ! -f "$toml" ]; then
        warn "pulse ${id} unit crash-loop (toml missing) — stopping until Sync rewrites config"
        systemctl stop "${unit}" 2>/dev/null || true
        systemctl reset-failed "${unit}" 2>/dev/null || true
      fi
      continue
    fi

    if _peer_should_purge "$id"; then
      remove_tunnel_unit_fully "$id"
      purged=1
    fi
  done < <(systemctl list-unit-files 'hpx-pulse-tunnel-*.service' --no-legend 2>/dev/null | awk '{print $1}')

  for toml in "$ETC_DIR"/l3-pulse-*.toml; do
    [ -f "$toml" ] || continue
    id="${toml##*/l3-pulse-}"
    id="${id%.toml}"
    [ -f "${AGENTS_DIR}/${id}.env" ] && continue
    [ -n "$mine_id" ] && [ "$id" = "$mine_id" ] && continue
    if _peer_should_purge "$id"; then
      remove_tunnel_unit_fully "$id"
      purged=1
    fi
  done

  while IFS= read -r unit; do
    [ -n "$unit" ] || continue
    id="$(_pulse_id_from_tunnel_unit "$unit")"
    [ -n "$id" ] || continue
    [ -n "$mine_id" ] && [ "$id" = "$mine_id" ] && continue
    if _peer_should_purge "$id"; then
      remove_tunnel_unit_fully "$id"
      purged=1
    fi
  done < <(
    systemctl list-units 'hpx-pulse-tunnel-*.service' --no-legend --all --state=running,failed,activating,inactive 2>/dev/null \
      | awk '{print $1}'
  )

  if [ "${PURGE_NEED_RELOAD:-0}" = 1 ] || [ "$purged" = 1 ]; then
    systemctl daemon-reload 2>/dev/null || true
  fi
  PURGE_NEED_RELOAD=0
}

# Throttle heavy purge: ping runs every 5s — never sweep that often (disrupts siblings).
maybe_prune_orphan_configs() {
  local stamp="${ETC_DIR}/.last_orphan_purge" now min_gap=120
  now="$(date +%s 2>/dev/null || echo 0)"
  if [ -f "$stamp" ]; then
    local last
    last="$(cat "$stamp" 2>/dev/null || echo 0)"
    if [ "$now" -gt 0 ] && [ "$last" -gt 0 ] && [ $((now - last)) -lt "$min_gap" ]; then
      return 0
    fi
  fi
  prune_orphan_configs
  mkdir -p "$ETC_DIR" 2>/dev/null || true
  echo "$now" >"$stamp" 2>/dev/null || true
}

ensure_engine() {
  if [ -x "$ENGINE_BIN" ] && [ "${HPX_ENGINE_FORCE:-0}" != "1" ]; then
    local ver=""
    ver="$("$ENGINE_BIN" --version 2>/dev/null | head -1 | tr -d '\r' || true)"
    if [ -n "$ver" ]; then
      log "engine already installed — ${ver}"
    else
      log "engine already installed — ${ENGINE_BIN}"
    fi
    return 0
  fi
  if [ "${HPX_ENGINE_FORCE:-0}" = "1" ]; then
    rm -f "$ENGINE_BIN"
  fi
  if [ -x /usr/local/bin/backpack ] && [ ! -x "$ENGINE_BIN" ] && [ "${HPX_ENGINE_FORCE:-0}" != "1" ]; then
    ln -sf /usr/local/bin/backpack "$ENGINE_BIN"
    log "engine linked from backpack — ${ENGINE_BIN}"
    return 0
  fi
  log "Installing HPX tunnel engine..."
  local installer panel_install_url prefer_github pinned_ver=""
  installer="$(mktemp)"
  panel_install_url=""
  prefer_github="${HPX_PREFER_GITHUB:-}"
  if [ -z "$prefer_github" ] && [ "${PULSE_SIDE:-}" = "iran" ]; then
    prefer_github=1
    log "Iran side — downloading engine from GitHub first (panel mirror often blocked)"
  fi
  if [ -n "${PANEL_URL:-}" ]; then
    panel_install_url="${PANEL_URL%/}/api/hpx_pulse/agent/engine-install.sh"
    pinned_ver="$(hp_panel_curl "${PANEL_URL%/}/api/hpx_pulse/engine" 2>/dev/null | jq -r '.engine_version // empty' 2>/dev/null || true)"
  elif [ -n "${HPX_AGENT_ASSETS_BASE:-}" ]; then
    panel_install_url="${HPX_AGENT_ASSETS_BASE%/}/engine-install.sh"
  fi
  if [ -z "$pinned_ver" ]; then
    pinned_ver="$(hp_curl "https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-tunnel-engine.version" 2>/dev/null | tr -d '[:space:]' || true)"
  fi
  [ -n "$pinned_ver" ] || pinned_ver="1.8.5"
  pinned_ver="${pinned_ver#v}"
  log "engine pin · v${pinned_ver}"
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
      HPX_NO_GITHUB_FALLBACK="${HPX_NO_GITHUB_FALLBACK:-0}" \
      HPX_TUNNEL_ENGINE_VERSION="${HPX_TUNNEL_ENGINE_VERSION:-$pinned_ver}" \
      bash "$installer"
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
  log "engine ready — $("$ENGINE_BIN" --version 2>/dev/null | head -1 || echo "$ENGINE_BIN")"
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
  local proto_tcp=1 proto_udp=0
  case "${TUNNEL_MODE:-}" in
    reverse_kcp|reverse_quic|reverse_udp) proto_tcp=0; proto_udp=1 ;;
  esac
  if has ss; then
    if [ "$proto_udp" = 1 ]; then
      ss -ulnH "sport = :${port}" 2>/dev/null | grep -q .
      return $?
    fi
    ss -tlnH "sport = :${port}" 2>/dev/null | grep -q .
    return $?
  fi
  if has netstat; then
    if [ "$proto_udp" = 1 ]; then
      netstat -uln 2>/dev/null | grep -q ":${port} "
      return $?
    fi
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
  local cfg="$1" engine_bin svc unit_path tmp
  engine_bin="$(engine_bin)"
  svc="$(tunnel_service_name)"
  retire_legacy_tunnel_service "$svc"
  unit_path="/etc/systemd/system/${svc}.service"
  tmp="$(mktemp)"
  cat >"$tmp" <<EOF
[Unit]
Description=HPX Pulse tunnel (pulse ${PULSE_ID:-?})
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${engine_bin} -c ${cfg}
Restart=always
RestartSec=3
Nice=-5
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF
  if [ ! -f "$unit_path" ] || ! cmp -s "$tmp" "$unit_path"; then
    mv "$tmp" "$unit_path"
    systemctl daemon-reload
    systemctl enable "${svc}.service" >/dev/null
  else
    rm -f "$tmp"
  fi
  # Restart only THIS pulse unit (toml already rewritten) — never wildcard siblings.
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
  local udp_control=0
  case "${TUNNEL_MODE:-}" in
    reverse_kcp|reverse_quic|reverse_udp) udp_control=1 ;;
  esac

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

  _allow_port() {
    local p="$1" proto="$2"
    if has ufw && ufw status 2>/dev/null | grep -qi "Status: active"; then
      ufw allow "${p}/${proto}" >/dev/null 2>&1 || true
      log "ufw allow ${p}/${proto}"
    elif has firewall-cmd; then
      firewall-cmd --permanent --add-port="${p}/${proto}" >/dev/null 2>&1 || true
      firewall-cmd --reload >/dev/null 2>&1 || true
      log "firewalld allow ${p}/${proto}"
    elif has iptables; then
      iptables -C INPUT -p "$proto" --dport "$p" -j ACCEPT 2>/dev/null \
        || iptables -I INPUT -p "$proto" --dport "$p" -j ACCEPT
      log "iptables allow ${p}/${proto}"
    else
      warn "open firewall manually: allow ${proto} ${p}"
    fi
  }

  for p in "${ports[@]}"; do
    # User forward ports are always TCP (Xray/VLESS listen).
    if [ -n "${CONTROL_PORT:-}" ] && [ "$p" = "$CONTROL_PORT" ] && [ "$udp_control" = 1 ]; then
      _allow_port "$p" udp
    else
      _allow_port "$p" tcp
    fi
  done

  # TCPMSS clamp on forward ports — critical for TCP/Stealth carriers on broken MTU paths.
  if has iptables; then
    for p in "${ports[@]}"; do
      [ -n "${CONTROL_PORT:-}" ] && [ "$p" = "$CONTROL_PORT" ] && continue
      iptables -t mangle -C POSTROUTING -p tcp --tcp-flags SYN,RST SYN --dport "$p" -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null \
        || iptables -t mangle -A POSTROUTING -p tcp --tcp-flags SYN,RST SYN --dport "$p" -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null || true
      iptables -t mangle -C POSTROUTING -p tcp --tcp-flags SYN,RST SYN --sport "$p" -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null \
        || iptables -t mangle -A POSTROUTING -p tcp --tcp-flags SYN,RST SYN --sport "$p" -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null || true
      # Hard clamp for Iran↔client TCP when path MTU discovery fails.
      case "${TUNNEL_MODE:-}" in
        reverse_stealth|reverse_tcp|reverse_tcpmux|reverse_ws|reverse_wss|reverse_wssmux)
          iptables -t mangle -C POSTROUTING -p tcp --tcp-flags SYN,RST SYN --dport "$p" -j TCPMSS --set-mss 1000 2>/dev/null \
            || iptables -t mangle -A POSTROUTING -p tcp --tcp-flags SYN,RST SYN --dport "$p" -j TCPMSS --set-mss 1000 2>/dev/null || true
          iptables -t mangle -C POSTROUTING -p tcp --tcp-flags SYN,RST SYN --sport "$p" -j TCPMSS --set-mss 1000 2>/dev/null \
            || iptables -t mangle -A POSTROUTING -p tcp --tcp-flags SYN,RST SYN --sport "$p" -j TCPMSS --set-mss 1000 2>/dev/null || true
          ;;
      esac
    done
  fi
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
  ensure_deps
  # Do NOT full-purge every 5s — races with Sync writing env and kills sibling tunnels.
  maybe_prune_orphan_configs
  verify_registrations_with_panel
  for_each_pulse_env send_heartbeat
}

sync_pulse_from_panel() {
  local cfg hash toml command
  if ! cfg=$(api_request GET "/api/hpx_pulse/agent/config"); then
    if panel_registration_revoked; then
      cleanup_revoked_pulse "${PULSE_ID:-}"
      return 0
    fi
    warn "panel config fetch failed (HTTP ${API_LAST_HTTP_CODE:-?}) — keeping tunnel; retry after panel is up"
    return 1
  fi
  _reset_revoke_streak "${PULSE_ID:-}"
  hash=$(echo "$cfg" | jq -r '.config_hash')
  command=$(echo "$cfg" | jq -r '.agent_command // empty')
  if [ "$command" = "leave" ] || [ "$command" = "uninstall" ]; then
    log "panel requested local removal for pulse ${PULSE_ID}"
    _reset_revoke_streak "${PULSE_ID:-}"
    api POST "/api/hpx_pulse/agent/ack" \
      "$(jq -nc --arg c "$command" '{command:$c, status:"stopped", message:"local tunnel removed"}')" \
      >/dev/null || true
    remove_pulse_local_state "$PULSE_ID"
    return 0
  fi
  toml=$(echo "$cfg" | jq -r '.tunnel_toml // .backpack_toml // empty')
  TUNNEL_MODE=$(echo "$cfg" | jq -r '.tunnel_mode // "direct_l3"')
  CONTROL_PORT=$(echo "$cfg" | jq -r '.control_port // empty')
  IRAN_PUBLIC_IP=$(echo "$cfg" | jq -r '.iran_public_ip // empty')
  ABROAD_PUBLIC_IP=$(echo "$cfg" | jq -r '.abroad_public_ip // empty')
  PORT_FORWARDS=$(echo "$cfg" | jq -c '.port_forwards // []')

  if [ "$command" = "diagnose" ] || [ "$command" = "diagnose-fix" ] || [ "$command" = "fix" ]; then
    local diag_fix=0
    case "$command" in
      diagnose-fix|fix) diag_fix=1 ;;
    esac
    if [ "$diag_fix" = 1 ]; then
      # Fix path: apply latest panel TOML (may include TCP Extreme upgrade).
      if [ -n "$toml" ] && [ "$toml" != "null" ]; then
        if [ "$hash" != "${CONFIG_HASH:-}" ]; then
          apply_tunnel_config "$toml"
          CONFIG_HASH="$hash"
        else
          open_iran_firewall || true
        fi
      fi
    elif [ -n "$toml" ] && [ "$toml" != "null" ] && [ "$hash" != "${CONFIG_HASH:-}" ]; then
      # Read-only diagnose: only apply pending Sync TOML, never open firewall / MSS locally.
      apply_tunnel_config "$toml"
      CONFIG_HASH="$hash"
    fi
    write_env
    handle_diagnose_command "$diag_fix" || true
    return 0
  fi

  case "$command" in
    path-ping|path-ping:*|pp|pp:*)
      write_env
      handle_path_ping_command "$command" || true
      return 0
      ;;
  esac

  if [ "$hash" != "${CONFIG_HASH:-}" ] || [ "$command" = "start" ] || [ "$command" = "restart" ]; then
    # Keep env on disk before unit restart so a concurrent ping purge cannot
    # treat this pulse as an orphan while Sync is mid-apply.
    CONFIG_HASH="$hash"
    write_env
    apply_tunnel_config "$toml"
    api POST "/api/hpx_pulse/agent/ack" \
      "$(jq -nc --arg c "${command:-start}" '{command:$c, status:"running", message:"HPX config applied"}')" >/dev/null || true
  else
    open_iran_firewall
    check_abroad_backends
    write_env
  fi
  send_heartbeat
}

# TCP connect with class: ok | refused | timeout | error  (abroad→Iran path).
probe_tcp_connect_json() {
  local host="$1" port="$2" label="${3:-tcp}"
  [ -n "$host" ] && [ -n "$port" ] || return 1
  if ! has python3 && ! has python; then
    local ms
    ms="$(measure_tcp_ms "$host" "$port" || true)"
    if [ -n "$ms" ]; then
      jq -nc --argjson ms "$ms" --arg d "${label}: connect ok (${ms}ms)" \
        '{ok:true, state:"ok", blocked:false, class:"ok", ms:$ms, detail:$d}'
    else
      jq -nc --arg d "${label}: connect failed (no python for class)" \
        --arg f "Install python3; open Iran firewall TCP ${port}" \
        '{ok:false, state:"fail", blocked:true, class:"error", detail:$d, fix:$f}'
    fi
    return 0
  fi
  local py=python3
  has python3 || py=python
  "$py" -c "
import json, socket, time
host, port, label = '$host', int('$port'), '''$label'''
out = {'ok': False, 'state': 'fail', 'blocked': False, 'ms': None, 'class': 'error', 'detail': '', 'fix': ''}
s = socket.socket(); s.settimeout(4.0)
t = time.time()
try:
    s.connect((host, port))
    ms = round((time.time() - t) * 1000, 1)
    out.update(ok=True, state='ok', blocked=False, class='ok', ms=ms,
               detail='%s: connect ok (%.1fms)' % (label, ms))
except socket.timeout:
    out.update(blocked=True, class='timeout',
               detail='%s: TCP SYN timeout %s:%s — DC/provider drops TCP (not MSS stall)' % (label, host, port),
               fix='Compare working Iran IP from abroad (nc -vz IP %s). On broken Iran: ufw allow %s/tcp + provider firewall' % (port, port))
except ConnectionRefusedError:
    out.update(class='refused',
               detail='%s: TCP refused %s:%s — reachable but nothing listening' % (label, host, port),
               fix='On Iran: systemctl restart hpx-pulse-tunnel-*; ss -tlnp | grep :%s' % port)
except OSError as e:
    err = str(e).lower()
    blocked = ('timed out' in err) or ('unreachable' in err) or (getattr(e, 'errno', None) in (110, 101, 113))
    out.update(blocked=blocked, class='error',
               detail='%s: connect error: %s' % (label, e),
               fix='Open Iran TCP %s; if timeout only on this Iran IP → provider TCP filter — use the working Iran VPS' % port)
finally:
    s.close()
print(json.dumps(out))
" 2>/dev/null || echo '{"ok":false,"state":"fail","blocked":true,"class":"error","detail":"connect probe crashed","fix":""}'
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

# Connect + first-byte exchange — detects classic MSS/MTU stall (connect OK, data hangs).
probe_tcp_exchange_json() {
  local host="$1" port="$2"
  [ -n "$host" ] && [ -n "$port" ] || return 1
  if ! has python3 && ! has python; then
    echo '{"ok":false,"state":"warn","stall":false,"detail":"python missing — cannot run MSS exchange probe","fix":"install python3 on agent host"}'
    return 0
  fi
  local py=python3
  has python3 || py=python
  "$py" -c "
import json, socket, time, sys
host, port = sys.argv[1], int(sys.argv[2])
out = {'ok': False, 'state': 'fail', 'stall': False, 'ms': None, 'bytes': 0, 'detail': '', 'fix': ''}
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(4.0)
t0 = time.time()
try:
    s.connect((host, port))
    out['ms'] = round((time.time() - t0) * 1000, 1)
except Exception as e:
    out['detail'] = 'connect failed: %s' % e
    out['fix'] = 'Cannot TCP-connect to Iran:%s — firewall / wrong IP / tunnel down' % port
    print(json.dumps(out)); raise SystemExit
try:
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
except Exception:
    pass
# Minimal TLS ClientHello-ish bytes (works on 443); harmless noise on other ports.
payload = bytes([0x16, 0x03, 0x01, 0x00, 0x2e, 0x01, 0x00, 0x00, 0x2a, 0x03, 0x03]) + (b'\\x00' * 32) + bytes([0x00, 0x00, 0x02, 0x00, 0x2f, 0x01, 0x00])
try:
    s.sendall(payload)
except Exception as e:
    out.update(stall=True, detail='connect ok (%.1fms) but send failed: %s' % (out['ms'] or 0, e),
               fix='TCP write stall — Edit Pulse → Safe / MTU (mss=1200) → Save → Sync')
    print(json.dumps(out)); s.close(); raise SystemExit
s.settimeout(4.0)
try:
    data = s.recv(128)
    if data:
        out.update(ok=True, state='ok', bytes=len(data),
                   detail='connect+exchange ok (%.1fms, got %dB)' % (out['ms'] or 0, len(data)))
    else:
        # Empty recv = peer closed — usually abroad inbound missing, NOT MSS.
        out.update(stall=False, peer_closed=True,
                   detail='connect ok (%.1fms) then EOF on first read — abroad backend closed (often nothing on forward target)' % (out['ms'] or 0),
                   fix='Start Xray inbound on abroad matching port-forward target (e.g. 127.0.0.1:2082), or change Pulse forward to the port Xray actually listens')
except socket.timeout:
    out.update(stall=True,
               detail='stall_after_connect: TCP connected (%.1fms) but no bytes in 4s — classic MTU/MSS' % (out['ms'] or 0),
               fix='Edit Pulse → TCP Extreme (mss=1000) → Save → Sync both sides')
except Exception as e:
    out['detail'] = 'recv error after connect: %s' % e
finally:
    try: s.close()
    except Exception: pass
print(json.dumps(out))
" "$host" "$port" 2>/dev/null || echo '{"ok":false,"state":"fail","stall":false,"detail":"exchange probe crashed","fix":""}'
}

first_forward_backend() {
  # Prints host:port for first reverse forward target (default 127.0.0.1:<listen>).
  local raw entry target
  raw="${PORT_FORWARDS:-}"
  raw="${raw//[\[\]\"]/}"
  entry="${raw%%,*}"
  entry="${entry// /}"
  [ -n "$entry" ] || return 1
  if [[ "$entry" == *"="* ]]; then
    target="${entry#*=}"
  else
    target="127.0.0.1:${entry}"
  fi
  [[ "$target" == *:* ]] || target="127.0.0.1:${target}"
  echo "$target"
}

port_is_listening() {
  local port="$1"
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

toml_mss_value() {
  local cfg
  cfg="$(tunnel_cfg_path)"
  [ -f "$cfg" ] || return 1
  grep -E '^[[:space:]]*mss[[:space:]]*=' "$cfg" 2>/dev/null | head -1 | sed -E 's/.*=[[:space:]]*//' | tr -d '[:space:]'
}

toml_transport_value() {
  local cfg
  cfg="$(tunnel_cfg_path)"
  [ -f "$cfg" ] || return 1
  grep -E '^[[:space:]]*transport[[:space:]]*=' "$cfg" 2>/dev/null | head -1 | sed -E 's/.*=[[:space:]]*"?([^"]*)"?/\1/' | tr -d '[:space:]'
}

list_orphan_tunnel_units() {
  # Crash-loop leftovers only (missing toml). Intact peers / Sync races are not orphans.
  local u mine id toml
  mine="hpx-pulse-tunnel-${PULSE_ID:-0}.service"
  {
    systemctl list-units 'hpx-pulse-tunnel*.service' --no-legend --all --state=running,failed,activating 2>/dev/null \
      | awk '{print $1}'
    systemctl list-unit-files 'hpx-pulse-tunnel-*.service' --no-legend 2>/dev/null | awk '{print $1}'
  } | while read -r u; do
      [ -n "$u" ] || continue
      [ "$u" = "$mine" ] && continue
      id="$(_pulse_id_from_tunnel_unit "$u")"
      [ -n "$id" ] || continue
      toml="${ETC_DIR}/l3-pulse-${id}.toml"
      if [ ! -f "$toml" ]; then
        echo "$u"
      fi
    done | sort -u
}

count_local_pulse_envs() {
  find "$AGENTS_DIR" -maxdepth 1 -type f -name '*.env' 2>/dev/null | wc -l | tr -d ' '
}

auto_fix_on_diagnose() {
  local orphans o fixed=0 transport mss_now sibling_count
  log "diagnose auto-fix — pulse ${PULSE_ID:-?} side=${PULSE_SIDE:-?} mode=${TUNNEL_MODE:-?}"
  # Only wipe crash-loop leftovers of OTHER ids — never touch intact siblings.
  purge_stale_tunnel_units
  open_iran_firewall || true

  # TCP reverse: MSS only in THIS pulse's TOML. Do not set global tcp_base_mss —
  # that slows / breaks every other tunnel on the host.
  case "${TUNNEL_MODE:-}" in
    reverse_stealth|reverse_tcp|reverse_tcpmux|reverse_ws|reverse_wss|reverse_wssmux)
      if force_tcp_mss_toml 1000; then
        fixed=1
        log "forced mss=1000 in tunnel TOML (TCP Extreme local clamp)"
      fi
      if has sysctl; then
        sysctl -w net.ipv4.tcp_mtu_probing=1 >/dev/null 2>&1 || true
      fi
      ;;
  esac

  orphans="$(list_orphan_tunnel_units || true)"
  if [ -n "$orphans" ]; then
    while IFS= read -r o; do
      local oid=""
      [ -n "$o" ] || continue
      oid="$(_pulse_id_from_tunnel_unit "$o")"
      [ -n "$oid" ] || continue
      [ "$oid" = "${PULSE_ID:-}" ] && continue
      if [ ! -f "${ETC_DIR}/l3-pulse-${oid}.toml" ]; then
        log "removing crash-loop leftover tunnel $o"
        remove_tunnel_unit_fully "$oid"
        fixed=1
      fi
    done <<< "$orphans"
  fi
  if [ "${PURGE_NEED_RELOAD:-0}" = 1 ]; then
    systemctl daemon-reload 2>/dev/null || true
    PURGE_NEED_RELOAD=0
  fi
  if ! tunnel_service_active; then
    if [ -f "$(tunnel_cfg_path)" ]; then
      systemctl restart "$(tunnel_service_name).service" 2>/dev/null || true
      sleep 1
      fixed=1
    fi
  elif [ "$fixed" = 1 ]; then
    # Restart ONLY this pulse's unit after its own TOML/firewall change.
    systemctl restart "$(tunnel_service_name).service" 2>/dev/null || true
    sleep 1
  fi
  # Abroad backend nudge: NEVER restart shared Xray when multiple pulses share this host
  # (that drops every other tunnel's users).
  if [ "${PULSE_SIDE:-}" = "abroad" ]; then
    sibling_count="$(count_local_pulse_envs)"
    local be_port
    be_port="$(first_forward_listen_port || true)"
    if [ -n "$be_port" ] && ! port_is_listening "$be_port"; then
      if [ "${sibling_count:-0}" -gt 1 ]; then
        warn "backend :${be_port} down — NOT restarting Xray ( ${sibling_count} pulses on host; would disrupt siblings )"
      else
        for svc in xray xray.service x-ui x-ui.service sing-box; do
          if systemctl list-unit-files "$svc" >/dev/null 2>&1 || systemctl status "$svc" >/dev/null 2>&1; then
            log "backend :${be_port} down — restarting $svc (single-pulse host)"
            systemctl restart "$svc" 2>/dev/null || true
            sleep 1
            fixed=1
            break
          fi
        done
      fi
    fi
  fi
  [ "$fixed" = 1 ]
}

force_tcp_mss_toml() {
  # Ensure mss = N in reverse [server]/[client] TOML (TCP/Stealth path).
  local want="$1" cfg cur
  cfg="$(tunnel_cfg_path)"
  [ -f "$cfg" ] || return 1
  cur="$(toml_mss_value || true)"
  if [ -n "$cur" ] && [ "$cur" -le "$want" ] 2>/dev/null; then
    return 1
  fi
  if grep -qE '^[[:space:]]*mss[[:space:]]*=' "$cfg" 2>/dev/null; then
    sed -i -E "s/^([[:space:]]*mss[[:space:]]*=[[:space:]]*)[0-9]+/\\1${want}/" "$cfg" || return 1
  else
    # Insert after first transport= line (both sides have it).
    if grep -qE '^[[:space:]]*transport[[:space:]]*=' "$cfg" 2>/dev/null; then
      sed -i -E "/^[[:space:]]*transport[[:space:]]*=/a mss = ${want}" "$cfg" || return 1
    else
      printf '\nmss = %s\n' "$want" >>"$cfg" || return 1
    fi
  fi
  return 0
}

probe_tls_brief_json() {
  local host="$1" port="$2" label="$3"
  [ -n "$host" ] && [ -n "$port" ] || return 1
  if ! has openssl; then
    echo '{"ok":false,"state":"warn","detail":"openssl missing","fix":"install openssl for TLS probe"}'
    return 0
  fi
  local out rc=0
  out="$(timeout 6 openssl s_client -connect "${host}:${port}" -servername "${host}" -brief </dev/null 2>&1)" || rc=$?
  if echo "$out" | grep -qiE 'Protocol version|CONNECTION ESTABLISHED|Verify return code'; then
    jq -nc --arg d "${label}: TLS handshake got response" --arg snip "$(echo "$out" | head -3 | tr '\n' ' ' | cut -c1-160)" \
      '{ok:true, state:"ok", detail:($d+" · "+$snip)}'
  elif [ "$rc" = 124 ]; then
    jq -nc --arg d "${label}: TLS hang/timeout 6s after connect — stall or Reality/filter" \
      --arg f "If local OK but via-Iran hangs: tunnel payload path broken. Try TCP Pass/KCP or Safe/MTU. Check client uses Iran IP." \
      '{ok:false, state:"fail", stall:true, detail:$d, fix:$f}'
  else
    # Connection refused / reset still useful — means something answered at TCP layer.
    if echo "$out" | grep -qiE 'Connection refused|Connection reset|alert handshake'; then
      jq -nc --arg d "${label}: TCP up, TLS alert/refuse (often OK for Reality — core answered)" \
        --arg snip "$(echo "$out" | head -2 | tr '\n' ' ' | cut -c1-120)" \
        '{ok:true, state:"ok", detail:($d+" · "+$snip)}'
    else
      jq -nc --arg d "${label}: TLS probe failed rc=${rc}" --arg snip "$(echo "$out" | head -2 | tr '\n' ' ' | cut -c1-120)" \
        '{ok:false, state:"fail", detail:($d+" · "+$snip), fix:"Check Xray inbound + port forward target"}'
    fi
  fi
}

probe_xray_json() {
  local be_port="${1:-443}"
  local proc="false" detail listens tls_local="null"
  if pgrep -x xray >/dev/null 2>&1 || pgrep -af '[x]ray' >/dev/null 2>&1; then
    proc="true"
    detail="xray process running"
  elif pgrep -af '[s]ing-box' >/dev/null 2>&1; then
    proc="true"
    detail="sing-box process running"
  else
    detail="no xray/sing-box process found"
  fi
  listens="$(ss -tlnp 2>/dev/null | grep -E ':(443|8443|2053)\s' | head -8 | tr '\n' ';' | cut -c1-300)"
  if port_is_listening "$be_port"; then
    tls_local="$(probe_tls_brief_json 127.0.0.1 "$be_port" "local:${be_port}")"
  else
    tls_local=$(jq -nc --arg d "nothing listening on :${be_port}" --arg f "Start Xray inbound on 127.0.0.1:${be_port}" '{ok:false, state:"fail", detail:$d, fix:$f}')
  fi
  jq -nc \
    --argjson proc "$proc" \
    --arg d "$detail" \
    --arg L "${listens:-none}" \
    --argjson tls "$tls_local" \
    '{ok:$proc, detail:$d, listens:$L, tls_local:$tls, fix:(if $proc then "" else "Install/start Xray on abroad; inbound must match port forward" end)}'
}

build_diag_report_json() {
  local host eng mss_val mss_ok="true" mss_detail mss_fix=""
  local svc_ok="false" svc_detail ctl_json="null" be_json="null"
  local tcp_ctl="null" tcp_fwd="null" tcp_ex="null" tls_via="null" xray_json="null"
  local orphans_json transport_json mode_json
  local fwd_port be_target be_host be_port
  local verdict_level="info" verdict_summary="probe collected" verdict_fix=""
  local ts udp_detail udp_fix="" transport_val orphans orphan_ok="true" orphan_detail

  host="$(hostname -f 2>/dev/null || hostname)"
  eng="$("$ENGINE_BIN" --version 2>/dev/null | head -1 | tr -d '\r' || echo unknown)"
  ts="$(date +%s 2>/dev/null || echo 0)"
  mss_val="$(toml_mss_value || true)"
  if [ -z "$mss_val" ]; then
    mss_ok="false"
    mss_detail="mss not set in TOML (path may use full 1500 MTU segments)"
    mss_fix="Sync from panel — pick Safe / MTU profile (mss=1200) or set mss=1200 both sides"
  else
    mss_detail="mss=${mss_val}"
    if [ "$mss_val" -gt 1280 ] 2>/dev/null; then
      mss_ok="false"
      mss_fix="High MSS — Edit Pulse → Safe / MTU → Save → Sync"
    fi
  fi

  if tunnel_service_active; then
    svc_ok="true"
    svc_detail="active ($(tunnel_service_name))"
  else
    svc_detail="inactive ($(tunnel_service_name))"
  fi

  transport_val="$(toml_transport_value || echo unknown)"
  mode_json=$(jq -nc --arg m "${TUNNEL_MODE:-}" --arg t "$transport_val" --arg c "${PULSE_SIDE:-}" \
    '{ok:true, detail:("mode="+$m+" transport="+$t+" side="+$c)}')
  orphans="$(list_orphan_tunnel_units | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
  if [ -n "$orphans" ]; then
    orphan_ok="false"
    orphan_detail="orphan tunnels still running: ${orphans}"
  else
    orphan_detail="no orphan tunnel units"
  fi
  orphans_json=$(jq -nc --argjson ok "$orphan_ok" --arg d "$orphan_detail" --arg f "Diagnose auto-fix stops orphans; or: systemctl stop <unit>" '{ok:$ok, detail:$d, fix:$f}')
  transport_json=$(jq -nc --arg t "$transport_val" --arg m "${TUNNEL_MODE:-}" \
    '{ok:true, detail:("toml transport="+$t+" · pulse mode="+$m), fix:(if ($t=="stealth" or $t=="tcp" or $t=="wss") then "If Reality -1 with TCP stall: switch profile to TCP Pass/KCP" else "" end)}')

  if [ "${PULSE_SIDE:-}" = "iran" ] && [[ "${TUNNEL_MODE:-}" == reverse_* ]]; then
    if tunnel_port_listening; then
      case "${TUNNEL_MODE:-}" in
        reverse_kcp|reverse_quic|reverse_udp)
          ctl_json=$(jq -nc --arg d "UDP listening :${CONTROL_PORT} (OK for ${TUNNEL_MODE})" '{ok:true, detail:$d}')
          ;;
        *)
          ctl_json=$(jq -nc --arg d "TCP listening :${CONTROL_PORT}" '{ok:true, detail:$d}')
          ;;
      esac
    else
      ctl_json=$(jq -nc --arg d "control NOT listening :${CONTROL_PORT} mode=${TUNNEL_MODE}" --arg f "systemctl restart $(tunnel_service_name); open firewall (UDP for KCP/QUIC)" '{ok:false, detail:$d, fix:$f}')
    fi
  fi

  if [ "${PULSE_SIDE:-}" = "abroad" ] && [[ "${TUNNEL_MODE:-}" == reverse_* ]]; then
    be_target="$(first_forward_backend || true)"
    if [ -n "$be_target" ]; then
      be_host="${be_target%:*}"
      be_port="${be_target##*:}"
      if port_is_listening "$be_port"; then
        be_json=$(jq -nc --arg d "listening ${be_host}:${be_port}" '{ok:true, detail:$d}')
      else
        be_json=$(jq -nc --arg d "NOT listening ${be_host}:${be_port}" --arg f "Start Xray/inbound on abroad ${be_host}:${be_port}" '{ok:false, detail:$d, fix:$f}')
      fi
      xray_json="$(probe_xray_json "$be_port")"
    else
      xray_json="$(probe_xray_json 443)"
    fi

    # For UDP carriers, control port is UDP — skip misleading TCP control connect.
    case "${TUNNEL_MODE:-}" in
      reverse_kcp|reverse_quic|reverse_udp)
        # Without UDP to Iran:control, KCP never links — Iran:443 still accepts then stalls.
        if [ -n "${IRAN_PUBLIC_IP:-}" ] && [ -n "${CONTROL_PORT:-}" ] && { has python3 || has python; }; then
          local py=python3 uok
          has python3 || py=python
          uok="$($py -c "
import socket
s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(2.0)
try:
    s.sendto(b'hpx-diag', ('${IRAN_PUBLIC_IP}', int('${CONTROL_PORT}')))
    print('sent')
except Exception as e:
    print('fail:'+str(e))
finally:
    s.close()
" 2>/dev/null || echo fail)"
          if [[ "$uok" == sent* ]]; then
            tcp_ctl=$(jq -nc --arg d "UDP send to Iran:${CONTROL_PORT} ok (control for ${TUNNEL_MODE})" '{ok:true, state:"ok", detail:$d}')
          else
            tcp_ctl=$(jq -nc --arg d "UDP to Iran:${CONTROL_PORT} failed (${uok})" --arg f "Open Iran firewall UDP ${CONTROL_PORT} — without it KCP never links and Iran:443 stalls after connect" '{ok:false, state:"fail", detail:$d, fix:$f}')
          fi
        else
          tcp_ctl=$(jq -nc --arg d "control is UDP for ${TUNNEL_MODE} — ensure Iran allows UDP :${CONTROL_PORT:-?}" '{ok:true, state:"ok", detail:$d}')
        fi
        ;;
      *)
        if [ -n "${IRAN_PUBLIC_IP:-}" ] && [ -n "${CONTROL_PORT:-}" ]; then
          tcp_ctl="$(probe_tcp_connect_json "$IRAN_PUBLIC_IP" "$CONTROL_PORT" "control")"
        fi
        ;;
    esac

    fwd_port="$(first_forward_listen_port || true)"
    if [ -n "${IRAN_PUBLIC_IP:-}" ] && [ -n "$fwd_port" ]; then
      tcp_fwd="$(probe_tcp_connect_json "$IRAN_PUBLIC_IP" "$fwd_port" "forward")"
      if echo "$tcp_fwd" | jq -e '.ok == true' >/dev/null 2>&1; then
        tcp_ex="$(probe_tcp_exchange_json "$IRAN_PUBLIC_IP" "$fwd_port")"
        tls_via="$(probe_tls_brief_json "$IRAN_PUBLIC_IP" "$fwd_port" "via-Iran:${fwd_port}")"
      else
        tcp_ex=$(jq -nc --arg d "skipped — forward TCP blocked/refused" '{ok:false, state:"fail", stall:false, blocked:true, detail:$d}')
      fi
    fi
  fi

  udp_detail="Carrier=${transport_val}. User configs stay TCP on Iran forward; KCP/QUIC/UDP only change Iran↔abroad hop."
  udp_fix="Reality -1 + connect OK ⇒ check TLS via-Iran probe / client address must be Iran IP"

  # Verdict — backend down before MSS stall (EOF after connect ≠ MTU).
  if echo "${orphans_json:-}" | jq -e '.ok == false' >/dev/null 2>&1; then
    verdict_level="fail"
    verdict_summary="$(echo "$orphans_json" | jq -r '.detail')"
    verdict_fix="$(echo "$orphans_json" | jq -r '.fix // empty')"
  elif echo "${be_json:-}" | jq -e '.ok == false' >/dev/null 2>&1; then
    verdict_level="fail"
    verdict_summary="$(echo "$be_json" | jq -r '.detail')"
    verdict_fix="$(echo "$be_json" | jq -r '.fix // empty')"
  elif echo "${xray_json:-}" | jq -e '.tls_local.ok == false' >/dev/null 2>&1; then
    verdict_level="fail"
    verdict_summary="$(echo "$xray_json" | jq -r '.tls_local.detail // .detail')"
    verdict_fix="$(echo "$xray_json" | jq -r '.tls_local.fix // .fix // empty')"
  elif echo "${tcp_fwd:-}" | jq -e '.blocked == true' >/dev/null 2>&1; then
    verdict_level="fail"
    verdict_summary="$(echo "$tcp_fwd" | jq -r '.detail')"
    verdict_fix="$(echo "$tcp_fwd" | jq -r '.fix // empty')"
  elif echo "${tcp_ctl:-}" | jq -e '.blocked == true' >/dev/null 2>&1; then
    verdict_level="fail"
    verdict_summary="$(echo "$tcp_ctl" | jq -r '.detail')"
    verdict_fix="$(echo "$tcp_ctl" | jq -r '.fix // empty')"
  elif echo "${tls_via:-}" | jq -e '.stall == true' >/dev/null 2>&1; then
    verdict_level="fail"
    verdict_summary="$(echo "$tls_via" | jq -r '.detail')"
    verdict_fix="$(echo "$tls_via" | jq -r '.fix // empty')"
  elif echo "${tcp_ex:-}" | jq -e '.stall == true' >/dev/null 2>&1; then
    verdict_level="fail"
    verdict_summary="$(echo "$tcp_ex" | jq -r '.detail')"
    verdict_fix="$(echo "$tcp_ex" | jq -r '.fix // empty')"
  elif echo "${tcp_fwd:-}" | jq -e '.ok == false' >/dev/null 2>&1; then
    verdict_level="fail"
    verdict_summary="$(echo "$tcp_fwd" | jq -r '.detail')"
    verdict_fix="$(echo "$tcp_fwd" | jq -r '.fix // empty')"
  elif echo "${tcp_ctl:-}" | jq -e '.ok == false' >/dev/null 2>&1; then
    verdict_level="fail"
    verdict_summary="$(echo "$tcp_ctl" | jq -r '.detail')"
    verdict_fix="$(echo "$tcp_ctl" | jq -r '.fix // empty')"
  elif echo "${xray_json:-}" | jq -e '.ok == false' >/dev/null 2>&1; then
    verdict_level="fail"
    verdict_summary="$(echo "$xray_json" | jq -r '.detail')"
    verdict_fix="$(echo "$xray_json" | jq -r '.fix // empty')"
  elif echo "${tcp_ex:-}" | jq -e '.ok == true' >/dev/null 2>&1; then
    verdict_level="ok"
    verdict_summary="Path OK (connect + exchange). If Reality still -1: client must use Iran IP/domain, not abroad."
    verdict_fix="Confirm subscription host = Iran public IP; SNI/Reality dest unchanged"
  elif [ "${PULSE_SIDE:-}" = "iran" ]; then
    if echo "${ctl_json:-}" | jq -e '.ok == true' >/dev/null 2>&1; then
      verdict_level="ok"
      verdict_summary="Iran control listening — wait for abroad path/Xray probe"
    else
      verdict_level="fail"
      verdict_summary="$(echo "${ctl_json:-null}" | jq -r '.detail // "Iran local checks failed"')"
      verdict_fix="$(echo "${ctl_json:-null}" | jq -r '.fix // empty')"
    fi
  fi

  jq -nc \
    --arg side "${PULSE_SIDE:-unknown}" \
    --arg host "$host" \
    --arg eng "$eng" \
    --argjson ts "${ts:-0}" \
    --argjson svc "$(jq -nc --argjson ok "$svc_ok" --arg d "$svc_detail" '{ok:$ok, detail:$d}')" \
    --argjson ctl "$ctl_json" \
    --argjson be "$be_json" \
    --argjson mss "$(jq -nc --argjson ok "$mss_ok" --arg d "$mss_detail" --arg f "$mss_fix" '{ok:$ok, detail:$d, fix:$f}')" \
    --argjson tctl "$tcp_ctl" \
    --argjson tfwd "$tcp_fwd" \
    --argjson tex "$tcp_ex" \
    --argjson tls "$tls_via" \
    --argjson xr "$xray_json" \
    --argjson orp "$orphans_json" \
    --argjson trn "$transport_json" \
    --argjson md "$mode_json" \
    --arg ud "$udp_detail" \
    --arg uf "$udp_fix" \
    --arg vl "$verdict_level" \
    --arg vs "$verdict_summary" \
    --arg vf "$verdict_fix" \
    '{
      side:$side, host:$host, engine_version:$eng, ts:$ts,
      tunnel_service:$svc,
      mode:$md,
      transport:$trn,
      orphan_tunnels:$orp,
      control_listen:(if $ctl == null then null else $ctl end),
      backend_listen:(if $be == null then null else $be end),
      xray:(if $xr == null then null else $xr end),
      mss:$mss,
      tcp:{
        control:(if $tctl == null then null else $tctl end),
        forward:(if $tfwd == null then null else $tfwd end),
        forward_exchange:(if $tex == null then null else $tex end),
        tls_via_iran:(if $tls == null then null else $tls end)
      },
      udp:{detail:$ud, fix:$uf},
      verdict:{level:$vl, summary:$vs, fix:$vf}
    }'
}

post_deep_diag_heartbeat() {
  local diag lat_json="null" fwd_json="null" msg="HPX deep diagnose" running="false" link="false" hb_ok=0
  tunnel_service_active && running="true"
  tunnel_link_up && link="true"
  diag="$(build_diag_report_json)" || diag="{}"
  if echo "$diag" | jq -e '.tcp.forward_exchange.stall == true or .tcp.tls_via_iran.stall == true' >/dev/null 2>&1; then
    fwd_json="false"
    msg="$(echo "$diag" | jq -r '.verdict.summary // "TLS/TCP stall after connect"')"
  elif echo "$diag" | jq -e '.tcp.forward.ok == true' >/dev/null 2>&1; then
    fwd_json="true"
    lat_json="$(echo "$diag" | jq -r '.tcp.forward.ms // empty')"
    [ -n "$lat_json" ] || lat_json="null"
    msg="$(echo "$diag" | jq -r '.verdict.summary // "user path OK"')"
  elif echo "$diag" | jq -e '.tcp.control.ok == true' >/dev/null 2>&1; then
    fwd_json="false"
    lat_json="$(echo "$diag" | jq -r '.tcp.control.ms // empty')"
    [ -n "$lat_json" ] || lat_json="null"
    msg="$(echo "$diag" | jq -r '.verdict.summary // "control OK, forward down"')"
  elif echo "$diag" | jq -e '.verdict.summary != null' >/dev/null 2>&1; then
    msg="$(echo "$diag" | jq -r '.verdict.summary')"
  fi
  [ "$lat_json" = "null" ] || [ -n "$lat_json" ] || lat_json="null"

  api_request POST "/api/hpx_pulse/agent/heartbeat" \
    "$(jq -nc \
      --arg s "running" \
      --arg h "$(hostname -f 2>/dev/null || hostname)" \
      --arg m "$msg" \
      --argjson tr "$running" \
      --argjson iu "$link" \
      --argjson lm "$lat_json" \
      --argjson fo "$fwd_json" \
      --argjson d "$diag" \
      '{status:$s, host:$h, tunnel_running:$tr, iface_up:$iu, latency_ms:($lm|tonumber? // null), forward_ok:$fo, message:$m, diag:$d}')" \
    >/dev/null && hb_ok=1
  [ "$hb_ok" = 1 ]
}

handle_diagnose_command() {
  local with_fix="${1:-0}"
  if [ "$with_fix" = 1 ]; then
    log "panel diagnose-fix — auto-fix + deep probes (pulse ${PULSE_ID:-?})"
    auto_fix_on_diagnose || true
  else
    log "panel diagnose — read-only deep probes (pulse ${PULSE_ID:-?})"
  fi
  if post_deep_diag_heartbeat; then
    local ack_cmd="diagnose"
    local ack_msg="HPX deep diagnose posted (read-only)"
    if [ "$with_fix" = 1 ]; then
      ack_cmd="diagnose-fix"
      ack_msg="HPX deep diagnose + autofix posted"
    fi
    api POST "/api/hpx_pulse/agent/ack" \
      "$(jq -nc --arg c "$ack_cmd" --arg m "$ack_msg" '{command:$c, status:"running", message:$m}')" >/dev/null || true
    log "diagnose report posted to panel"
  else
    warn "diagnose heartbeat failed (HTTP ${API_LAST_HTTP_CODE:-?})"
    return 1
  fi
}

# Panel queues: pp:t:4:c | pp:u:8:f  (also legacy path-ping:tcp:4:control)
run_path_ping_samples() {
  local proto="$1" count="$2" target_kind="$3"
  local host="${IRAN_PUBLIC_IP:-}" port="" i ms status detail replies_json="[]" ok_n=0
  [ -n "$host" ] || { echo '{"status":"error","detail":"iran_public_ip missing"}'; return 1; }

  if [ "$target_kind" = "forward" ]; then
    port="$(first_forward_listen_port || true)"
    [ -n "$port" ] || port=443
  else
    port="${CONTROL_PORT:-}"
  fi
  [ -n "$port" ] || { echo '{"status":"error","detail":"no port"}'; return 1; }

  if ! has python3 && ! has python; then
    echo '{"status":"error","detail":"python missing"}'
    return 1
  fi
  local py=python3
  has python3 || py=python

  for i in $(seq 1 "$count"); do
    if [ "$proto" = "udp" ]; then
      ms="$($py -c "
import socket, time
s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(2.0)
t=time.time()
try:
    s.sendto(b'hpx-path-ping', ('$host', int('$port')))
    # UDP often no reply — RTT = send success latency (path open enough to emit)
    print('%.1f' % ((time.time()-t)*1000))
except Exception:
    pass
finally:
    s.close()
" 2>/dev/null || true)"
      if [ -n "$ms" ]; then
        status=ok; detail="udp send ok"; ok_n=$((ok_n + 1))
      else
        status=timeout; ms=""; detail="udp send failed"
      fi
    else
      ms="$(measure_tcp_ms "$host" "$port" || true)"
      if [ -n "$ms" ]; then
        status=ok; detail="tcp connect ok"; ok_n=$((ok_n + 1))
      else
        status=timeout; ms=""; detail="tcp connect timeout/fail"
      fi
    fi
    if [ -n "$ms" ]; then
      replies_json="$(echo "$replies_json" | jq -c --argjson seq "$i" --arg st "$status" --argjson ms "$ms" --arg d "$detail" \
        '. + [{seq:$seq, status:$st, time_ms:$ms, detail:$d}]')"
    else
      replies_json="$(echo "$replies_json" | jq -c --argjson seq "$i" --arg st "$status" --arg d "$detail" \
        '. + [{seq:$seq, status:$st, time_ms:null, detail:$d}]')"
    fi
    sleep 0.25
  done

  local times min_ms max_ms avg_ms loss
  times="$(echo "$replies_json" | jq '[.[] | select(.time_ms != null) | .time_ms]')"
  min_ms="$(echo "$times" | jq 'if length>0 then min else null end')"
  max_ms="$(echo "$times" | jq 'if length>0 then max else null end')"
  avg_ms="$(echo "$times" | jq 'if length>0 then (add/length) else null end')"
  loss="$(echo "$replies_json" | jq --argjson n "$count" --argjson ok "$ok_n" 'if $n>0 then (100*($n-$ok)/$n) else 100 end')"

  jq -nc \
    --arg proto "$proto" \
    --argjson count "$count" \
    --arg target "$target_kind" \
    --argjson port "$port" \
    --arg host "$host" \
    --arg side "${PULSE_SIDE:-abroad}" \
    --argjson replies "$replies_json" \
    --argjson min "$min_ms" \
    --argjson max "$max_ms" \
    --argjson avg "$avg_ms" \
    --argjson loss "$loss" \
    --argjson ok "$ok_n" \
    --argjson ts "$(date +%s)" \
    '{
      status:"done", proto:$proto, count:$count, target:$target, port:$port,
      from:$side, to:$host, replies:$replies,
      min_ms:$min, max_ms:$max, avg_ms:$avg, loss_pct:$loss,
      packets_received:$ok, ts:$ts
    }'
}

handle_path_ping_command() {
  local raw="${1:-pp:t:4:c}"
  local proto=tcp count=4 target=control
  # Formats:
  #   pp:t:4:c | pp:u:8:f
  #   path-ping:tcp:4:control | path-ping:udp:8:forward
  #   path-ping | pp  (defaults)
  if [[ "$raw" == pp:* ]]; then
    IFS=':' read -r _ proto count target <<< "${raw}"
    case "$proto" in
      t|tcp) proto=tcp ;;
      u|udp) proto=udp ;;
      *) proto=tcp ;;
    esac
    case "$target" in
      c|control) target=control ;;
      f|forward) target=forward ;;
      *) target=control ;;
    esac
  elif [[ "$raw" == path-ping:* ]]; then
    IFS=':' read -r _ proto count target <<< "${raw}"
    proto="${proto:-tcp}"
    count="${count:-4}"
    target="${target:-control}"
  else
    proto=tcp
    count=4
    target=control
  fi
  [[ "$count" =~ ^[0-9]+$ ]] || count=4
  [ "$count" -ge 1 ] || count=1
  [ "$count" -le 20 ] || count=20
  case "$proto" in tcp|udp) ;; *) proto=tcp ;; esac
  case "$target" in control|forward) ;; *) target=control ;; esac

  log "path-ping ${proto} ×${count} → Iran ${target} (pulse ${PULSE_ID:-?})"
  local result diag avg_raw lat_json="null" msg
  result="$(run_path_ping_samples "$proto" "$count" "$target")" || result='{"status":"error","replies":[]}'
  avg_raw="$(echo "$result" | jq -r '.avg_ms // empty')"
  [ -n "$avg_raw" ] && [ "$avg_raw" != "null" ] && lat_json="$avg_raw"
  msg="$(echo "$result" | jq -r '"path-ping "+(.proto//"?")+" avg="+((.avg_ms|tostring)//"?")+"ms loss="+((.loss_pct|tostring)//"?")+"%"')"
  diag="$(jq -nc --argjson pp "$result" --arg side "${PULSE_SIDE:-abroad}" --argjson ts "$(date +%s)" \
    '{path_ping:$pp, side:$side, ts:$ts}')"

  api_request POST "/api/hpx_pulse/agent/heartbeat" \
    "$(jq -nc \
      --arg s "running" \
      --arg h "$(hostname -f 2>/dev/null || hostname)" \
      --arg m "$msg" \
      --argjson d "$diag" \
      --argjson lm "$lat_json" \
      '{status:$s, host:$h, tunnel_running:true, iface_up:true, latency_ms:(if $lm==null then null else ($lm|tonumber) end), message:$m, diag:$d}')" \
    >/dev/null || warn "path-ping heartbeat failed"

  api POST "/api/hpx_pulse/agent/ack" \
    "$(jq -nc --arg c "$raw" '{command:$c, status:"running", message:"path-ping posted"}')" >/dev/null || true
}

maybe_handle_diagnose_command() {
  local cfg command hash toml
  cfg=$(api_request GET "/api/hpx_pulse/agent/config") || return 0
  command=$(echo "$cfg" | jq -r '.agent_command // empty')
  case "$command" in
    diagnose|diagnose-fix|fix)
      hash=$(echo "$cfg" | jq -r '.config_hash // empty')
      toml=$(echo "$cfg" | jq -r '.tunnel_toml // .backpack_toml // empty')
      TUNNEL_MODE=$(echo "$cfg" | jq -r '.tunnel_mode // "direct_l3"')
      CONTROL_PORT=$(echo "$cfg" | jq -r '.control_port // empty')
      IRAN_PUBLIC_IP=$(echo "$cfg" | jq -r '.iran_public_ip // empty')
      ABROAD_PUBLIC_IP=$(echo "$cfg" | jq -r '.abroad_public_ip // empty')
      PORT_FORWARDS=$(echo "$cfg" | jq -c '.port_forwards // []')
      local diag_fix=0
      case "$command" in
        diagnose-fix|fix) diag_fix=1 ;;
      esac
      if [ "$diag_fix" = 1 ]; then
        if [ -n "$toml" ] && [ "$toml" != "null" ]; then
          if [ "$hash" != "${CONFIG_HASH:-}" ]; then
            apply_tunnel_config "$toml"
            CONFIG_HASH="$hash"
            write_env
          else
            open_iran_firewall || true
          fi
        fi
      elif [ -n "$toml" ] && [ "$toml" != "null" ] && [ "$hash" != "${CONFIG_HASH:-}" ]; then
        apply_tunnel_config "$toml"
        CONFIG_HASH="$hash"
        write_env
      fi
      handle_diagnose_command "$diag_fix"
      ;;
    path-ping|path-ping:*|pp|pp:*)
      TUNNEL_MODE=$(echo "$cfg" | jq -r '.tunnel_mode // "direct_l3"')
      CONTROL_PORT=$(echo "$cfg" | jq -r '.control_port // empty')
      IRAN_PUBLIC_IP=$(echo "$cfg" | jq -r '.iran_public_ip // empty')
      ABROAD_PUBLIC_IP=$(echo "$cfg" | jq -r '.abroad_public_ip // empty')
      PORT_FORWARDS=$(echo "$cfg" | jq -c '.port_forwards // []')
      handle_path_ping_command "$command"
      ;;
    *) return 0 ;;
  esac
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
    api_request POST "/api/hpx_pulse/agent/heartbeat" \
      "$(jq -nc \
        --arg s "running" \
        --arg h "$(hostname -f 2>/dev/null || hostname)" \
        --argjson tr "$running" \
        --argjson iu "$link" \
        '{status:$s, host:$h, tunnel_running:$tr, iface_up:$iu}')" \
      >/dev/null && hb_ok=1
  else
    api_request POST "/api/hpx_pulse/agent/heartbeat" \
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
  if [ "$hb_ok" != 1 ]; then
    if panel_registration_revoked; then
      cleanup_revoked_pulse "${PULSE_ID:-}"
      # Never pretend success after 401 — join used to print "connected" while tunnel was wiped.
      return 1
    fi
    warn "heartbeat to panel failed (HTTP ${API_LAST_HTTP_CODE:-?}) — keeping tunnel; try: hpx-pulse-agent set-panel-url https://domain (no :8000)"
  else
    _reset_revoke_streak "${PULSE_ID:-}"
    # Fast path: Diagnose UI queues "diagnose" — pick up on 5s ping, not only 30s sync.
    maybe_handle_diagnose_command || true
  fi
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
      --insecure|-k) CURL_INSECURE_ARGS=(-k); export HPX_INSECURE=1; shift ;;
      -*) die "unknown flag $1" ;;
      *) token="$1"; shift ;;
    esac
  done
  [ -n "$token" ] && [ -n "$panel_url" ] && [ -n "$side" ] || die "usage: join TOKEN --panel-url URL --side iran|abroad [--insecure]"
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
  [ "${#CURL_INSECURE_ARGS[@]}" -gt 0 ] && warn "TLS verify disabled (-k / HPX_INSECURE=1)"

  ensure_deps
  local host body claim
  host="$(hostname -f 2>/dev/null || hostname)"
  body=$(jq -nc --arg t "$token" --arg h "$host" --arg s "$side" '{join_token:$t, host:$h, side:$s}')

  probe_panel_reachability "$PANEL_URL"

  log "claiming join token (${side})..."
  local claim_tmp http_code base claim="" last_codes="" detail=""
  claim_tmp="$(mktemp)"
  while IFS= read -r base; do
    [ -n "$base" ] || continue
    http_code=$(curl_panel_post "$claim_tmp" "$body" "${base}/api/hpx_pulse/agent/claim")
    read_curl_last_err
    if [ -n "${CURL_LAST_ERR:-}" ]; then
      last_codes="${last_codes}${last_codes:+; }${base}→${http_code}(${CURL_LAST_ERR})"
    else
      last_codes="${last_codes}${last_codes:+; }${base}→${http_code}"
    fi
    if [ "$http_code" = "200" ]; then
      claim="$(cat "$claim_tmp")"
      [ "$base" != "${PANEL_URL%/}" ] && log "panel claim OK at ${base} (using this for agent)"
      PANEL_URL="$base"
      break
    fi
    if [ "$http_code" = "401" ] || [ "$http_code" = "403" ]; then
      detail="HTTP ${http_code} = bad/expired/already-used token — regenerate Tokens in panel (do not reuse the same hpxpi_/hpxpa_)"
      break
    fi
    if [ "$http_code" = "000" ] && [ -z "$detail" ]; then
      detail="HTTP 000 = this VPS cannot open TCP/TLS to panel (firewall / blocked port / DNS / SNI filter). Iran: use panel IP + --insecure from Tokens"
    elif [ -z "$detail" ] && [ "$http_code" != "200" ]; then
      detail="HTTP ${http_code}"
    fi
  done < <(panel_api_bases)
  rm -f "$claim_tmp"
  if [ -z "$claim" ]; then
    die "claim failed (${last_codes:-no URL tried})${detail:+ — ${detail}}. Test: curl -v --connect-timeout 10 ${PANEL_URL}/api/system   Or put HTTPS on 443 and use --panel-url https://domain   Self-signed cert: add --insecure"
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
  # Fresh claim must not inherit a leftover revoke streak from a previous attempt on this pulse id.
  _reset_revoke_streak "$PULSE_ID"

  install_self
  write_env
  prune_orphan_configs
  # Only wipe *other* pulses on revoke — never the one we just claimed mid-join.
  SKIP_REVOKE_FOR_PULSE="$PULSE_ID" verify_registrations_with_panel
  check_local_forward_conflicts
  ensure_engine
  apply_tunnel_config "$(echo "$claim" | jq -r '.tunnel_toml // .backpack_toml // empty')"
  write_env
  install_agent_systemd
  _reset_revoke_streak "$PULSE_ID"

  api POST "/api/hpx_pulse/agent/ack" \
    "$(jq -nc '{command:"start", status:"running", message:"HPX Pulse joined"}')" >/dev/null || true
  if send_heartbeat; then
    write_env
    log "ready on ${side} — pulse_id=${PULSE_ID} · forwards=${PORT_FORWARDS:-[]} (panel shows agent connected)"
  else
    write_env
    if [ -f "${AGENTS_DIR}/${PULSE_ID}.env" ]; then
      warn "tunnel is running locally but panel heartbeat failed at ${PANEL_URL}"
      warn "from Iran, port :8000 is often blocked — try:"
      warn "  sudo hpx-pulse-agent set-panel-url https://YOUR_DOMAIN"
      warn "  (no :8000 if nginx serves panel on 443) then: sudo hpx-pulse-agent sync"
      log "ready on ${side} — pulse_id=${PULSE_ID} · forwards=${PORT_FORWARDS:-[]} (fix PANEL_URL so panel shows connected)"
    else
      warn "join claimed pulse ${PULSE_ID} but local tunnel was removed after auth errors — regenerate Tokens and re-join"
      return 1
    fi
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
  # Pull latest agent script once so firewall/ping/diagnose fixes apply without re-join.
  # Prefer panel-hosted copy (matches this panel version), then GitHub.
  if { [ -n "${PANEL_URL:-}" ] \
      && hp_curl "${PANEL_URL%/}/api/hpx_pulse/agent/hpx-pulse-agent.sh" \
        -o "$INSTALL_DIR/hpx-pulse-agent.sh.new" 2>/dev/null; } \
    || hp_curl "https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-pulse-agent.sh" \
      -o "$INSTALL_DIR/hpx-pulse-agent.sh.new" 2>/dev/null; then
    if [ -s "$INSTALL_DIR/hpx-pulse-agent.sh.new" ] \
      && ! cmp -s "$INSTALL_DIR/hpx-pulse-agent.sh.new" "$INSTALL_DIR/hpx-pulse-agent.sh" 2>/dev/null; then
      mv "$INSTALL_DIR/hpx-pulse-agent.sh.new" "$INSTALL_DIR/hpx-pulse-agent.sh"
      chmod 755 "$INSTALL_DIR/hpx-pulse-agent.sh"
      ln -sfn "$INSTALL_DIR/hpx-pulse-agent.sh" "$BIN_LINK"
      log "agent updated — re-exec sync"
      exec "$BIN_LINK" sync
    fi
    rm -f "$INSTALL_DIR/hpx-pulse-agent.sh.new"
  fi
  ensure_engine
  load_env 2>/dev/null || true
  migrate_legacy_agent_registration
  prune_orphan_configs
  verify_registrations_with_panel
  for_each_pulse_env sync_pulse_from_panel
  # Batch one reload after leave/purge during sync — never mid-loop (sibling stalls).
  if [ "${PURGE_NEED_RELOAD:-0}" = 1 ]; then
    systemctl daemon-reload 2>/dev/null || true
    PURGE_NEED_RELOAD=0
  fi
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

cmd_leave() {
  need_root
  ensure_deps
  local pid="${1:-}" env_file
  # Legacy single-file registration (pre multi-agent) still shown by status.
  clear_legacy_agent_env() {
    if [ ! -d "$AGENTS_DIR" ] || ! compgen -G "$AGENTS_DIR/*.env" >/dev/null; then
      if [ -f "$ENV_FILE" ]; then
        rm -f "$ENV_FILE"
        log "cleared legacy ${ENV_FILE}"
      fi
    fi
  }
  if [ -n "$pid" ]; then
    log "removing local pulse ${pid} only (other pulses on this host stay up)..."
    remove_pulse_local_state "$pid"
    clear_legacy_agent_env
    if [ "${PURGE_NEED_RELOAD:-0}" = 1 ]; then
      systemctl daemon-reload 2>/dev/null || true
      PURGE_NEED_RELOAD=0
    fi
    log "pulse ${pid} removed from this server"
    return
  fi
  if [ ! -d "$AGENTS_DIR" ] || ! compgen -G "$AGENTS_DIR/*.env" >/dev/null; then
    if [ -f "$ENV_FILE" ]; then
      pid="$(grep -E '^[[:space:]]*PULSE_ID=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '[:space:]"')"
      [ -n "$pid" ] && [ "$pid" != "0" ] && remove_pulse_local_state "$pid"
      rm -f "$ENV_FILE"
      log "cleared legacy ${ENV_FILE}"
      if [ "${PURGE_NEED_RELOAD:-0}" = 1 ]; then
        systemctl daemon-reload 2>/dev/null || true
        PURGE_NEED_RELOAD=0
      fi
      return
    fi
    log "no local pulse registrations under ${AGENTS_DIR}"
    return
  fi
  for env_file in "$AGENTS_DIR"/*.env; do
    [ -f "$env_file" ] || continue
    pid="$(basename "$env_file" .env)"
    log "removing local pulse ${pid}..."
    remove_pulse_local_state "$pid"
  done
  clear_legacy_agent_env
  if [ "${PURGE_NEED_RELOAD:-0}" = 1 ]; then
    systemctl daemon-reload 2>/dev/null || true
    PURGE_NEED_RELOAD=0
  fi
  log "all local pulse registrations removed"
}

usage() {
  cat <<EOF
HPX Pulse Agent
  join TOKEN --panel-url URL --side iran|abroad
  leave [PULSE_ID]        remove stopped/deleted pulse from this server (frees ports)
  set-panel-url URL       when :8000 is blocked from Iran, use https://domain (443)
  install-engine [--force]  install hpx-tunnel-engine (GitHub-first on Iran)
  uninstall-engine        remove engine binary (for reinstall tests)
  sync | ping | status
  tcp-check IP [ports...] compare TCP reachability (run on abroad vs two Iran IPs)

Engine manual install (if join hangs on panel mirror):
  curl --http1.1 -fsSL .../hpx-tunnel-engine-install.sh | sudo env HPX_PREFER_GITHUB=1 bash
  sudo hpx-pulse-agent sync

Engine reinstall test:
  sudo hpx-pulse-agent uninstall-engine
  sudo hpx-pulse-agent install-engine --force
  # or one-liner:
  HPX_ENGINE_FORCE=1 curl .../hpx-tunnel-engine-install.sh | sudo env HPX_PREFER_GITHUB=1 bash

Compare why TCP dies on one Iran VPS (from abroad):
  sudo hpx-pulse-agent tcp-check 93.113.230.164 443 26912
  sudo hpx-pulse-agent tcp-check OTHER_IRAN_IP 443 26912
EOF
}

cmd_tcp_check() {
  local ip="${1:-}"
  shift || true
  [ -n "$ip" ] || die "usage: tcp-check IP [port ...]"
  local ports=("$@")
  if [ "${#ports[@]}" -eq 0 ]; then
    ports=(443 80 2053 8443)
  fi
  echo "TCP path check → ${ip} (from $(hostname -f 2>/dev/null || hostname))"
  local p j
  for p in "${ports[@]}"; do
    j="$(probe_tcp_connect_json "$ip" "$p" "check")"
    echo "$j" | jq -r --arg p "$p" '"  :\($p)  \(.class // "?")  \(.detail)"' 2>/dev/null \
      || echo "  :${p}  $(echo "$j" | head -c 200)"
  done
}

main() {
  local cmd="${1:-status}"
  shift || true
  case "$cmd" in
    join) cmd_join "$@" ;;
    leave) cmd_leave "$@" ;;
    set-panel-url) cmd_set_panel_url "$@" ;;
    install-engine) shift; cmd_install_engine "$@" ;;
    uninstall-engine) cmd_uninstall_engine ;;
    tcp-check) cmd_tcp_check "$@" ;;
    sync) cmd_sync ;;
    ping) cmd_ping ;;
    status) cmd_status ;;
    -h|--help|help) usage ;;
    *) die "unknown: $cmd" ;;
  esac
}

main "$@"

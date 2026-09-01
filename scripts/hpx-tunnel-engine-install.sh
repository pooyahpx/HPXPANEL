#!/usr/bin/env bash
# Installs the HPX tunnel engine binary as /usr/local/bin/hpx-tunnel-engine
set -euo pipefail

TARGET="/usr/local/bin/hpx-tunnel-engine"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="${SCRIPT_DIR}/hpx-tunnel-engine.version"
ENGINE_REPO="${HPX_TUNNEL_ENGINE_REPO:-pooyahpx/HPXPANEL}"
ENGINE_SOURCE=""
LOCAL_DIRS=(
  "${HPX_ENGINE_LOCAL_DIR:-}"
  "/opt/hpx-pulse/engine"
  "/etc/hpx-pulse/engine"
  "${SCRIPT_DIR}"
  "${SCRIPT_DIR}/release"
  "${SCRIPT_DIR}/dist"
)

# HTTP/1.1 avoids curl error 92 (PROTOCOL_ERROR) on some filtered routes.
CURL=(curl --http1.1 --connect-timeout 30 --max-time 300 --retry 3 --retry-delay 2 -fsSL)
# Panel mirror: fail fast so GitHub fallback kicks in when the panel port is blocked.
PANEL_CURL=(curl --http1.1 --connect-timeout 8 --max-time 25 --retry 0 -fsSL)

_hpx_ui_init() {
  HPX_UI_COLOR=0
  if [ -t 2 ] && [ -z "${NO_COLOR:-}" ]; then
    HPX_UI_COLOR=1
  fi
}

_hpx_c() {
  local code="$1"
  shift
  if [ "${HPX_UI_COLOR:-0}" = 1 ]; then
    printf '\033[%sm' "$code"
    printf '%s' "$*"
    printf '\033[0m'
  else
    printf '%s' "$*"
  fi
}

_hpx_out() { printf '%s\n' "$*" >&2; }

_hpx_banner() {
  local title="${1:-HPX TUNNEL ENGINE}" subtitle="${2:-installer}"
  _hpx_out ""
  _hpx_out "$(_hpx_c "36;1" "  ┌────────────────────────────────────────┐")"
  _hpx_out "$(_hpx_c "36;1" "  │")  $(_hpx_c "1" "$title")$(_hpx_c "36;1" "                         │")"
  _hpx_out "$(_hpx_c "36;1" "  │")  $(_hpx_c "2" "$subtitle")$(_hpx_c "36;1" "                              │")"
  _hpx_out "$(_hpx_c "36;1" "  └────────────────────────────────────────┘")"
  _hpx_out ""
}

_hpx_step() { _hpx_out "$(_hpx_c "36" "  ›") $*"; }
_hpx_dim() { _hpx_out "$(_hpx_c "2" "     $*")"; }
_hpx_ok() { _hpx_out "$(_hpx_c "32" "  ✓") $*"; }
_hpx_warn() { _hpx_out "$(_hpx_c "33" "  !") $*"; }
_hpx_err() { _hpx_out "$(_hpx_c "31" "  ✗") $*"; }

_hpx_success_full() {
  local ver="${1:-}"
  _hpx_out ""
  _hpx_out "$(_hpx_c "32;1" "  ╔════════════════════════════════════════╗")"
  _hpx_out "$(_hpx_c "32;1" "  ║")       $(_hpx_c "1" "✓  SUCCESS — FULL")$(_hpx_c "32;1" "                ║")"
  _hpx_out "$(_hpx_c "32;1" "  ╚════════════════════════════════════════╝")"
  if [ -n "$ver" ]; then
    _hpx_out "$(_hpx_c "32" "  Engine ready") · $(_hpx_c "1" "$TARGET") · v$ver"
  else
    _hpx_out "$(_hpx_c "32" "  Engine ready") · $(_hpx_c "1" "$TARGET")"
  fi
  _hpx_out ""
}

_hpx_fail_full() {
  local msg="${1:-Install failed}"
  _hpx_out ""
  _hpx_out "$(_hpx_c "31;1" "  ╔════════════════════════════════════════╗")"
  _hpx_out "$(_hpx_c "31;1" "  ║")       $(_hpx_c "1" "✗  INSTALL FAILED")$(_hpx_c "31;1" "               ║")"
  _hpx_out "$(_hpx_c "31;1" "  ╚════════════════════════════════════════╝")"
  _hpx_err "$msg"
  _hpx_out ""
}

_hpx_already_installed() {
  _hpx_banner
  _hpx_ok "Already installed · $TARGET"
  _hpx_dim "Reinstall test: sudo hpx-pulse-agent uninstall-engine"
  _hpx_dim "              then: sudo hpx-pulse-agent install-engine --force"
  _hpx_dim "Or: HPX_ENGINE_FORCE=1 curl .../hpx-tunnel-engine-install.sh | sudo bash"
  _hpx_out ""
}

_hpx_ui_init

if [ -x "$TARGET" ] && [ "${HPX_ENGINE_FORCE:-0}" != "1" ]; then
  _hpx_already_installed
  exit 0
fi

if [ "${HPX_ENGINE_FORCE:-0}" = "1" ] && [ -e "$TARGET" ]; then
  _hpx_banner "HPX TUNNEL ENGINE" "reinstall"
  _hpx_step "Removing previous binary..."
  rm -f "$TARGET"
  _hpx_ok "Cleared $TARGET"
else
  _hpx_banner
fi

engine_version="${HPX_TUNNEL_ENGINE_VERSION:-}"
if [ -z "$engine_version" ] && [ -f "$VERSION_FILE" ]; then
  engine_version="$(tr -d '[:space:]' <"$VERSION_FILE")"
fi
[ -n "$engine_version" ] || engine_version="1.7.5"
engine_version="${engine_version#v}"
release_tag="hpx-tunnel-engine-v${engine_version}"

arch="$(uname -m)"
case "$arch" in
  x86_64|amd64) asset="hpx-tunnel-engine_linux_amd64.tar.gz"; arch_key="amd64" ;;
  aarch64|arm64) asset="hpx-tunnel-engine_linux_arm64.tar.gz"; arch_key="arm64" ;;
  *)
    _hpx_fail_full "Unsupported architecture: $arch"
    exit 1
    ;;
esac

_hpx_step "Architecture · $arch_key"
_hpx_step "Release tag · $release_tag"
_hpx_out ""

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

verify_asset() {
  local file="$1" sums="$2"
  local expected actual

  [ -f "$sums" ] || return 0
  expected="$(grep -E "[[:space:]]\\*?${asset}\$" "$sums" 2>/dev/null | awk '{print $1}' | head -1)"
  [ -n "$expected" ] || return 0

  _hpx_step "Verifying SHA256 checksum..."
  if command -v sha256sum >/dev/null 2>&1; then
    actual="$(sha256sum "$file" | awk '{print $1}')"
  elif command -v shasum >/dev/null 2>&1; then
    actual="$(shasum -a 256 "$file" | awk '{print $1}')"
  else
    _hpx_warn "sha256sum not found — skipping verify"
    return 0
  fi

  if [ "$expected" != "$actual" ]; then
    _hpx_err "Checksum mismatch for ${asset}"
    return 1
  fi
  _hpx_ok "Checksum verified"
  return 0
}

try_local_asset() {
  local dir cand sums
  for dir in "${LOCAL_DIRS[@]}"; do
    [ -n "$dir" ] || continue
    for cand in "$dir/$asset" "$dir/release/$asset" "$dir/dist/$asset"; do
      [ -f "$cand" ] || continue
      ENGINE_SOURCE="local"
      _hpx_step "Using local archive"
      _hpx_dim "$cand"
      cp "$cand" "$work/engine.tgz"
      sums="$(dirname "$cand")/SHA256SUMS"
      verify_asset "$work/engine.tgz" "$sums" || return 1
      return 0
    done
  done
  return 1
}

try_panel_asset() {
  local base="" panel_url="${HPX_PANEL_URL:-}"
  if [ -n "$panel_url" ]; then
    base="${panel_url%/}/api/hpx_pulse/agent"
  elif [ -n "${HPX_AGENT_ASSETS_BASE:-}" ]; then
    base="${HPX_AGENT_ASSETS_BASE%/}"
  fi
  [ -n "$base" ] || return 1

  ENGINE_SOURCE="panel"
  _hpx_step "Downloading from panel mirror..."
  _hpx_dim "${base%/}/engine/${arch_key}"
  if ! "${PANEL_CURL[@]}" "${base%/}/engine/${arch_key}" -o "$work/engine.tgz"; then
    _hpx_warn "Panel mirror unreachable"
    return 1
  fi

  if "${PANEL_CURL[@]}" "${base%/}/engine/SHA256SUMS" -o "$work/SHA256SUMS" 2>/dev/null; then
    verify_asset "$work/engine.tgz" "$work/SHA256SUMS" || return 1
  fi
  _hpx_ok "Download complete (panel)"
  return 0
}

try_github_asset() {
  ENGINE_SOURCE="github"
  _hpx_step "Downloading from GitHub..."
  _hpx_dim "${ENGINE_REPO} · ${release_tag}"
  local direct_url release_url
  direct_url="https://github.com/${ENGINE_REPO}/releases/download/${release_tag}/${asset}"
  if "${CURL[@]}" "$direct_url" -o "$work/engine.tgz"; then
    if "${CURL[@]}" "https://github.com/${ENGINE_REPO}/releases/download/${release_tag}/SHA256SUMS" -o "$work/SHA256SUMS"; then
      verify_asset "$work/engine.tgz" "$work/SHA256SUMS" || return 1
    fi
    _hpx_ok "Download complete (GitHub)"
    return 0
  fi

  release_url="$("${CURL[@]}" "https://api.github.com/repos/${ENGINE_REPO}/releases/tags/${release_tag}" \
    | grep -o "https://[^\"]*${asset}" | head -1)" || true
  [ -n "$release_url" ] || return 1
  "${CURL[@]}" "$release_url" -o "$work/engine.tgz"
  _hpx_ok "Download complete (GitHub API)"
}

if try_local_asset; then
  :
elif [ "${HPX_PREFER_GITHUB:-0}" = "1" ] && try_github_asset; then
  :
elif try_panel_asset; then
  :
elif [ "${HPX_NO_GITHUB_FALLBACK:-0}" = "1" ]; then
  _hpx_fail_full "Panel mirror failed and GitHub fallback is disabled"
  _hpx_dim "Run: sudo hpxpanel update  OR  copy ${asset} to /opt/hpx-pulse/engine/"
  exit 1
elif try_github_asset; then
  :
else
  _hpx_fail_full "Could not download ${asset} (${release_tag})"
  _hpx_dim "If GitHub is blocked: place archive + SHA256SUMS in /opt/hpx-pulse/engine/"
  exit 1
fi

_hpx_step "Extracting archive..."
tar -xzf "$work/engine.tgz" -C "$work"

bin="$(find "$work" -maxdepth 2 -type f -name hpx-tunnel-engine -perm -111 | head -1)"
if [ -z "$bin" ]; then
  bin="$(find "$work" -maxdepth 2 -type f -name backpack -perm -111 | head -1)"
fi
if [ -z "$bin" ]; then
  bin="$(find "$work" -maxdepth 2 -type f -perm -111 | head -1)"
fi
[ -n "$bin" ] || { _hpx_fail_full "Binary not found inside archive"; exit 1; }

_hpx_step "Installing to $TARGET ..."
install -m 755 "$bin" "$TARGET"
_hpx_ok "Installed · source: ${ENGINE_SOURCE:-unknown}"

_hpx_success_full "$engine_version"

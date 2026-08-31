#!/usr/bin/env bash
# Installs the HPX tunnel engine binary as /usr/local/bin/hpx-tunnel-engine
set -euo pipefail

TARGET="/usr/local/bin/hpx-tunnel-engine"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="${SCRIPT_DIR}/hpx-tunnel-engine.version"
ENGINE_REPO="${HPX_TUNNEL_ENGINE_REPO:-pooyahpx/HPXPANEL}"
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

if [ -x "$TARGET" ]; then
  exit 0
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
  *) echo "unsupported architecture: $arch" >&2; exit 1 ;;
esac

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

verify_asset() {
  local file="$1" sums="$2"
  local expected actual

  [ -f "$sums" ] || return 0
  expected="$(grep -E "[[:space:]]\\*?${asset}\$" "$sums" 2>/dev/null | awk '{print $1}' | head -1)"
  [ -n "$expected" ] || return 0

  if command -v sha256sum >/dev/null 2>&1; then
    actual="$(sha256sum "$file" | awk '{print $1}')"
  elif command -v shasum >/dev/null 2>&1; then
    actual="$(shasum -a 256 "$file" | awk '{print $1}')"
  else
    echo "sha256sum not available — skipping checksum verify" >&2
    return 0
  fi

  if [ "$expected" != "$actual" ]; then
    echo "CHECKSUM MISMATCH for ${asset}" >&2
    return 1
  fi
  return 0
}

try_local_asset() {
  local dir cand sums
  for dir in "${LOCAL_DIRS[@]}"; do
    [ -n "$dir" ] || continue
    for cand in "$dir/$asset" "$dir/release/$asset" "$dir/dist/$asset"; do
      [ -f "$cand" ] || continue
      echo "Using local engine archive: $cand" >&2
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

  echo "Downloading HPX tunnel engine from panel mirror..." >&2
  if ! "${CURL[@]}" "${base%/}/engine/${arch_key}" -o "$work/engine.tgz"; then
    return 1
  fi

  if "${CURL[@]}" "${base%/}/engine/SHA256SUMS" -o "$work/SHA256SUMS" 2>/dev/null; then
    verify_asset "$work/engine.tgz" "$work/SHA256SUMS" || return 1
  fi
  return 0
}

try_github_asset() {
  local direct_url release_url
  direct_url="https://github.com/${ENGINE_REPO}/releases/download/${release_tag}/${asset}"
  if "${CURL[@]}" "$direct_url" -o "$work/engine.tgz"; then
    if "${CURL[@]}" "https://github.com/${ENGINE_REPO}/releases/download/${release_tag}/SHA256SUMS" -o "$work/SHA256SUMS"; then
      verify_asset "$work/engine.tgz" "$work/SHA256SUMS" || return 1
    fi
    return 0
  fi

  release_url="$("${CURL[@]}" "https://api.github.com/repos/${ENGINE_REPO}/releases/tags/${release_tag}" \
    | grep -o "https://[^\"]*${asset}" | head -1)" || true
  [ -n "$release_url" ] || return 1
  "${CURL[@]}" "$release_url" -o "$work/engine.tgz"
}

if try_local_asset; then
  :
elif try_panel_asset; then
  :
elif [ "${HPX_NO_GITHUB_FALLBACK:-0}" = "1" ]; then
  echo "HPX tunnel engine download failed from panel mirror." >&2
  echo "Ask the panel admin to run: sudo hpxpanel update" >&2
  echo "Or copy ${asset} + SHA256SUMS to /opt/hpx-pulse/engine/ and retry." >&2
  exit 1
elif try_github_asset; then
  :
else
  echo "HPX tunnel engine download failed (${ENGINE_REPO} ${release_tag})" >&2
  if [ -n "${HPX_PANEL_URL:-}${HPX_AGENT_ASSETS_BASE:-}" ]; then
    echo "Panel mirror was unavailable — ask the admin to run: sudo hpxpanel update" >&2
  fi
  echo "If GitHub is blocked, place ${asset} + SHA256SUMS in /opt/hpx-pulse/engine/ and retry." >&2
  exit 1
fi

tar -xzf "$work/engine.tgz" -C "$work"

bin="$(find "$work" -maxdepth 2 -type f -name hpx-tunnel-engine -perm -111 | head -1)"
if [ -z "$bin" ]; then
  bin="$(find "$work" -maxdepth 2 -type f -name backpack -perm -111 | head -1)"
fi
if [ -z "$bin" ]; then
  bin="$(find "$work" -maxdepth 2 -type f -perm -111 | head -1)"
fi
[ -n "$bin" ] || { echo "HPX tunnel engine binary not found in archive" >&2; exit 1; }

install -m 755 "$bin" "$TARGET"

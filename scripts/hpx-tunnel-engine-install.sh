#!/usr/bin/env bash
# Installs the HPX tunnel engine binary as /usr/local/bin/hpx-tunnel-engine
set -euo pipefail

TARGET="/usr/local/bin/hpx-tunnel-engine"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="${SCRIPT_DIR}/hpx-tunnel-engine.version"
ENGINE_REPO="${HPX_TUNNEL_ENGINE_REPO:-pooyahpx/HPXPANEL}"

# HTTP/1.1 avoids curl error 92 (PROTOCOL_ERROR) on some filtered routes (e.g. Iran).
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
  x86_64|amd64) asset="hpx-tunnel-engine_linux_amd64.tar.gz" ;;
  aarch64|arm64) asset="hpx-tunnel-engine_linux_arm64.tar.gz" ;;
  *) echo "unsupported architecture: $arch" >&2; exit 1 ;;
esac

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

direct_url="https://github.com/${ENGINE_REPO}/releases/download/${release_tag}/${asset}"
if ! "${CURL[@]}" "$direct_url" -o "$work/engine.tgz"; then
  release_url="$("${CURL[@]}" "https://api.github.com/repos/${ENGINE_REPO}/releases/tags/${release_tag}" \
    | grep -o "https://[^\"]*${asset}" | head -1)" || true
  if [ -z "$release_url" ]; then
    echo "HPX tunnel engine download failed (${ENGINE_REPO} ${release_tag})" >&2
    echo "Publish assets with workflow: Publish HPX tunnel engine binaries" >&2
    exit 1
  fi
  "${CURL[@]}" "$release_url" -o "$work/engine.tgz"
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

#!/usr/bin/env bash
# HPX NOVA TUNNEL ENGINE installer — isolated from hpx-tunnel-engine (Pulse).
set -euo pipefail

ENGINE_NAME="HPX NOVA TUNNEL ENGINE"
BIN_PATH="${HPX_NOVA_ENGINE_BIN:-/usr/local/bin/hpx-nova-tunnel-engine}"
VERSION_PIN_URL="${HPX_NOVA_VERSION_URL:-https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-nova-tunnel-engine.version}"
REPO="${HPX_NOVA_ENGINE_REPO:-pooyahpx/HPXPANEL}"

arch_raw="$(uname -m)"
case "$arch_raw" in
  x86_64|amd64) arch="amd64" ;;
  aarch64|arm64) arch="arm64" ;;
  *) echo "Unsupported arch: $arch_raw" >&2; exit 1 ;;
esac

if [[ -n "${HPX_NOVA_TUNNEL_ENGINE_VERSION:-}" ]]; then
  ver="${HPX_NOVA_TUNNEL_ENGINE_VERSION#v}"
else
  ver="$(curl --http1.1 -fsSL "$VERSION_PIN_URL" | tr -d '[:space:]' | sed 's/^v//')"
fi
[[ -n "$ver" ]] || { echo "Could not resolve Nova engine version" >&2; exit 1; }

tag="hpx-nova-tunnel-engine-v${ver}"
asset="hpx-nova-tunnel-engine_linux_${arch}.tar.gz"
url="https://github.com/${REPO}/releases/download/${tag}/${asset}"

# Prefer panel mirror when PANEL_URL is set (agent path).
if [[ -n "${PANEL_URL:-}" ]]; then
  mirror="${PANEL_URL%/}/api/hpx_nova/agent/engine/${arch}"
  if curl --http1.1 -fsSL "$mirror" -o /tmp/hpx-nova-engine.tgz; then
    url="panel-mirror"
  fi
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
if [[ "$url" == "panel-mirror" ]]; then
  tar -xzf /tmp/hpx-nova-engine.tgz -C "$work"
else
  curl --http1.1 -fsSL "$url" -o "$work/engine.tgz"
  tar -xzf "$work/engine.tgz" -C "$work"
fi

bin="$(find "$work" -type f -name 'hpx-nova-tunnel-engine' | head -1)"
[[ -n "$bin" ]] || { echo "${ENGINE_NAME} binary missing in archive" >&2; exit 1; }

install -m 755 "$bin" "$BIN_PATH"
echo "${ENGINE_NAME} installed: $BIN_PATH (v${ver})"
"$BIN_PATH" --version 2>/dev/null || "$BIN_PATH" -V 2>/dev/null || true

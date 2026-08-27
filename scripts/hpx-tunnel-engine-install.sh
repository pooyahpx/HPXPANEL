#!/usr/bin/env bash
# Installs the HPX tunnel engine binary as /usr/local/bin/hpx-tunnel-engine
set -euo pipefail

TARGET="/usr/local/bin/hpx-tunnel-engine"

if [ -x "$TARGET" ]; then
  exit 0
fi

arch="$(uname -m)"
case "$arch" in
  x86_64|amd64) asset="backpack_linux_amd64.tar.gz" ;;
  aarch64|arm64) asset="backpack_linux_arm64.tar.gz" ;;
  *) echo "unsupported architecture: $arch" >&2; exit 1 ;;
esac

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

release_url="$(curl -fsSL https://api.github.com/repos/AminMGMT/BackPack/releases/latest \
  | grep -o "https://[^\"]*${asset}" | head -1)"

if [ -z "$release_url" ]; then
  echo "HPX tunnel engine download failed" >&2
  exit 1
fi

curl -fsSL "$release_url" -o "$work/engine.tgz"
tar -xzf "$work/engine.tgz" -C "$work"

bin="$(find "$work" -maxdepth 2 -type f -name backpack -perm -111 | head -1)"
if [ -z "$bin" ]; then
  bin="$(find "$work" -maxdepth 2 -type f -perm -111 | head -1)"
fi
[ -n "$bin" ] || { echo "HPX tunnel engine binary not found in archive" >&2; exit 1; }

install -m 755 "$bin" "$TARGET"

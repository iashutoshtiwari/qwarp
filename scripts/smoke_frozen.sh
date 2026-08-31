#!/usr/bin/env bash
set -euo pipefail

binary="${1:?usage: smoke_frozen.sh BINARY VERSION}"
version="${2:?usage: smoke_frozen.sh BINARY VERSION}"
smoke_dir="$(mktemp -d)"
trap 'rm -rf "$smoke_dir"' EXIT

test "$("$binary" --version)" = "QWarp $version"
"$binary" --help | grep -q 'Qt6-based alternative desktop client'

mkdir -p "$smoke_dir/bin" "$smoke_dir/config" "$smoke_dir/runtime"
chmod 700 "$smoke_dir/runtime"
ln -s /bin/false "$smoke_dir/bin/warp-cli"
ln -s /bin/false "$smoke_dir/bin/systemctl"
ln -s /bin/false "$smoke_dir/bin/pkexec"

set +e
env \
    PATH="$smoke_dir/bin:/usr/bin:/bin" \
    QWARP_IPC_NAME="qwarp-smoke-$$" \
    QT_QPA_PLATFORM=offscreen \
    XDG_CONFIG_HOME="$smoke_dir/config" \
    XDG_RUNTIME_DIR="$smoke_dir/runtime" \
    timeout --signal=TERM --kill-after=3s 5s "$binary"
status=$?
set -e

test "$status" -eq 124

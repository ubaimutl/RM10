#!/usr/bin/env bash
# 00-fetch-tools.sh — build/fetch open-source extraction tools into tools/bin (no sudo).
# - payload-dumper-go (OTA payload.bin extractor) via go install
# - erofs-utils (dump.erofs) built from kernel.org source into tools/erofs (only if needed)
set -euo pipefail
source "$(dirname "$0")/common.sh"

mkdir -p "$TOOLS_BIN"

if [ ! -x "$TOOLS_BIN/payload-dumper-go" ]; then
  log "installing payload-dumper-go ..."
  GOBIN="$TOOLS_BIN" go install github.com/ssut/payload-dumper-go@latest 2>&1 | tail -3
else
  log "payload-dumper-go already present"
fi

# erofs support: REDMAGIC dynamic partitions may be EROFS (verify per-image with fs_magic).
# Build only on demand: ./00-fetch-tools.sh --erofs
if [ "${1:-}" = "--erofs" ]; then
  need gcc; need make; need autoconf
  if [ ! -x "$REPO_ROOT/tools/erofs/bin/dump.erofs" ]; then
    log "building erofs-utils ..."
    cd /tmp/opencode 2>/dev/null || cd "$WORK_DIR"
    rm -rf erofs-utils && git clone --depth 1 git://git.kernel.org/pub/scm/linux/kernel/git/xiang/erofs-utils.git
    cd erofs-utils
    ./autogen.sh && ./configure --prefix="$REPO_ROOT/tools/erofs" --disable-fuse --without-uuid
    make -j"$(nproc)" && make install
  else
    log "dump.erofs already present"
  fi
fi

log "tools OK:"; ls -la "$TOOLS_BIN"

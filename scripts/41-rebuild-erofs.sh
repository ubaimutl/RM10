#!/usr/bin/env bash
# 41-rebuild-erofs.sh — rebuild a candidate EROFS image from a staging tree.
# Usage: ./41-rebuild-erofs.sh <stage-tree> <partition> <out.img> [mkfs-time]
#   <stage-tree>: directory laid out like the mounted partition ROOT
#                (for system: root containing system/, system_ext/ symlinks, ...;
#                 i.e. the same layout fsck.erofs --extract produced)
#   <partition>: system | system_ext | product
# file_contexts + fs_config are taken from the STAGING tree itself
# (plat/system_ext/product _file_contexts, fs_config_dirs/files), so labels
# and uid/gid/mode stay stock-defined. Transplants must add their own entries
# (see build/transplant-fsconfig-additions.txt).
set -euo pipefail
source "$(dirname "$0")/common.sh"

[ $# -ge 3 ] || die "usage: $0 <stage-tree> <partition> <out.img> [mkfs-time]"
STAGE="$1"; PART="$2"; OUT="$3"; MKFSTIME="${4:-1779121582}"  # stock build date UTC
MKFS="$REPO_ROOT/tools/erofs/bin/dump.erofs"
[ -x "$REPO_ROOT/tools/erofs/bin/mkfs.erofs" ] || die "mkfs.erofs missing"
MKFS="$REPO_ROOT/tools/erofs/bin/mkfs.erofs"
FSCK="$REPO_ROOT/tools/erofs/bin/fsck.erofs"

case "$PART" in
  system)     FC="$STAGE/system/etc/selinux/plat_file_contexts"
              FSCFG_D="$STAGE/system/etc/fs_config_dirs"
              FSCFG_F="$STAGE/system/etc/fs_config_files" ;;
  system_ext) FC="$STAGE/etc/selinux/system_ext_file_contexts"
              FSCFG_D="$STAGE/etc/fs_config_dirs"
              FSCFG_F="$STAGE/etc/fs_config_files" ;;
  product)    FC="$STAGE/etc/selinux/product_file_contexts"
              FSCFG_D="$STAGE/etc/fs_config_dirs"
              FSCFG_F="$STAGE/etc/fs_config_files" ;;
  *) die "unknown partition $PART" ;;
esac
[ -f "$FC" ] || die "missing file_contexts: $FC"

EXTRA_CFG=""
if [ -f "$REPO_ROOT/build/transplant-fsconfig-additions.txt" ]; then
  EXTRA_CFG="$REPO_ROOT/build/transplant-fsconfig-additions.txt"
fi

log "mkfs.erofs $PART (compressor lz4, mkfs-time $MKFSTIME) ..."
log "NOTE: run this script under fakeroot (or ensure staged ownership first)."
# erofs-utils 1.9.4 takes uid/gid/mode/xattrs from the source tree:
# ownership/labels must be staged beforehand (see scripts/42-label-tree.py).
"$MKFS" -zlz4 -T"$MKFSTIME" --mkfs-time \
  "$OUT" "$STAGE" 2>&1 | tail -5

log "fsck verify ..."
"$FSCK" "$OUT" 2>&1 | tail -3
log "size: $(stat -c%s "$OUT") bytes"

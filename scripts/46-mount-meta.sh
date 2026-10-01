#!/usr/bin/env bash
# 46-mount-meta.sh — xattr-capable metadata dump via erofsfuse (unprivileged).
# Usage: ./46-mount-meta.sh <images-dir> <outdir>
# For each <part>.img: mount, walk, record path<TAB>uid<TAB>gid<TAB>mode-octal
#   <TAB>kind<TAB>link-target<TAB>xattrs(JSON-ish k=v;...) ; unmount.
# READS ONLY. Works unprivileged (FUSE + getfattr reads need no privilege).
set -euo pipefail
source "$(dirname "$0")/common.sh"
[ $# -ge 2 ] || die "usage: $0 <images-dir> <outdir> [part...]"
IMGS="$1"; OUT="$2"; shift 2
PARTS="${*:-system system_ext product vendor odm vendor_dlkm system_dlkm}"
FUSE="$REPO_ROOT/tools/erofs/bin/erofsfuse"
[ -x "$FUSE" ] || die "erofsfuse missing (rebuild with --enable-fuse)"
mkdir -p "$OUT"
need fusermount; need getfattr; need stat

for part in $PARTS; do
  img="$IMGS/$part.img"; [ -f "$img" ] || continue
  mnt="$OUT/.mnt-$part"; mkdir -p "$mnt"
  log "$part: mounting ..."
  "$FUSE" "$img" "$mnt" >/dev/null 2>&1
  # prefix inside mount: system.img root contains system/ subdir (system-as-root);
  # other partitions are rooted directly. Normalize: strip a leading partition
  # dir ONLY for system (its image root == / and holds system/ as the mount).
  log "$part: walking (stat) + recursive xattr dump ..."
  ( cd "$mnt" && find . -mindepth 1 -printf '%P\t%U\t%G\t%m\t%y\t%l\n' ) > "$OUT/$part-raw.txt"
  getfattr -R -d -m ".*" --absolute-names "$mnt" > "$OUT/$part-xattr.txt" 2>/dev/null
  python3 "$REPO_ROOT/scripts/46b-join-meta.py" "$OUT/$part-raw.txt" "$OUT/$part-xattr.txt" "$OUT/$part-meta.tsv" "$mnt"
  fusermount -u "$mnt"; rmdir "$mnt"
  log "$part: $(grep -c '' "$OUT/$part-meta.tsv") entries"
done

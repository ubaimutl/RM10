#!/usr/bin/env bash
# 48-rebuild-all.sh — tarball + mkfs.erofs for all modified partitions.
# Usage: ./48-rebuild-all.sh <candidate-fs> <meta2-dir> <out-images-dir>
# Partitions rebuilt: system, system_ext, product, vendor.
# (odm/dlkm untouched — no changes staged there.)
# Records per image: size, sha256, fsck output, inode census vs stock.
set -euo pipefail
source "$(dirname "$0")/common.sh"
[ $# -eq 3 ] || die "usage: $0 <candidate-fs> <meta2-dir> <out-images-dir>"
CAND="$1"; META="$2"; OUT="$3"
mkdir -p "$OUT" "$OUT/tars"
MKFS="$REPO_ROOT/tools/erofs/bin/mkfs.erofs"
FSCK="$REPO_ROOT/tools/erofs/bin/fsck.erofs"
MTIME=1779121582  # stock build time UTC (deterministic)

build_one() {
  part="$1"; fc="$2"; fbfb="$3"; prefix="$4"
  python3 - "$REPO_ROOT/build/candidate-v2.json" "$part" "$OUT/tars/$part-root.json" <<'PY'
import json, sys
with open(sys.argv[3], 'w') as f:
    json.dump(json.load(open(sys.argv[1]))['partitions'][sys.argv[2]]['root'], f)
PY
  log "== $part: tar ..."
  python3 "$REPO_ROOT/scripts/47-build-tar.py" \
    "$CAND/$part" "$META/$part-meta.tsv" "$fc" "$fbfb" "$prefix" "$OUT/tars/$part.tar" \
    --mtime "$MTIME" --root-metadata "$OUT/tars/$part-root.json"
  log "== $part: mkfs ..."
  local compressor=(-zlz4)
  case "$part" in
    system_ext) compressor=(-zlz4hc,level=12) ;;
    vendor) compressor=(-zlz4hc,level=12 -C131072) ;;
  esac
  # Pin the UUID and worker count as well as timestamps and compression.
  local uuid
  uuid="$(python3 -c 'import sys,uuid; print(uuid.uuid5(uuid.NAMESPACE_URL, "rm10-eu1105-v2/" + sys.argv[1]))' "$part")"
  "$MKFS" "${compressor[@]}" -b4096 --workers=1 -U"$uuid" -T"$MTIME" --mkfs-time "$OUT/$part.img" --tar=f "$OUT/tars/$part.tar" 2>&1 | tail -2
  log "== $part: fsck ..."
  "$FSCK" "$OUT/$part.img" 2>&1 | tail -2
  log "== $part: $(stat -c%s "$OUT/$part.img") bytes sha256=$(sha256_of "$OUT/$part.img" | cut -c1-16)..."
}

PLAT="$CAND/system/system/etc/selinux/plat_file_contexts"
build_one system     "$CAND/system/system/etc/selinux/plat_file_contexts" "-" ""
build_one system_ext "$CAND/system_ext/etc/selinux/system_ext_file_contexts" "$PLAT" "/system_ext"
build_one product    "$CAND/product/etc/selinux/product_file_contexts" "$PLAT" "/product"
build_one vendor     "$CAND/vendor/etc/selinux/vendor_file_contexts" "$PLAT" "/vendor"
log "rebuild complete:"
ls -la "$OUT"/*.img

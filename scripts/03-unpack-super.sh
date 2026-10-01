#!/usr/bin/env bash
# 03-unpack-super.sh — handle super.img (sparse? -> raw -> lpunpack logical partitions).
# Usage: ./03-unpack-super.sh <images-dir> <outdir>
set -euo pipefail
source "$(dirname "$0")/common.sh"

[ $# -eq 2 ] || die "usage: $0 <images-dir> <outdir>"
IMGS="$1"; OUT="$2"
need lpunpack; need simg2img
mkdir -p "$OUT"

SUPER="$(find "$IMGS" -maxdepth 1 -name 'super.img' | head -1)"
[ -n "$SUPER" ] || die "no super.img in $IMGS"

RAW="$OUT/super.raw.img"
case "$(fs_magic "$SUPER")" in
  sparse) log "sparse super -> raw"; simg2img "$SUPER" "$RAW" ;;
  *)      log "super already raw (or unknown), copying"; cp "$SUPER" "$RAW" ;;
esac

log "lpunpack ..."
lpunpack "$RAW" "$OUT/" 2>&1 | tail -3
log "logical partitions:"
ls -la "$OUT"
for f in "$OUT"/*.img; do
  [ -f "$f" ] || continue
  printf '%s %s %s\n' "$(fs_magic "$f")" "$(stat -c%s "$f")" "$(basename "$f")"
done

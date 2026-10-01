#!/usr/bin/env bash
# 01-verify-input.sh — verify a pristine firmware ZIP: size, SHA-256, zip listing.
# Usage: ./01-verify-input.sh <firmware.zip> <manifest-out>
# Never mutates the input. Manifest records everything needed to re-verify later.
set -euo pipefail
source "$(dirname "$0")/common.sh"

[ $# -eq 2 ] || die "usage: $0 <firmware.zip> <manifest-out>"
ZIP="$1"; OUT="$2"
[ -f "$ZIP" ] || die "not found: $ZIP"
need unzip; need sha256sum

mkdir -p "$(dirname "$OUT")"
SIZE="$(stat -c%s "$ZIP")"
SHA="$(sha256_of "$ZIP")"

{
  echo "# NX789J firmware input manifest"
  echo "# generated: $(date -u +%FT%TZ)"
  echo "file: $(basename "$ZIP")"
  echo "size_bytes: $SIZE"
  echo "sha256: $SHA"
  echo ""
  echo "## zip listing (name + uncompressed size)"
  unzip -l "$ZIP"
} > "$OUT"

log "manifest -> $OUT"
log "size=$SIZE sha256=$SHA"

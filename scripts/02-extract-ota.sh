#!/usr/bin/env bash
# 02-extract-ota.sh — unpack update.zip and extract payload.bin images.
# Usage: ./02-extract-ota.sh <firmware.zip> <outdir>
# Layout: <outdir>/zip-contents/... <outdir>/images/<part>.img + payload_manifest.txt
set -euo pipefail
source "$(dirname "$0")/common.sh"

[ $# -eq 2 ] || die "usage: $0 <firmware.zip> <outdir>"
ZIP="$1"; OUT="$2"
need unzip
# NOTE: Info-ZIP `unzip` trips its zipbomb detector on Nubia's ~9 GB
# payload.bin (stored entry). Prefer 7z when available.
if command -v 7z >/dev/null 2>&1; then
  UNZIPPER="7z"
else
  UNZIPPER="unzip"
fi
PDGO="$TOOLS_BIN/payload-dumper-go"
[ -x "$PDGO" ] || die "run ./00-fetch-tools.sh first (payload-dumper-go missing)"

mkdir -p "$OUT/zip-contents" "$OUT/images"
log "unzipping (no clobber of originals) ..."
if [ "$UNZIPPER" = "7z" ]; then
  7z x -o"$OUT/zip-contents" "$ZIP" >/dev/null
else
  unzip -o -q "$ZIP" -d "$OUT/zip-contents"
fi
log "zip root:"; ls "$OUT/zip-contents"

PAYLOAD="$(find "$OUT/zip-contents" -maxdepth 2 -name 'payload.bin' | head -1)"
[ -n "$PAYLOAD" ] || die "no payload.bin found (non-OTA package? inspect $OUT/zip-contents)"

log "extracting payload.bin -> $OUT/images ..."
cd "$OUT/images"
"$PDGO" -o . "$PAYLOAD" 2>&1 | tail -5

log "extracted images:"
ls -la "$OUT/images"
for f in "$OUT"/images/*.img; do
  printf '%s %s\n' "$(fs_magic "$f")" "$(basename "$f")"
done

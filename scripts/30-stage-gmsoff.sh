#!/usr/bin/env bash
# 30-stage-gmsoff.sh — build a GMS-off staging tree from pristine extraction.
# Usage: ./30-stage-gmsoff.sh <fs-root> <stage-id>
#   Copies NOTHING (works via overlay list): writes build/stage-<id>/ containing:
#     removed.txt (path + sha256 + size of every removed file)
#     manifest of survivors is generated on demand by 31-validate-stage.sh
# Design: the stage is a *transformation record*, not a file copy.
# Rebuilding images from (pristine + removals + replacements) happens in Phase 8b.
set -euo pipefail
source "$(dirname "$0")/common.sh"

[ $# -eq 2 ] || die "usage: $0 <fs-root> <stage-id>"
FS="$1"; STAGE="$2"
OUT="build/stage-$STAGE"
mkdir -p "$OUT"

 log() { echo "[stage] $*" >&2; }

REMOVED="$OUT/removed.txt"
: > "$REMOVED"
missing=0; removed=0
while IFS= read -r rel; do
  [ -z "$rel" ] && continue
  f="$FS/$rel"
  if [ -e "$f" ]; then
    # directories (overlay dirs, dpi-split apks live in dirs): record tree, do not delete here
    if [ -d "$f" ]; then
      find "$f" -type f | while read -r g; do
        printf 'TREE %s %s %s\n' "${g#$FS/}" "$(stat -c%s "$g")" "$(sha256_of "$g")" >> "$REMOVED"
      done
    else
      printf 'FILE %s %s %s\n' "$rel" "$(stat -c%s "$f")" "$(sha256_of "$f")" >> "$REMOVED"
    fi
    removed=$((removed+1))
  else
    echo "MISSING $rel" >> "$REMOVED"
    missing=$((missing+1))
  fi
done < build/gms-removal-v1.txt
while IFS= read -r rel; do
  [ -z "$rel" ] && continue
  f="$FS/$rel"
  if [ -e "$f" ]; then
    if [ -d "$f" ]; then
      find "$f" -type f | while read -r g; do
        printf 'TREE %s %s %s\n' "${g#$FS/}" "$(stat -c%s "$g")" "$(sha256_of "$g")" >> "$REMOVED"
      done
    else
      printf 'FILE %s %s %s\n' "$rel" "$(stat -c%s "$f")" "$(sha256_of "$f")" >> "$REMOVED"
    fi
    removed=$((removed+1))
  else
    echo "MISSING $rel" >> "$REMOVED"
    missing=$((missing+1))
  fi
done < build/zte-replace-v1.txt

log "stage $STAGE: entries processed, missing=$missing (see $REMOVED)"
log "counts:"; grep -c "^FILE" "$REMOVED"; grep -c "^TREE" "$REMOVED"; grep -c "^MISSING" "$REMOVED" || true

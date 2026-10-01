#!/usr/bin/env bash
# 43-dump-meta.sh — per-path uid/gid/mode truth from ORIGINAL erofs images.
# Usage: ./43-dump-meta.sh <extract-root> <images-dir> <outdir>
# For each partition dir in extract-root: enumerate files+dirs+links, query
# dump.erofs --path (8-way parallel), emit <outdir>/<part>-meta.tsv
# (path<TAB>uid<TAB>gid<TAB>mode-octal<TAB>kind). Failures -> STDERR, skipped.
set -euo pipefail
source "$(dirname "$0")/common.sh"
[ $# -eq 3 ] || die "usage: $0 <extract-root> <images-dir> <outdir>"
ROOT="$1"; IMGS="$2"; OUT="$3"
DUMP="$REPO_ROOT/tools/erofs/bin/dump.erofs"
mkdir -p "$OUT"

query_one() {
  img="$1"; rel="$2"
  out="$("$DUMP" --path="/$rel" "$img" 2>/dev/null)" || return 1
  ug=$(echo "$out" | grep -E "^Uid:" | head -1)
  uid=$(echo "$ug" | sed -E 's/Uid: *([0-9]+).*/\1/')
  gid=$(echo "$ug" | sed -E 's/.*Gid: *([0-9]+).*/\1/')
  mode=$(echo "$ug" | sed -E 's/.*Access: *0?([0-7]+).*/\1/')
  kind="f"; echo "$out" | grep -q "directory" && kind="d"
  [ -z "$uid" ] && return 1
  printf '%s\t%s\t%s\t%s\t%s\n' "$rel" "$uid" "$gid" "$mode" "$kind"
}
export -f query_one; export DUMP

for part in system system_ext product vendor odm vendor_dlkm system_dlkm; do
  [ -d "$ROOT/$part" ] || continue
  img="$IMGS/$part.img"; [ -f "$img" ] || { log "$part: no image, skip"; continue; }
  log "$part: enumerating ..."
  ( cd "$ROOT/$part" && find . -mindepth 1 | sed 's|^\./||' ) > "$OUT/$part-paths.txt"
  log "$part paths: $(wc -l < "$OUT/$part-paths.txt")"
  log "$part: querying (parallel) ..."
  # shellcheck disable=SC2016
  xargs -a "$OUT/$part-paths.txt" -d '\n' -P 8 -I{} bash -c 'query_one "$0" "$1" || echo "FAIL $1" >&2' "$img" "{}" \
    > "$OUT/$part-meta.tsv" 2> "$OUT/$part-meta.err"
  log "$part: $(grep -c '' "$OUT/$part-meta.tsv") ok, $(grep -c FAIL "$OUT/$part-meta.err") fail"
done

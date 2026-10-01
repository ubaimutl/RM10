#!/usr/bin/env bash
# 45-assemble-stage.sh — assemble the candidate staging tree.
# Usage: ./45-assemble-stage.sh <pristine-fs> <donor-apks> <out-stage-fs>
# Steps (all recorded):
#  1. hardlink-copy pristine system/system_ext/product (space-efficient)
#  2. delete removal-list files (gms + zte-replace) on the COPY
#  3. apply zte-allowlist patches (DEL_BLOCK/DEL_LINE)
#  4. install transplants + aosp allowlist XML
#  5. write transplant/removal application manifest
# Run labeling (42) + mkfs (41) afterwards, under fakeroot.
set -euo pipefail
source "$(dirname "$0")/common.sh"
[ $# -eq 3 ] || die "usage: $0 <pristine-fs> <donor-apks> <out-stage-fs>"
FS="$1"; DONOR="$2"; ST="$3"
mkdir -p "$ST"
log "hardlink copy ..."
for p in system system_ext product vendor; do
  rm -rf "$ST/$p"
  cp -al "$FS/$p" "$ST/$p"
done

MANIFEST="$ST-APPLIED.txt"
: > "$MANIFEST"

log "applying removals ..."
while IFS= read -r rel; do
  [ -z "$rel" ] && continue
  # map fs-root-relative path to stage path (top component = partition dir)
  top="${rel%%/*}"; rest="${rel#*/}"
  target="$ST/$top/$rest"
  if [ -e "$target" ] || [ -L "$target" ]; then
    if [ -d "$target" ] && [ ! -L "$target" ]; then
      find "$target" -type f | while read -r g; do echo "RM-FILE ${g#$ST/} $(stat -c%s "$g") $(sha256_of "$g")" >> "$MANIFEST"; done
      rm -rf "$target"
      echo "RM-DIR $rel" >> "$MANIFEST"
    else
      echo "RM-FILE $rel $(stat -c%s "$target") $(sha256_of "$target")" >> "$MANIFEST"
      rm -f "$target"
    fi
  else
    echo "WAS-MISSING $rel" >> "$MANIFEST"
  fi
done < <(cat "$REPO_ROOT/build/gms-removal-v1.txt" "$REPO_ROOT/build/zte-replace-v1.txt" | sort -u)

log "applying ZTE allowlist patches ..."
python3 - "$ST" <<'EOF'
import re, sys, os
stage = sys.argv[1]
def safe_write(path, data):
    # os.replace breaks the hardlink (pristine tree shares inodes via cp -al)
    tmp = path + ".stage-tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(data)
    os.replace(tmp, path)
for line in open('build/zte-allowlist-patches-v1.txt'):
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    f, action, _c = [s.strip() for s in line.split('|')]
    # stage layout: ST/<part>/<rest...> ; patch paths are fs-root-relative (part/rest...)
    fp = f"{stage}/{f}"
    txt = open(fp, encoding='utf-8').read()
    if action.startswith('DEL_BLOCK:'):
        _, start, end = action.split(':', 2)
        new, n = re.subn(start + r'.*?' + end, '', txt, flags=re.S)
        assert n >= 1, f"no block matched in {f}: {start}"
        safe_write(fp, new)
        print(f"PATCH {f}: removed {n} block(s) {start[:60]}")
    elif action.startswith('DEL_LINE:'):
        pat = action.split(':', 1)[1]
        lines = txt.splitlines(keepends=True)
        kept = [l for l in lines if pat not in l]
        assert len(kept) < len(lines), f"no line matched in {f}: {pat}"
        safe_write(fp, ''.join(kept))
        print(f"PATCH {f}: removed {len(lines)-len(kept)} line(s) {pat[:60]}")
EOF

log "installing transplants ..."
while IFS= read -r line; do
  [ -z "$line" ] || [[ "$line" == \#* ]] && continue
  donor="$(echo "${line%%|*}" | xargs)"; rest="${line#*|}"
  cand="$(echo "${rest%%|*}" | xargs)"
  donor="${donor#donor:}"
  top="${cand%%/*}"; rpath="${cand#*/}"
  # donor files stored flat: <donor-path-with-/_>.apk (already full filename)
  srcfile="$DONOR/$(echo "$donor" | tr '/' '_')"
  [ -f "$srcfile" ] || { log "MISSING donor $donor"; continue; }
  destdir="$ST/$top/$(dirname "$rpath")"
  mkdir -p "$destdir"
  cp "$srcfile" "$destdir/$(basename "$rpath")"
  echo "ADD $cand $(stat -c%s "$destdir/$(basename "$rpath")") $(sha256_of "$destdir/$(basename "$rpath")")" >> "$MANIFEST"
done < "$REPO_ROOT/build/transplants-v1.txt"
cp "$REPO_ROOT/build/privapp-permissions-aosp-transplants.xml" "$ST/system/system/etc/permissions/"
echo "ADD system/system/etc/permissions/privapp-permissions-aosp-transplants.xml" >> "$MANIFEST"

log "materializing hardlinks (labeling later mutates inodes; pristine must stay clean) ..."
find "$ST" -type f -links +1 -print0 | while IFS= read -r -d '' f; do
  cp --preserve=all "$f" "$f.stage-tmp" && mv "$f.stage-tmp" "$f"
done
log "materialize done"

log "stage assembled at $ST ; application manifest: $MANIFEST"
grep -c "^RM-" "$MANIFEST"; grep -c "^ADD" "$MANIFEST"; grep -c "WAS-MISSING\|MISSING" "$MANIFEST" || true

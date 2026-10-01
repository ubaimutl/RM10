#!/usr/bin/env bash
# common.sh — shared helpers for the NX789J firmware pipeline.
# Usage: source "$(dirname "$0")/common.sh"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLS_BIN="$REPO_ROOT/tools/bin"
FIRMWARE_DIR="$REPO_ROOT/firmware"
WORK_DIR="$REPO_ROOT/.work"

# aapt/apksigner auto-detect (host has /opt/android-sdk, no sudo needed)
if [ -z "${AAPT:-}" ]; then
  for bt in /opt/android-sdk/build-tools/*/aapt "$HOME/Android/Sdk/build-tools/"*/aapt; do
    [ -x "$bt" ] && AAPT="$bt" && break
  done
fi
if [ -z "${APKSIGNER:-}" ]; then
  for bs in /opt/android-sdk/build-tools/*/apksigner; do
    [ -x "$bs" ] && APKSIGNER="$bs" && break
  done
fi

log()  { echo "[$(date -u +%FT%TZ)] $*" >&2; }
die()  { log "FATAL: $*"; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing required tool: $1"; }

sha256_of() { sha256sum "$1" | awk '{print $1}'; }

# fs_magic <image> — prints one of: erofs ext4 sparse android-super unknown
fs_magic() {
  local f="$1" magic
  magic="$(xxd -p -l 16 "$f" 2>/dev/null | tr -d ' \n')"
  magic1024="$(xxd -p -s 1024 -l 16 "$f" 2>/dev/null | tr -d ' \n')"
  case "$magic:$magic1024" in
    e2e1f5e0*:*|*:e2e1f5e0*) echo "erofs" ;;
    3aff26ed*) echo "sparse" ;;
    00000000000000000000000000000000*) echo "empty?" ;;
    *)
      # ext4 superblock magic 0x53EF at offset 0x438
      if [ "$(xxd -p -s 1080 -l 2 "$f" 2>/dev/null)" = "53ef" ]; then echo "ext4";
      # super partition: "lpmd" geometry magic at 0x... check via lpunpack instead
      elif head -c 4 "$f" | grep -q "lpmd"; then echo "android-super";
      else echo "unknown"; fi ;;
  esac
}

#!/usr/bin/env python3
"""11-file-manifest.py — machine-readable manifest for an extracted partition tree.

Records per file: relative path, size, SHA-256, coarse type (via magic).
Usage: 11-file-manifest.py <rootdir> <out.tsv>
Output: TSV with header. Deterministic order (sorted paths).
"""
import hashlib
import os
import sys

MAGIC = {
    b"\x7fELF": "elf",
    b"PK\x03\x04": "zip/apk/jar",
    b"\x1f\x8b": "gzip",
    b"dex\n": "dex",
    b"\x02\x00\x00\x00": "axml?",  # weak; aapt used for APK truth instead
    b"oat\n": "oat",
    b"vdex": "vdex",
    b"true": "cdex?",
}


def coarse(path):
    try:
        with open(path, "rb") as f:
            head = f.read(8)
    except OSError:
        return "unreadable"
    for m, t in MAGIC.items():
        if head.startswith(m):
            return t
    if head.startswith(b"\x03\x00\x8e\xad"):  # EROFS handled at image level, not here
        return "erofs?"
    # printable text heuristic
    try:
        head.decode("utf-8")
        with open(path, "rb") as f:
            sample = f.read(4096)
        sample.decode("utf-8")
        return "text"
    except (UnicodeDecodeError, OSError):
        return "binary"


def main(root, out):
    rows = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            try:
                size = os.path.getsize(full)
                h = hashlib.sha256()
                with open(full, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                rows.append((rel, size, h.hexdigest(), coarse(full)))
            except OSError as e:
                rows.append((rel, -1, f"ERROR:{e}", "error"))
    rows.sort()
    with open(out, "w", encoding="utf-8") as f:
        f.write("path\tsize_bytes\tsha256\ttype\n")
        for rel, size, sha, typ in rows:
            f.write(f"{rel}\t{size}\t{sha}\t{typ}\n")
    print(f"wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: 11-file-manifest.py <rootdir> <out.tsv>")
    main(sys.argv[1], sys.argv[2])

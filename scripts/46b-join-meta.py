#!/usr/bin/env python3
"""46b-join-meta.py — join find-stat walk with recursive getfattr dump.

Usage: 46b-join-meta.py <raw-find.tsv> <getfattr-recursive.txt> <out-meta.tsv> <mnt-root>
raw-find columns: path uid gid mode kind link (path relative to mount root).
Output: path uid gid mode kind link xattrs(name=value;...)
"""
import sys


def main(raw, xa, out, mnt):
    mnt = mnt.rstrip("/")
    xmap, cur = {}, None
    with open(xa, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("# file: "):
                p = line[len("# file: "):]
                cur = p[len(mnt) + 1:] if p.startswith(mnt + "/") else p
                xmap[cur] = []
            elif cur is not None and "=" in line and not line.startswith("#"):
                name, _, val = line.partition("=")
                name = name.strip()
                if name.startswith(("security.", "user.", "trusted.")):
                    xmap[cur].append(f"{name}={val.strip().strip(chr(34))}")
    n = 0
    with open(out, "w") as o:
        for line in open(raw):
            p = line.rstrip("\n").split("\t")
            if len(p) < 6 or not p[0]:
                continue
            xs = ";".join(xmap.get(p[0], []))
            o.write("\t".join(p[:6] + [xs]) + "\n")
            n += 1
    print(f"wrote {out} ({n} rows)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

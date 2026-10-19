#!/usr/bin/env python3
"""Generate lossless original-inode tables directly from stock EROFS images.

No mount/FUSE/root is needed. Binary xattrs use getfattr-compatible 0s base64
notation, including symlink labels that the legacy FUSE tables omitted.
"""
import argparse
import base64
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from erofs_metadata import ErofsImage
from rm10_offline import ROOT, PARTITIONS, write_json


def extract(stock, output):
    if output.exists():
        raise ValueError("metadata output must be a new directory")
    output.mkdir(parents=True)
    counts = {}
    for part in PARTITIONS:
        rows = []
        with ErofsImage(stock / (part + ".img")) as image:
            paths = image.paths(ROOT / "tools/erofs/bin/dump.erofs")
            for path, nid in sorted(paths.items()):
                if any(c in path for c in "\n\r\t"):
                    raise ValueError("path cannot be represented in metadata TSV")
                m = image.inode(nid)
                kind = {4: "d", 8: "f", 10: "l"}.get(m["kind"])
                if kind is None:
                    raise ValueError("unsupported original inode type")
                attrs = ";".join(name + "=0s" + base64.b64encode(value).decode("ascii")
                                 for name, value in sorted(m["xattrs"].items()))
                # Symlink targets come from the byte-verified staged tree;
                # the reserved target field is not used by the tar builder.
                rows.append(f"{path}\t{m['uid']}\t{m['gid']}\t{m['mode']:o}\t{kind}\t\t{attrs}\n")
        (output / (part + "-meta.tsv")).write_text("".join(rows))
        counts[part] = len(rows)
        print(part, len(rows), "original inodes, including root", flush=True)
    write_json(output / "counts.json", counts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock", type=Path, default=ROOT / ".work/extract-eu/images")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        extract(args.stock, args.output)
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))

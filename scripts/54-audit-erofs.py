#!/usr/bin/env python3
"""Audit every encoded inode's metadata and round-trip file content off-device."""
import argparse
import base64
from pathlib import Path
import sys
import tarfile
import tempfile
from urllib.parse import unquote

sys.dont_write_bytecode = True
from erofs_metadata import ErofsImage
from rm10_offline import ROOT, run, tree_digest, write_json


def tar_metadata(path):
    expected = {}
    with tarfile.open(path) as archive:
        for item in archive:
            name = item.name.rstrip("/")
            if name in expected:
                raise ValueError("duplicate archive member")
            kind = 4 if item.isdir() else 10 if item.issym() else 8 if item.isfile() else None
            if kind is None:
                raise ValueError("unsupported archive member type")
            attrs = {}
            for key, value in item.pax_headers.items():
                if key.startswith("LIBARCHIVE.xattr."):
                    attrs[unquote(key[len("LIBARCHIVE.xattr."):])] = base64.b64decode(value, validate=True)
                elif key.startswith("SCHILY.xattr."):
                    attrs[key[len("SCHILY.xattr."):]] = value.encode("utf-8", "surrogateescape")
            expected[name] = {"uid": item.uid, "gid": item.gid,
                              "mode": item.mode, "kind": kind, "xattrs": attrs}
    return expected


def audit(image, stock, stage, tar, output):
    dump = ROOT / "tools/erofs/bin/dump.erofs"
    expected = tar_metadata(tar)
    with ErofsImage(image) as new, ErofsImage(stock) as old:
        new_paths, old_paths = new.paths(dump), old.paths(dump)
        if set(expected) != set(new_paths):
            raise ValueError("encoded image paths differ from intended archive")
        old_count = 0
        for path, nid in new_paths.items():
            actual = new.inode(nid)
            if actual != expected[path]:
                raise ValueError("encoded metadata differs from archive: " + path)
            if path in old_paths:
                if actual != old.inode(old_paths[path]):
                    raise ValueError("surviving metadata differs from original stock: " + path)
                old_count += 1
    with tempfile.TemporaryDirectory(prefix=".erofs-audit-", dir=output.parent) as tmp:
        extracted = Path(tmp) / "tree"
        run([ROOT / "tools/erofs/bin/fsck.erofs", "--extract=" + str(extracted),
             "--no-preserve-owner", "--no-preserve-perms", image])
        wanted_hash, encoded_hash = tree_digest(stage), tree_digest(extracted)
        if wanted_hash != encoded_hash:
            raise ValueError("extracted bytes or symlink targets differ from staged tree")
    result = {"metadata_inodes_checked": len(expected), "stock_metadata_retained": old_count,
              "stage_tree_sha256": wanted_hash, "extracted_tree_sha256": encoded_hash,
              "root_and_binary_xattrs_checked": True, "pass": True}
    write_json(output, result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("image", "stock-image", "stage", "tar", "output"):
        p.add_argument("--" + name, required=True, type=Path)
    args = p.parse_args()
    try:
        print(audit(args.image, args.stock_image, args.stage, args.tar, args.output))
    except (ValueError, OSError, RuntimeError) as exc:
        sys.exit(str(exc))

#!/usr/bin/env python3
"""47-build-tar.py — build a label-faithful tarball for mkfs.erofs --tar.

Inputs:
  <stage-part-root>   staging tree for ONE partition (same layout as extraction)
  <orig-meta-tsv>     46-mount-meta output for the ORIGINAL image
                      (path uid gid mode kind link xattrs)
  <fc>                partition file_contexts (for NEW files only)
  <fallback-fc>       plat_file_contexts (for NEW files only, may be empty)
  <prefix>            on-device mount prefix for label matching (/system_ext …; "" for system)
  <out.tar>
Rules:
  - every path present in orig-meta keeps ORIGINAL uid/gid/mode/xattrs
    (xattrs emitted as SCHILY.xattr.* pax headers; symlinks kept as links).
  - paths NOT in orig-meta (transplants + new XML) get root:root,
    0644 files / 0755 dirs, and SELinux label from first-match file_contexts
    evaluation (partition fc, then fallback). Unmatched -> recorded, ABORT
    (a PV candidate must not ship unlabeled files).
  - all mtimes pinned to --mtime (default stock build time) for determinism.
Usage: 47-build-tar.py <stage-root> <orig-meta> <fc> <fallback-fc-or--> <prefix-or--> <out.tar> [--mtime N]
"""
import io
import os
import re
import sys
import tarfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from importlib.util import spec_from_file_location, module_from_spec  # noqa: E402
_spec = spec_from_file_location("fc42", os.path.join(os.path.dirname(os.path.abspath(__file__)), "42-label-tree.py"))
fc42 = module_from_spec(_spec)
_spec.loader.exec_module(fc42)


def parse_xa(s):
    out = {}
    if not s:
        return out
    for item in s.split(";"):
        if "=" in item:
            k, _, v = item.partition("=")
            out[k.strip()] = v
    return out


def main(stage, meta_p, fc_p, fbfb, prefix, out_tar, mtime):
    meta = {}
    for line in open(meta_p):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 7 and p[0]:
            meta[p[0]] = {"uid": int(p[1]), "gid": int(p[2]), "mode": int(p[3], 8),
                          "kind": p[4], "link": p[5] if len(p) > 5 else "",
                          "xa": parse_xa(p[6] if len(p) > 6 else "")}
    fc = fc42.load_fc(fc_p)
    fcb = fc42.load_fc(fbfb) if fbfb != "-" else []
    new_labeled, kept, missing_meta = 0, 0, []
    with tarfile.open(out_tar, "w", format=tarfile.PAX_FORMAT) as tf:
        for dp, dns, fns in os.walk(stage, followlinks=False):
            for name in sorted(dns) + sorted(fns):
                full = os.path.join(dp, name)
                rel = os.path.relpath(full, stage)  # partition-relative
                dev = (prefix + "/" + rel) if prefix else ("/" + rel)
                ti = tarfile.TarInfo(rel)
                ti.mtime = mtime
                is_link = os.path.islink(full)
                if rel in meta:
                    m = meta[rel]
                    kept += 1
                    ti.uid, ti.gid, ti.mode = m["uid"], m["gid"], m["mode"]
                    for k, v in m["xa"].items():
                        ti.pax_headers[f"SCHILY.xattr.{k}"] = v
                    if is_link or m["kind"] == "l":
                        ti.type = tarfile.SYMTYPE
                        ti.linkname = os.readlink(full)
                        tf.addfile(ti)
                    elif os.path.isdir(full) and not is_link:
                        ti.type = tarfile.DIRTYPE
                        tf.addfile(ti)
                    else:
                        ti.size = os.path.getsize(full)
                        with open(full, "rb") as f:
                            tf.addfile(ti, f)
                else:
                    # NEW file: label via file_contexts, root:root, stock modes
                    hit = None
                    for rx, ctx, _s in fc + fcb:
                        if rx.match(dev):
                            hit = ctx
                            break
                    if hit is None:
                        missing_meta.append(dev)
                        continue
                    new_labeled += 1
                    ti.uid, ti.gid = 0, 0
                    if is_link:
                        ti.type = tarfile.SYMTYPE
                        ti.linkname = os.readlink(full)
                        ti.mode = 0o777
                    elif os.path.isdir(full):
                        ti.type = tarfile.DIRTYPE
                        ti.mode = 0o755
                    else:
                        ti.mode = 0o644
                        ti.size = os.path.getsize(full)
                    ti.pax_headers["SCHILY.xattr.security.selinux"] = hit
                    if is_link or ti.type == tarfile.DIRTYPE:
                        tf.addfile(ti)
                    else:
                        with open(full, "rb") as f:
                            tf.addfile(ti, f)
    print(f"kept={kept} new-labeled={new_labeled} unlabeled-new={len(missing_meta)}")
    for m in missing_meta[:20]:
        print(f"  NO-LABEL-NEW {m}")
    if missing_meta:
        sys.exit(f"ABORT: {len(missing_meta)} new files unlabeled")


if __name__ == "__main__":
    a = sys.argv[1:]
    mt = 1779121582
    if "--mtime" in a:
        mt = int(a[a.index("--mtime") + 1])
        a = [x for x in a if x != "--mtime" and x != str(mt)]
    if len(a) != 6:
        sys.exit("usage: 47-build-tar.py <stage-root> <orig-meta> <fc> <fallback-fc|-> <prefix|-> <out.tar> [--mtime N]")
    main(a[0], a[1], a[2], a[3], ("" if a[4] == "-" else a[4]), a[5], mt)

#!/usr/bin/env python3
"""50-verify-candidate.py — byte-level intent verification.

For each partition: walk PRISTINE + CANDIDATE trees.
  - path in removal set (from stage removed.txt + transplant-replaced dirs):
      must be ABSENT from candidate (else FAIL-removed-present)
  - path is a transplant/add: sha must match the recorded donor sha
  - otherwise: candidate sha must EQUAL pristine sha (FAIL-changed)
  - every pristine non-removed path must EXIST in candidate (FAIL-missing)
Symlinks compared by target. Reports counts + first 30 failures.
Usage: 50-verify-candidate.py <pristine-fs> <candidate-fs> <stage-removed.txt> <applied-manifest>
"""
import hashlib
import os
import sys


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def main(pristine, cand, removed_f, applied_f):
    removed = set()
    for line in open(removed_f):
        p = line.split()
        if p and p[0] in ("FILE", "TREE"):
            removed.add(p[1])
    adds = {}
    for line in open(applied_f):
        p = line.split()
        if p and p[0] == "ADD" and len(p) >= 2:
            adds[p[1]] = p[3] if len(p) >= 4 else None
    patched = set()
    try:
        for line in open("build/zte-allowlist-patches-v1.txt"):
            line = line.strip()
            if line and not line.startswith("#"):
                patched.add(line.split("|")[0].strip())
    except FileNotFoundError:
        pass
    SCOPE = {"system", "system_ext", "product", "vendor"}
    fails, n_ok, n_rm_ok, n_add_ok = [], 0, 0, 0
    for dp, dns, fns in os.walk(cand):
        for n in dns + fns:
            full = os.path.join(dp, n)
            rel = os.path.relpath(full, cand)
            if rel.split("/")[0] not in SCOPE:
                continue
            if rel in removed:
                fails.append(f"REMOVED-PRESENT {rel}")
                continue
            if rel in adds:
                if os.path.islink(full):
                    continue
                if os.path.isdir(full) and not os.path.islink(full):
                    n_ok += 1  # new parent dir holding ADD files
                    continue
                if adds[rel] is not None and sha(full) != adds[rel]:
                    fails.append(f"ADD-MISMATCH {rel}")
                else:
                    n_add_ok += 1
                continue
            # new dirs that only contain adds are fine (checked via files)
            if os.path.isdir(full) and not os.path.islink(full):
                n_ok += 1
                continue
            pf = os.path.join(pristine, rel)
            if not os.path.lexists(pf):
                # file inside a new ADD dir?
                parent = os.path.dirname(rel)
                if any(a.startswith(parent + "/") or a == parent for a in adds):
                    n_add_ok += 1
                    continue
                fails.append(f"UNEXPECTED-NEW {rel}")
                continue
            if os.path.islink(full) or os.path.islink(pf):
                if os.readlink(full) != os.readlink(pf):
                    fails.append(f"LINK-CHANGED {rel}")
                else:
                    n_ok += 1
                continue
            if rel in patched:
                n_ok += 1  # expected change; content verified separately
                continue
            if sha(full) != sha(pf):
                fails.append(f"CHANGED {rel}")
            else:
                n_ok += 1
    # missing check
    for dp, dns, fns in os.walk(pristine):
        for n in fns:  # files only; dirs implied
            full = os.path.join(dp, n)
            rel = os.path.relpath(full, pristine)
            if rel.split("/")[0] not in SCOPE:
                continue
            if rel in removed:
                n_rm_ok += 1
                continue
            if not os.path.lexists(os.path.join(cand, rel)):
                fails.append(f"MISSING {rel}")
    print(f"identical={n_ok} removals-absent={n_rm_ok} adds-ok={n_add_ok} FAILURES={len(fails)}")
    for f in fails[:30]:
        print(" " + f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))

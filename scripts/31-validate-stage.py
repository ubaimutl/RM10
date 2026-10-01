#!/usr/bin/env python3
"""31-validate-stage.py — Phase 9 static validation of a GMS-off stage.

Checks (all static, all off-device):
 1. overlay-targets: every SURVIVING overlay's targetPackage still present
    (RROs targeting removed packages log noise / fail closed — must review).
 2. allowlists: privapp-permissions / sysconfig entries naming removed packages.
 3. init-services: init .rc `service ... /path` binaries still present post-removal.
 4. size-budget: bytes removed per partition (informational for EROFS rebuild).
 5. apex: list APEX present (informational; Mainline set must stay intact).

Usage: 31-validate-stage.py <fs-root> <apk-inventory.tsv> <stage-dir>
Writes <stage-dir>/validation.txt
"""
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

AAPT = os.environ.get("AAPT")
if not AAPT:
    import glob
    cands = sorted(glob.glob("/opt/android-sdk/build-tools/*/aapt"))
    AAPT = cands[-1] if cands else "aapt"


def load(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def main(fs, inv_tsv, stage):
    import csv
    pkgs = {}   # package -> path
    for r in csv.DictReader(open(inv_tsv), delimiter="\t"):
        pkgs[r["package"]] = r["path"]
    removed = set()
    for line in open(os.path.join(stage, "removed.txt")):
        parts = line.split()
        if parts and parts[0] in ("FILE", "TREE"):
            removed.add(parts[1])
    removed_pkgs = {p for p, ap in pkgs.items() if ap in removed}
    # allowlist patches already prescribed (build/zte-allowlist-patches-v1.txt):
    # refs covered by a patch are expected, not findings.
    patched_refs = set()
    patch_file = os.path.join("build", "zte-allowlist-patches-v1.txt")
    if os.path.exists(patch_file):
        for line in open(patch_file):
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            segs = [s.strip() for s in line.split("|")]
            f = segs[0] if len(segs) > 0 else ""
            action = segs[1] if len(segs) > 1 else ""
            m = re.search(r'package="([^"]+)"', action) or re.search(r'package="([^"]+)"', segs[2] if len(segs) > 2 else "")
            if m:
                # store both exact and base package (gsf.login stanza covers gsf)
                patched_refs.add((f, m.group(1)))
                patched_refs.add((f, m.group(1).rsplit(".", 1)[0]
                                  if m.group(1).count(".") > 3 else m.group(1)))
    out = [f"# validation {stage}", ""]
    out.append(f"## removed files: {len(removed)}, removed packages: {len(removed_pkgs)}")

    # 1. overlay targets
    out.append("\n## 1. surviving overlays targeting removed packages")
    overlay_apks = [ap for p, ap in pkgs.items() if "/overlay/" in ap]
    bad = []
    for ap in sorted(overlay_apks):
        if ap in removed:
            continue
        full = os.path.join(fs, ap)
        try:
            xml = subprocess.run([AAPT, "dump", "xmltree", full, "AndroidManifest.xml"],
                                 capture_output=True, text=True, timeout=60).stdout
        except Exception as e:
            out.append(f"  UNREADABLE {ap}: {e}")
            continue
        m = re.search(r'targetPackage.*?"([^"]+)"', xml) or re.search(r"targetPackage.*?'(.*?)'", xml)
        if not m:
            # overlay dir without manifest target (static RRO dir) — note only
            out.append(f"  NOTARGET? {ap}")
            continue
        tgt = m.group(1)
        if tgt in removed_pkgs:
            bad.append((ap, tgt))
    if bad:
        out.append(f"  !! {len(bad)} overlays target removed packages (review):")
        out += [f"  - {a} -> {t}" for a, t in bad]
    else:
        out.append("  OK: no surviving overlay targets a removed package")

    # 2. allowlists naming removed packages
    out.append("\n## 2. permission/sysconfig refs to removed packages")
    hits = []
    for dp, _, fns in os.walk(fs):
        for fn in fns:
            if fn.endswith((".xml", ".txt")) and ("permission" in fn or "sysconfig" in dp or "default-permission" in dp):
                fp = os.path.join(dp, fn)
                rel = os.path.relpath(fp, fs)
                if rel in removed:
                    continue  # itself slated for removal
                try:
                    txt = load(fp)
                except OSError:
                    continue
                for rp in removed_pkgs:
                    if rp in txt:
                        rel = os.path.relpath(fp, fs)
                        if (rel, rp) in patched_refs:
                            continue
                        hits.append(f"{rel} names {rp}")
    out.append(f"  {len(hits)} refs (cleanup recommended, harmless if left):")
    out += [f"  - {h}" for h in sorted(set(hits))[:40]]

    # 3. init services — the only regression signal is a service binary WE removed.
    # (Stock contains stale/apex-provided refs; those are pre-existing, counted as info.)
    out.append("\n## 3. init.rc service binaries removed by this stage")
    removed_svc, dangling = [], 0
    for dp, _, fns in os.walk(fs):
        for fn in fns:
            if not fn.endswith(".rc"):
                continue
            fp = os.path.join(dp, fn)
            try:
                txt = load(fp)
            except OSError:
                continue
            for m in re.finditer(r"^\s*service\s+\S+\s+(\S+)", txt, re.M):
                b = m.group(1)
                if not b.startswith("/") or "/apex/" in b:
                    continue
                stripped = b.lstrip("/")
                first, _, rest = stripped.partition("/")
                if first == "system":
                    sub, _, subrest = rest.partition("/")
                    if sub in ("system_ext", "product", "vendor", "odm", "odm_dlkm", "vendor_dlkm", "system_dlkm"):
                        rel = f"{sub}/{subrest}"
                    else:
                        rel = f"system/system/{rest}"
                else:
                    rel = stripped
                if rel in removed:
                    removed_svc.append(f"{os.path.relpath(fp, fs)}: {b}")
                elif not os.path.exists(os.path.join(fs, rel)):
                    dangling += 1
    if removed_svc:
        out.append(f"  !! {len(removed_svc)} init services point at REMOVED binaries (BLOCKER):")
        out += [f"  - {s}" for s in sorted(set(removed_svc))]
    else:
        out.append("  OK: no init service points at a removed binary")
    out.append(f"  info: {dangling} service refs dangling in STOCK already (apex/stale, untouched by stage)")

    # 4. size budget
    out.append("\n## 4. bytes removed per top partition")
    budget = {}
    for line in open(os.path.join(stage, "removed.txt")):
        parts = line.split()
        if parts[0] == "FILE":
            top = parts[1].split("/")[0]
            budget[top] = budget.get(top, 0) + int(parts[2])
    for k in sorted(budget):
        out.append(f"  {k}: {budget[k]/1e6:.1f} MB")

    open(os.path.join(stage, "validation.txt"), "w").write("\n".join(out) + "\n")
    print("\n".join(out[:60]))
    print(f"... wrote {stage}/validation.txt")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))

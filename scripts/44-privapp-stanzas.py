#!/usr/bin/env python3
"""44-privapp-stanzas.py — derive privapp-permissions stanzas for transplant APKs.

Method (no guessing):
 1. Requested permissions per APK via `aapt dump badging`.
 2. protectionLevel per permission from the STOCK frameworks-res AndroidManifest
    (aapt dump xmltree), mapping SDK int flags -> signature|privileged/etc.
    protectionLevel bits (API 36): 0x2=signature, 0x10=privileged, plus
    knownFlags (0x10000=...). We parse the hex and test bits 0x2 and 0x10
    on the BASE mask (low 16 bits), which is stable across releases.
 3. Emit stanza with exactly the signature|privileged subset.
 4. FLAG as BLOCKER any requested permission whose base level is pure
    `signature` (ungrantable to non-platform-signed transplants).

Usage: 44-privapp-stanzas.py <framework-res.apk> <apk> [apk...]
"""
import re
import subprocess
import sys

AAPT = "/opt/android-sdk/build-tools/36.0.0/aapt"


def manifest_xml(apk):
    r = subprocess.run([AAPT, "dump", "xmltree", apk, "AndroidManifest.xml"],
                       capture_output=True, text=True, timeout=120)
    return r.stdout


def requested(apk):
    r = subprocess.run([AAPT, "dump", "badging", apk],
                       capture_output=True, text=True, timeout=120)
    return sorted(set(re.findall(r"uses-permission: name='([^']+)'", r.stdout)))


def protection_levels(fw_res):
    """permission name -> (base_hex, raw_string)"""
    xml = manifest_xml(fw_res)
    levels = {}
    # <uses-permission android:name=... > then <permission ...> blocks; simpler:
    # find E: permission ... A: android:name="X" ... A: android:protectionLevel=(type 0x10)0xNNN
    blocks = re.split(r"E: permission ", xml)
    for b in blocks[1:]:
        name = re.search(r'android:name\(0x[0-9a-fA-F]+\)="([^"]+)"', b)
        prot = re.search(r"protectionLevel\(0x[0-9a-fA-F]+\)=\(type 0x1[01]\)(0x[0-9a-fA-F]+)", b)
        if name and prot:
            try:
                levels[name.group(1)] = int(prot.group(1), 16)
            except ValueError:
                pass
    return levels


def classify(level_int):
    base = level_int & 0xFFFF
    sig = bool(base & 0x2)
    priv = bool(base & 0x10)
    if sig and priv:
        return "signature|privileged"
    if sig:
        return "signature"
    return "normal-or-lower"


def main(fw_res, apks):
    levels = protection_levels(fw_res)
    print(f"<!-- derived from {len(levels)} framework permission definitions -->")
    for apk in apks:
        req = requested(apk)
        pkgm = re.search(r"package: name='([^']+)'",
                         subprocess.run([AAPT, "dump", "badging", apk],
                                        capture_output=True, text=True, timeout=120).stdout)
        pkg = pkgm.group(1) if pkgm else "UNKNOWN"
        grant, blockers, unknown = [], [], []
        for p in req:
            if not p.startswith("android.permission."):
                continue  # custom perms handled by their defining app, not here
            if p not in levels:
                unknown.append(p)
                continue
            c = classify(levels[p])
            if c == "signature|privileged":
                grant.append(p)
            elif c == "signature":
                blockers.append(p)
        print(f"<privapp-permissions package=\"{pkg}\">")
        for p in sorted(grant):
            print(f'    <permission name="{p}"/>')
        print("</privapp-permissions>")
        if blockers:
            print(f"<!-- BLOCKER: {pkg} needs pure-signature (ungrantable): {', '.join(blockers)} -->")
        if unknown:
            print(f"<!-- NOTE: {pkg} {len(unknown)} android perms not in framework defs (likely runtime/vendor-defined): {', '.join(unknown[:6])} -->")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: 44-privapp-stanzas.py <framework-res.apk> <apk> [apk...]")
    main(sys.argv[1], sys.argv[2:])

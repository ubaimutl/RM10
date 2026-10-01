#!/usr/bin/env python3
"""10-apk-inventory.py — APK inventory for an extracted partition tree.

For every *.apk: package, versionName/versionCode, SDK targets, permissions,
privileged flag (path under priv-app), signing certs (SHA-256 + subject).

Uses host aapt ($AAPT or auto-detect) and apksigner ($APKSIGNER or auto-detect).
Usage: 10-apk-inventory.py <rootdir> <out.tsv>
"""
import glob
import os
import re
import subprocess
import sys

AAPT = os.environ.get("AAPT") or glob.glob("/opt/android-sdk/build-tools/*/aapt", recursive=False)[-1]
APKSIGNER = os.environ.get("APKSIGNER") or glob.glob("/opt/android-sdk/build-tools/*/apksigner")[-1]


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
    except Exception as e:
        return f"ERROR:{e}"


def parse_badging(text):
    pkg = re.search(r"^package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", text, re.M)
    sdk = re.search(r"^sdkVersion:'([^']+)'", text, re.M)
    target = re.search(r"^targetSdkVersion:'([^']+)'", text, re.M)
    perms = re.findall(r"^uses-permission: name='([^']+)'", text, re.M)
    app = re.search(r"^application:.*label='([^']*)'", text, re.M)
    shared = re.search(r"^sharedUserId='([^']+)'", text) or re.search(r"sharedUserId='([^']+)'", text)
    return {
        "package": pkg.group(1) if pkg else "?",
        "versionCode": pkg.group(2) if pkg else "?",
        "versionName": pkg.group(3) if pkg else "?",
        "sdk": sdk.group(1) if sdk else "?",
        "targetSdk": target.group(1) if target else "?",
        "label": app.group(1) if app else "",
        "sharedUserId": shared.group(1) if shared else "",
        "permissions": ";".join(sorted(set(perms))),
    }


def certs(apk):
    out = run(["java", "-jar", APKSIGNER, "verify", "--print-certs", apk])
    digests = re.findall(r"certificate SHA-256 digest: (\S+)", out)
    subjects = re.findall(r"certificate DN: (.+)", out)
    return ("|".join(digests) or "?", " // ".join(subjects) or "?".replace("?", ""))


def main(root, out_path):
    apks = sorted(f for dp, _, fns in os.walk(root) for f in [os.path.join(dp, fn) for fn in fns] if f.endswith(".apk"))
    with open(out_path, "w", encoding="utf-8") as out:
        out.write("path\tpackage\tversionName\tversionCode\tsdk\ttargetSdk\tlabel\tsharedUserId\tprivileged\tpermissions\tcert_sha256\tcert_subject\n")
        for apk in apks:
            rel = os.path.relpath(apk, root)
            info = parse_badging(run([AAPT, "dump", "badging", apk]))
            digest, subject = certs(apk)
            priv = "yes" if "/priv-app/" in rel else "no"
            out.write("\t".join([rel, info["package"], info["versionName"], info["versionCode"],
                                  info["sdk"], info["targetSdk"], info["label"], info["sharedUserId"],
                                  priv, info["permissions"], digest, subject]) + "\n")
    print(f"inventoried {len(apks)} APKs -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: 10-apk-inventory.py <rootdir> <out.tsv>")
    main(sys.argv[1], sys.argv[2])

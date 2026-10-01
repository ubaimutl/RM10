#!/usr/bin/env python3
"""20-gms-scan.py — strict GMS-dependency scan over APK dex strings.

For each APK: unzip classes*.dex in memory, extract strings, match strict
Java type descriptors / package prefixes that indicate a REAL code
dependency on Google Mobile Services (not TLD tables or prose).

Usage: 20-gms-scan.py <fs-root> <apk-list-file> <out.tsv>
  apk-list-file: one APK path per line, relative to fs-root (or absolute).
Output TSV: apk, class_refs, intent_refs, permission_refs, provider_refs, notes
"""
import re
import sys
import zipfile

CLASS_PATTERNS = [
    (r"Lcom/google/android/gms/", "gms-core"),
    (r"Lcom/google/firebase/", "firebase"),
    (r"Lcom/google/android/location/", "fused-location"),
    (r"Lcom/google/android/auth/", "gsa-auth"),
    (r"Lcom/google/android/vending/", "vending-licensing"),
    (r"Lcom/google/android/play/", "play-core"),
    (r"Lcom/google/android/finsky/", "finsky"),
    (r"Lcom/android/billingclient/", "billing"),
    (r"Lcom/google/ads/", "ads"),
    (r"Lcom/google/android/aidl/", "aidl-base"),
    (r"Lcom/google/android/useragent/", "useragent"),
]
INTENT_PATTERNS = [
    (r"com\.google\.android\.gms\.", "gms-intent/action"),
    (r"com\.google\.android\.c2dm\.", "c2dm-push"),
    (r"com\.google\.firebase\.", "firebase-action"),
]
PROVIDER_PATTERNS = [
    (r"com\.google\.android\.gms", "gms-provider/auth"),
    (r"com\.google\.settings", "google-settings-provider"),
]
PERM_PATTERNS = [
    (r"com\.google\.android\.c2dm\.permission\.RECEIVE", "c2dm-receive"),
    (r"com\.google\.android\.providers\.gsf\.permission\.READ_GSERVICES", "gservices-read"),
    (r"com\.google\.android\.gms\.permission\.", "gms-permission"),
    (r"com\.android\.vending\.(BILLING|CHECK_LICENSE)", "vending-perm"),
]


def dex_strings(data):
    # dex stores strings as MUTF-8 length-prefixed; crude but effective:
    # split on non-printable runs
    out = set()
    cur = bytearray()
    for b in data:
        if 32 <= b < 127:
            cur.append(b)
        else:
            if len(cur) >= 8:
                try:
                    out.add(cur.decode("ascii"))
                except UnicodeDecodeError:
                    pass
            cur = bytearray()
    if len(cur) >= 8:
        try:
            out.add(cur.decode("ascii"))
        except UnicodeDecodeError:
            pass
    return out


def scan(apk_path):
    try:
        z = zipfile.ZipFile(apk_path)
    except Exception as e:
        return ("ERR:" + str(e)[:60], "", "", "", "")
    strings = set()
    for name in z.namelist():
        if re.fullmatch(r"classes\d*\.dex", name.split("/")[-1]):
            try:
                strings |= dex_strings(z.read(name))
            except Exception:
                pass
    hits_c, hits_i, hits_p, hits_pm = {}, [], [], []
    for s in strings:
        for pat, label in CLASS_PATTERNS:
            if re.search(pat, s):
                hits_c.setdefault(label, set()).add(s[:120])
        for pat, label in INTENT_PATTERNS:
            if re.search(pat, s):
                hits_i.append(label + ":" + s[:100])
        for pat, label in PROVIDER_PATTERNS:
            if re.search(pat, s):
                hits_p.append(label + ":" + s[:100])
        for pat, label in PERM_PATTERNS:
            if re.search(pat, s):
                hits_pm.append(label)
    c = ";".join(f"{k}({len(v)})" for k, v in sorted(hits_c.items()))
    return (c, ";".join(sorted(set(hits_i))[:8]), ";".join(sorted(set(hits_p))[:8]),
            ";".join(sorted(set(hits_pm))))


def main(root, lst, out):
    import os
    apks = [l.strip() for l in open(lst) if l.strip()]
    with open(out, "w") as f:
        f.write("apk\tclass_refs\tintent_refs\tprovider_refs\tpermission_refs\n")
        for a in apks:
            p = a if os.path.isabs(a) else os.path.join(root, a)
            c, i, pr, pm = scan(p)
            f.write(f"{a}\t{c}\t{i}\t{pr}\t{pm}\n")
    print(f"scanned {len(apks)} -> {out}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))

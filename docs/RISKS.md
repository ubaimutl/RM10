# RISKS

Severity: CRITICAL (device/data loss or irreversible) · HIGH (project failure / wrong architecture) · MED (rework) · LOW (nuisance).
Owner constraint: NX789J is the primary device. No flashing without explicit authorization. Ever.

## R-01 — CRITICAL — Modem/region damage via CN firmware
Cross-flashing CN packages (or mixing CN modem/radio/vendor-radio config into EU base) may break LTE bands/VoLTE (see FINDINGS F-10). Mitigation: EU low-level foundation is inviolable; CN components (if ever used) restricted to product/system overlays only after diff proves radio-neutrality; never touch modem/EFS/persist/modemst/NV. Status: MITIGATED BY DESIGN (approach A).

## R-02 — CRITICAL — Bootloader unlock / eFuse uncertainty on SM8750
Community reports free-unlock beta for RM10 with "do not update to 11.0.13+" andвард eFuse speculation (F-11). Owner on 11.0.5MR1. Any unlock attempt or OTA could theoretically change fuse state. Mitigation: NO unlock, NO update, NO EDL, NO flashing actions at all until a signed-off test plan exists; freeze updater on device (recommend to owner separately). Status: AVOIDED (no device ops).

## R-03 — CRITICAL — No verified rollback path yet
Without a complete, hashed stock backup (EDL backup per slot + recovery + super images) and a tested restore procedure, any flash is one-way. Mitigation: test plan (Phase 10) requires backup + hashes + slot strategy + abort criteria BEFORE any flash proposal. Status: OPEN.

## R-04 — HIGH — Attack surface of closed flashing tools
ZTE Family Toolbox, UnlockTool, QFIL-adjacent paid zips, Baidu mirrors, password-locked EDL packages: malware/brick risk. Mitigation: treat as untrusted; prefer official Nubia CDN + open-source tooling (payload-dumper-go, bkerler/edl for STUDY only); hash everything; never execute closed tools on the build host without sandbox analysis. Status: MITIGATED BY POLICY.

## R-05 — HIGH — Wrong-architecture commitment (A vs B vs C vs D)
Choosing full AOSP/Lineage too early discards the working ZTE stack (UDFPS cmd10, Game Space, triggers, audio extensions); choosing CN-hybrid risks radio breakage. Mitigation: decision gated on EU-vs-CN diff + Google-dependency graph (Phases 4–7). Current lean: A. Status: OPEN (evidence pending).

## R-06 — HIGH — GMS dependency deeper than package list
REDMAGIC services may bind GMS APIs (location, push, auth, integrity) and crash-loop if GMS is removed naively. Mitigation: Phase 5 dependency graph (smali/native/permission/allowlist/init/SELinux/VINTF analysis), then stub-or-repair per edge, never blind deletion. Status: OPEN.

## R-07 — HIGH — Firmware provenance / supply chain
HalabTech/romprovider mirrors, Baidu Pan, Telegram/Discord blobs: tampered images possible. Mitigation: prefer official CDN; cross-check sizes/checksums across mirrors; record SHA-256 of every artifact; immutable inputs. Status: PARTLY MITIGATED (EU from official CDN).

## R-08 — MED — Version skew (V11.0.05MR1 vs V2.0.0B05MR1)
Official page label and URL version disagree. Risk of analyzing a different build than the owner's. Mitigation: resolve from payload_properties/build fingerprint post-extraction; record fingerprint; compare with owner's `ro.build.fingerprint` (ask owner to provide via `adb shell getprop`, read-only, safe). Status: OPEN.

## R-09 — MED — /tmp exhaustion on build host
/tmp is tmpfs ~98% full; multi-GB images must NOT go to /tmp. Mitigation: all large artifacts under `firmware/` (workspace, 39 GB free); /tmp/opencode only for small decompiles. Status: MITIGATED.

## R-10 — MED — Recovery flash constraints misunderstood
NX789J rejects `fastboot boot`/`fastboot flash recovery`; recovery install needs dd from root/recovery. Any test plan must respect this or risk slot confusion. Mitigation: documented in F-02; test plan to use logical-partition-only experiments first. Status: DOCUMENTED.

## R-11 — LOW — Sibling-device knowledge misapplied
RM11 (NX809J) sysfs/event indices/settings may differ on NX789J (e.g. event7 vs event4/5, brightness max 2047 vs 4095). Mitigation: every sibling claim tagged; NX789J-stock verification required before use. Status: TRACKED via QUESTIONS.

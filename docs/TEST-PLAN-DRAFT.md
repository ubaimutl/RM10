# Safe hardware test plan — DRAFT FOR OWNER REVIEW (DO NOT EXECUTE)

No step below is authorized. Nothing here flashes, unlocks, wipes, or modifies
the device. This plan exists so the owner can approve, amend, or reject each gate.

## Gate 0 — Preconditions (all must hold before any device step)

- [ ] Complete stock backup exists: EDL read-back of BOTH slots' critical partitions
      (boot, init_boot, vendor_boot, recovery, vbmeta*, super, modem, persist,
      EFS/modemst, ztecfg, uefivarstore) with SHA-256 recorded, stored off-device.
- [ ] Stock restore path TESTED on an identical spare device OR via read-back
      verification (never "tested" on the owner's phone first).
- [ ] Owner confirms data backup (photos, 2FA, chats) — device WILL be wiped by unlock.
- [ ] Owner accepts known irreversible changes: Widevine L1→L3 (documented),
      SafetyNet/PlayIntegrity fail, banking apps may refuse, warranty implications.
- [ ] Bootloader unlock compatibility for 11.0.5MR1_EU confirmed by community
      (currently NO published RM10 matrix — see QUESTIONS Q-10; do not proceed blind).
- [ ] EDL/firehose write path confirmed working on this exact build (read-back test only).
- [ ] Candidate images pass ALL Phase 9 static gates (already green for stage v1,
      must re-run after AOSP transplants + EROFS rebuild).
- [ ] Updater frozen on device (no OTA during experiments).

## Gate 1 — Unlock + backup (destructive to data, reversible to stock)

1. Unlock bootloader via the community free path ONLY IF Gate-0 version
   compatibility is confirmed. Record `fastboot getvar unlocked`.
2. Immediate full EDL backup (see Gate 0 list). Verify hashes.
3. Boot stock, confirm baseline: run the hardware test matrix subset
   (docs/TEST-MATRIX.md BOOT+DISPLAY+REDMAGIC+PHONE) on STOCK unlocked —
   establishes the unlocked-baseline (fingerprint behavior post-unlock!).

ABORT/ROLLBACK: relock is NOT clean (wiki: certification stays broken).
Rollback = restore EDL backup to both slots. If restore fails → STOP, seek spare-device recovery.

## Gate 2 — Smallest possible first experiment (no full flash)

Prefer slot-B-only, logical-partitions-only trials:
- Flash rebuilt `system_b` ALONE (GMS-off, ZTE stack intact) with patched
  vbmeta_system_b; keep vendor/odm/modem/boot untouched; keep slot A pristine.
- Expected: boot to launcher, Game Space + triggers + fan work, no GMS crash loops.
- If boot fails: `fastboot --set-active=a` back to pristine slot. REQUIREMENT:
  verify slot-switch works BEFORE flashing B (test A→B→A on stock images).

## Gate 3 — Full candidate (only after Gate 2 green)

Flash rebuilt system/system_ext/product (+ AOSP transplants) to slot B,
patched vbmeta chain, boot, run FULL docs/TEST-MATRIX.md incl. network audit
(boot with no user apps, capture DNS/TLS 15 min, classify endpoints).

## Gate 4 — Acceptance

All matrix rows pass + network audit shows no privileged-Google system traffic
+ modem/radio behavior identical to stock (signal, bands, VoLTE).
Result is still labeled CANDIDATE until 2 weeks daily-driver stability.

## Explicitly forbidden at every gate

- Modem/EFS/persist/ztecfg/uefivarstore writes. Radio-region experiments. Relocking around modified images. `fastboot flash` to the ACTIVE slot. Any step while EDL is unavailable.

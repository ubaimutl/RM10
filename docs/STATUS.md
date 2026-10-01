# STATUS — NX789J Google-free REDMAGIC OS project

Last updated: 2026-10-01 (UTC). Owner build: RedMagicOS 11.0.5MR1 EU, Android 16, kernel 6.6.92-android15-8-g3637f4904cf5.

## Where we are

**Phase 1 (research repo): IN PROGRESS.** Repo skeleton created, 9 source repos cloned, official EU firmware download started.

**Phase 2 (firmware landscape): IN PROGRESS.**
- EU target firmware IDENTIFIED + downloading: `V2.0.0B05MR1` (page label V11.0.05MR1), official Nubia CDN, 8,733,027,332 bytes, Last-Modified 2026-07-09. See `firmware-manifests/EU-V2.0.0B05MR1.md` once download completes.
- CN leads named but NOT yet acquired: `GEN_CN_NX789JV1.0.0B24_SD_WO_ERA.zip`, `GEN_CN_NX789JV1.0.0B12MR1_SD_WO_ERA.zip` (HalabTech listing; B12MR1 mirror is Baidu Pan — effectively inaccessible; trust/provenance unverified).
- Global (NEEA) Android-15-era OTA known: `GEN_NEEA_NX789JV1.0.0B13MR1_SD_WO_ERA` at `rom.download.nubia.com/Europe&Asia/NX789J/V10.0.13/update.zip` (not yet downloaded).

**Phase 3 (extraction pipeline): DONE.** payload-dumper-go + erofs-utils built local; scripts/ verify/extract/inventory/manifest/gms-scan all working.

**Phase 4 (EU firmware): DONE.** Official EU full OTA (RedMagicOS11.0.5MR1_EU == owner build, SHA-256 07eaf8be…) extracted: 44 partition images, 7 EROFS logical partitions, 574-APK inventory, per-file manifests, AVB chain mapped (vbmeta→boot/recovery/vbmeta_system; vbmeta_system→pvmfw/product/system/system_ext; vbmeta→dtbo/init_boot/vendor_boot/odm/system_dlkm/vendor/vendor_dlkm).

**Phase 5 (Google graph): STATIC DONE.** 26 priv Google APKs + ~53 apps + ~15 overlays inventoried for removal; REDMAGIC gaming stack GMS-clean; 12 dirty exceptions triaged. Artifacts in package-analysis/.

**Phase 6 (REDMAGIC graph): WELL UNDERWAY.** UDFPS protocol, triggers (sar0/1 + KEY_F7/F8 + nubia_game_scene), fan/LED/micropump/slider sysfs, charge-separation Settings keys all mapped statically.

**Phase 7 (architecture): INTERIM DECISION — Approach A** (rebuilt EU REDMAGIC OS). See docs/ARCHITECTURE.md.

**Phases 8–10: NOT STARTED** (staging script → rebuild pipeline → static validation → test plan for review).

## Key results so far

1. **No native NX789J custom ROM with Game Space exists (STRONG EVIDENCE, re-verified 2026-10-01).** Only GSI + root-module fixes exist. A Danish XDA post (Sep 2025) confirms GSI state: SIM off, under-screen camera unusable, shoulder triggers unusable on phh GSIs.
2. **Recovery knowledge is mature (VERIFIED from source).** OrangeFox tree (plompomg, active as of 2026-09-30) and TWRP tree (reminon, twrp-16.0 branch) give us: full partition map, fstab (FBE wrappedkey-v0, ICE), dynamic-partition list, verified sysfs nodes (`/sys/kernel/fan/*`, `aw22xxx_led`, `zte_battery`, `/sys/class/leds/sar0|sar1` implied by input blacklist `nubia_tgk_aw_sar0_ch0/1_ch0`), input blacklist, touch driver modules (`zte_tpd.ko`, `panel_event_notifier.ko`, `aw9620x.ko` SAR, `aw882xx` audio, `drm_display_helper/msm_drm`).
3. **UDFPS reverse-engineering is complete and reusable (VERIFIED from decompiled daemon).** sequencode's ZteFodDaemon documents the full ZTE fingerprint extension protocol — see `research/udfps-zte-protocol.md`.
4. **Shoulder-trigger mechanism mapped (STRONG EVIDENCE).** SAR input devices `nubia_tgk_aw_sar` → KEY_F7/F8; enable via `nubia_game_scene=1` (+ `sar*/mode_operation` sysfs on RM11 generation); Nubia SystemMgr resets on `notifyActivityResumed`. RM11 hardware guide (cmfnels) gives fan/LED/micropump sysfs map, applicability to NX789J TBD.
5. **Bootloader-unlock situation is VOLATILE — DO NOT TOUCH DEVICE.** ZTE Family Toolbox free unlock covers RM11 (SM8850); SM8750/RM10 support was in private beta (Apr 2026) with warnings that 11.0.13+ may block unlock and possible eFuse threat. Owner is on 11.0.5MR1 — below the warned version, but NO unlock/flash action without explicit authorization.

## Decisions taken

- Primary strategy remains **Approach A: rebuilt/modified EU REDMAGIC OS** (preserve EU vendor/radio, remove Google from system images). No evidence yet to prefer B/C/D.
- NO device flashing, NO bootloader operations, NO modem/EFS/persist modifications. All work off-device.
- Proprietary firmware NEVER committed to git (`firmware/` gitignored; hashes recorded in `firmware-manifests/`).

## Next actions

1. Wait for EU firmware download → verify size/hash → extract payload → manifests.
2. Write `scripts/` extraction pipeline (payload → super → erofs/ext4 → manifests).
3. Attempt CN package acquisition assessment (HalabTech provenance, hashes); do NOT download untrusted multi-GB blobs blindly.
4. Check Android Dumps GitLab `nubia/nx789j` + ZTE opensource kernel for NX789J.
5. Map RM11 LineageOS/EvolutionX approach for pattern reuse.

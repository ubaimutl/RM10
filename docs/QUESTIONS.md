# QUESTIONS (open, with owner of investigation)

- Q-01 — What is the full upstream chain of the NX789J recovery trees (reminon ← ? ← BigfootACA nx729j?; plompomg convert details; all forks/branches diffed)? Owner: research. Status: OPEN.
- Q-02 — NX789J-native sysfs paths for triggers — RESOLVED (F-19: sar0/sar1 mode_operation). REMAINING: fan/LED/HBM nodes on EU Android 16 build (cross-check post-extraction). Status: PARTLY OPEN.
- Q-05 — RESOLVED: EU build = RedMagicOS11.0.5MR1_EU, fingerprint nubia/NX789J-EEA/NX789J:16/BQ2A.250705.001-BP2A.250605.031.A3/20260519.002456, build date 2026-05-19, SPL 2026-04-01. Matches owner device.
- Q-16 — RESOLVED: FULL OTA (no pre-build in metadata), ota-type=AB, pre-device=NX789J assert. Extraction via payload-dumper-go in progress.
- Q-17 — RESOLVED (F-19).
- Q-03 — Brightness max discrepancy: 2047 (recovery TW_MAX_BRIGHTNESS) vs 4095 (daemon maxBacklight default)? Resolve from stock `panel0-backlight/max_brightness`. Status: OPEN.
- Q-04 — Do Nubia SystemMgr / Game Space / SettingsProvider code paths reference GMS APIs (location/push/auth/integrity)? Owner: Phase 5 (needs stock APK dump). Status: OPEN.
- Q-06 — HalabTech CN listings: exact filenames/sizes/dates/checksums for `GEN_CN_NX789JV1.0.0B24_SD_WO_ERA.zip` + `GEN_CN_NX789JV1.0.0B12MR1_SD_WO_ERA.zip`; are they FOTA-full, EDL, or distributor packages? Owner: research. Status: OPEN.
- Q-07 — What does `_SD_WO_ERA` suffix denote (SD-card sideload, wipe-or-not, ERA region/config)? Compare NX769J FOTA precedent. Status: OPEN.
- Q-08 — Inspect Android Dumps GitLab `nubia/nx789j` (which builds dumped, usability as analysis input)? Status: OPEN.
- Q-09 — Locate NX789J kernel source (ZTE opensource portal) + defconfig; confirm 6.6.92-android15-8 branch? Status: OPEN.
- Q-10 — Owner's exact build fingerprint (read-only `adb shell getprop ro.build.fingerprint`, no modification)? Downloaded EU image IS RedMagicOS11.0.5MR1_EU so match is near-certain; device confirmation still welcome but no longer blocking. Status: ASK OWNER (safe, read-only, optional).
- Q-11 — RM11 LineageOS 23.2/EvolutionX: how do they handle fan/RGB/triggers/fingerprint (stubs vs vendor keep)? Pattern extraction only. Status: OPEN.
- Q-12 — CN vs EU Google-integration delta: does CN product/system contain GMS at all (hypothesis: CN builds ship without GMS)? Needs CN package. Status: BLOCKED on Q-06.
- Q-13 — Which REDMAGIC packages request GMS-only permissions / bind GMS services (Phonesky, GSF, location)? Needs stock dump. Status: BLOCKED on extraction.
- Q-14 — UDFPS event node: stock EU uses /dev/input/event7 (daemon) — stable across builds? Verify via stock uevent/input dump. Status: OPEN.
- Q-15 — Recovery-partition disagreement: wiki says no dedicated recovery (bundled in boot/init_boot) vs two trees + working dd method proving recovery_a/b bootable. Resolve from EU payload (does update.zip contain recovery.img?) + stock fstab. Status: OPEN.

- Q-18 — AOSP donor sourcing: fetch AOSP GSI (phh/LineageOS) + chromium-webview prebuilt; verify hashes, package names, SDK-36 compat, GMS-scan clean. Status: TODO (plan in research/aosp-replacements.md).

- Q-19 — EROFS rebuild: mkfs.erofs available (built); determine fs_config + file_contexts + fsverity/hash-tree strategy for rebuilt system/system_ext/product; vbmeta re-sign flow (test key, flags 0x78). Status: TODO.

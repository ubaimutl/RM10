# QUESTIONS (open, with owner of investigation)

- Q-01 — What is the full upstream chain of the NX789J recovery trees (reminon ← ? ← BigfootACA nx729j?; plompomg convert details; all forks/branches diffed)? Owner: research. Status: OPEN.
- Q-02 — NX789J-native sysfs paths for triggers (`/sys/class/leds/sar0|1/mode_operation` present on stock?) and fan/LED/HBM nodes on EU Android 16 build? Owner: Phase 6 (needs stock extraction). Status: OPEN.
- Q-03 — Brightness max discrepancy: 2047 (recovery TW_MAX_BRIGHTNESS) vs 4095 (daemon maxBacklight default)? Resolve from stock `panel0-backlight/max_brightness`. Status: OPEN.
- Q-04 — Do Nubia SystemMgr / Game Space / SettingsProvider code paths reference GMS APIs (location/push/auth/integrity)? Owner: Phase 5 (needs stock APK dump). Status: OPEN.
- Q-05 — Resolve EU build versioning: page V11.0.05MR1 vs URL V2.0.0B05MR1; record `ro.build.fingerprint`, security patch, payload_properties. Owner: firmware extraction. Status: OPEN.
- Q-06 — HalabTech CN listings: exact filenames/sizes/dates/checksums for `GEN_CN_NX789JV1.0.0B24_SD_WO_ERA.zip` + `GEN_CN_NX789JV1.0.0B12MR1_SD_WO_ERA.zip`; are they FOTA-full, EDL, or distributor packages? Owner: research. Status: OPEN.
- Q-07 — What does `_SD_WO_ERA` suffix denote (SD-card sideload, wipe-or-not, ERA region/config)? Compare NX769J FOTA precedent. Status: OPEN.
- Q-08 — Inspect Android Dumps GitLab `nubia/nx789j` (which builds dumped, usability as analysis input)? Status: OPEN.
- Q-09 — Locate NX789J kernel source (ZTE opensource portal) + defconfig; confirm 6.6.92-android15-8 branch? Status: OPEN.
- Q-10 — Owner's exact build fingerprint + security patch + baseband (read-only `adb shell getprop`, no device modification)? Awaiting owner-provided output. Status: ASK OWNER (safe, read-only).
- Q-11 — RM11 LineageOS 23.2/EvolutionX: how do they handle fan/RGB/triggers/fingerprint (stubs vs vendor keep)? Pattern extraction only. Status: OPEN.
- Q-12 — CN vs EU Google-integration delta: does CN product/system contain GMS at all (hypothesis: CN builds ship without GMS)? Needs CN package. Status: BLOCKED on Q-06.
- Q-13 — Which REDMAGIC packages request GMS-only permissions / bind GMS services (Phonesky, GSF, location)? Needs stock dump. Status: BLOCKED on extraction.
- Q-14 — UDFPS event node: stock EU uses /dev/input/event7 (daemon) — stable across builds? Verify via stock uevent/input dump. Status: OPEN.

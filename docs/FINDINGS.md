# FINDINGS

Conventions: VERIFIED = inspected primary artifact in this repo · STRONG = multiple primary sources agree ·
PLAUSIBLE = single/leak source · SPECULATIVE = inference · DISPROVEN = contradicted by evidence.
Each entry records source + date + relevance (NX789J-native vs sibling).

## F-01 — No native NX789J ROM with Game Space (STRONG, 2026-10-01)

- Claim: no mature LineageOS/crDroid/AOSP ROM for NX789J preserving Game Space + gaming stack.
- Evidence: fresh web search 2026-10-01; XDA RM10 thread (Sep 2025, Danish user) lists GSI breakage (SIM, UDC camera, triggers); only root-module fixes (sequencode) and recoveries found; RM11 has unofficial LineageOS 23.2/EvolutionX 11.9 but those are NX809J, not flashable to NX789J.
- Relevance: NX789J-native (absence of evidence after directed search). Confidence: STRONG (not proof).

## F-02 — OrangeFox NX789J tree is active and informative (VERIFIED, 2026-10-01)

- Source: `sources/rm10pro-orangefox-recovery`, branch main, HEAD 2026-09-30 (cloned 2026-10-01).
- Verified contents: BoardConfig.mk (sun/sm8750, A/B, dynamic partitions 17,179,869,184 B super, recovery_a/b, FBE policy 2, wrappedkey), recovery.fstab (full partition map incl. metadata/userdata FBE-ICE flags, persist, modem→/firmware vfat), init.recovery.qcom.rc (ADSP SSR load, `write /sys/kernel/fan/fan_enable 1`, `fan_speed_level 1`, `aw22xxx_led trigger battery-charging-or-full`), TW_INPUT_BLACKLIST naming `nubia_tgk_aw_sar0_ch0`, `nubia_tgk_aw_sar1_ch0` (trigger input devices), touch modules `zte_tpd.ko panel_event_notifier.ko aw9620x.ko`, brightness path `panel0-backlight` max 2047 (recovery) vs 4095 (stock daemon — discrepancy noted, Q-03).
- Flashing constraint (from README): NO `fastboot boot`/`fastboot flash recovery`; install via `dd` to recovery_a+b from rooted Android or running recovery.
- Relevance: NX789J-native.

## F-03 — TWRP NX789J tree confirms + extends OrangeFox data (VERIFIED, 2026-10-01)

- Source: `sources/twrp_device_nubia_nx789j`, branch twrp-16.0, HEAD 2026-03-12 (cloned 2026-10-01).
- Feature status: ADB/decrypt/display/fastbootd/flash/MTP/fan/USB-OTG working; fan LED + vibrator WIP.
- Git history shows touch bring-up method: Goodix libs + `ztethp` service, vendor dir overlay from `/data/vendor` (encrypted-at-boot chicken-and-egg), input blacklist to fix tap lag, battery path `zte_battery`.
- Upstream derivation: README points at TWRP-Test manifest; XDA credits Xiaomi-base stripping + Claude-assisted touch fix. Full upstream chain not yet mapped (see Q-01).

## F-04 — ZTE fingerprint extension protocol fully recovered (VERIFIED, 2026-10-01)

- Source: decompiled `sources/redmagic-10-pro-udfps-fix/bin/ZteFodDaemon.dex` (jadx) → `research/udfps-zte-protocol.md`.
- Binder service `android.hardware.biometrics.fingerprint.IFingerprint/default` → `getExtension()` → `vendor.zte.fingerprint.ztecmdaidl.IZtecmdDaemon`; callback iface `...IZtecmdCallback`; TXN setNotify=1, zteCmd=2(cmd, a1, a2, "").
- Capture sequence: wake `zteCmd(10,1,0)` + `zteCmd(21,1,0)`; loop `zteCmd(22,1,0)`/330ms/`zteCmd(22,0,0)`/check/`zteCmd(10,0,0)`/90ms/`zteCmd(10,1,0)`/`zteCmd(21,1,0)`/60ms.
- Finger presence from `/dev/input/event7` (ABS_MT_POSITION_X=53/Y=54, BTN_TOUCH=330, BTN_TOOL_FINGER=325); FOD geometry center (608,2024) r=95 px on 1216×2688; abs-max 19455×43007.
- Illumination: `/proc/driver/lcd_hbm` + trusted overlay SurfaceControl "ZteFodLight" (top layer, dim mask adaptive to `panel0-backlight/brightness`, white circle over sensor); 60 Hz refresh lock during scan via `peak_refresh_rate/min_refresh_rate`.
- HAL-death recovery via watchdog re-acquire; overlay presence detected via `dumpsys SurfaceFlinger --list | grep UdfpsControllerOverlay`.
- Value: documents exactly what a proper ROM must integrate natively (framework UDFPS trigger + vendor extension + HBM + overlay) instead of a root daemon.
- Relevance: NX789J-native (event node index may vary per build; verify against stock).

## F-05 — Shoulder-trigger stack mapped (STRONG, 2026-10-01)

- Sources: RedTrigger (`sources/RedTrigger`, incl. CLAUDE.md) + RM11 hardware guide (`sources/RM-11-Pro-Hardware-Mapping/README.md`) + TW_INPUT_BLACKLIST (F-02).
- Chain: SAR capacitive sensors (`nubia_tgk_aw_sar`, SAR0→KEY_F7/137, SAR1→KEY_F8/138, RM11 events event4/5) → enable via Settings.Global `nubia_game_scene=1` (+ RM11 sysfs `/sys/class/leds/sar0|sar1/mode_operation`; NX789J sysfs path UNVERIFIED — Q-02) → Nubia SystemMgr converts F7/F8 to screen taps in Game Space; SystemMgr resets `nubia_game_scene` on every `notifyActivityResumed` (hence RedTrigger watchdog).
- Related settings: `nubia_game_mode`, `cc_game_mis_operate=0` (gesture blocking), `virtual_game_key` must NOT be set (hijacks launcher), `fourth_physical_key_function_value` (slider, RM11).
- Implication for Google-free ROM: trigger path appears ZTE-framework-local (no GMS in chain so far — must confirm via stock SettingsProvider/SystemMgr dependency scan in Phase 5, Q-04).
- Relevance: trigger core NX789J-native; sysfs details partly sibling (RM11).

## F-06 — Fan / LED / micropump sysfs map (PLAUSIBLE for NX789J, VERIFIED for RM11)

- RM11 (cmfnels, VERIFIED in repo): `/sys/kernel/fan/{fan_enable,fan_speed_level 0-5,fan_speed_pwm 0-255,fan_speed_count RPM}`, `/proc/driver/micropump/enable` (or `settings put system liquid_cooling_off_on 1`), `aw22xxx_led/{effect,cfg,rgb}`, haptics `/sys/class/leds/zte_vibrator/{duration,gain,activate}`.
- NX789J-native corroboration (STRONG for fan): OrangeFox init writes `/sys/kernel/fan/fan_enable` + `fan_speed_level` and sets `aw22xxx_led/trigger`; DeviceInfoHW lists `aw22xxx_led aw9620x_sar` on NX789J; thermal path `thermal_zone1` (TWRP) vs zones 5/8/12 (RM11) — differ, verify on stock.
- Relevance: mixed; NX789J verification needed during Phase 6.

## F-07 — GSI audio shims document vendor audio dependencies (VERIFIED, 2026-10-01)

- BT A2DP fix: GSI `sysbta` HAL squats A2DP slot blocking offload; fix = stop sysbta, force `ro.bluetooth.a2dp_offload.supported=true`, `bluetooth.a2dp.offload.enabled=true`, `persist.bluetooth.a2dp_offload.disabled=false`, `persist.bluetooth.system_audio_hal.enabled=false`, restart vendor.audio-hal-aidl + audioserver, cycle adapter. Watchdog design (max 2 repairs/connection).
- Call fix: GSI lacks `IHalAdapterVendorExtension` AIDL service; module ships registrar (`audiohalext_registrar` + `libaudiohalvendorextn.so`) + SELinux rule for audioserver.
- Value for ROM design: these are EXACTLY the vendor services a rebuilt REDMAGIC OS keeps automatically (approach A advantage over GSI/AOSP-base). Documents what approach C/D would need to reimplement.
- Relevance: NX789J-native.

## F-08 — EU target firmware identified, official, downloading (VERIFIED, 2026-10-01)

- `https://rom.download.nubia.com/Europe/NX789J/V2.0.0B05MR1/update.zip` — HTTP 200, 8,733,027,332 B, Last-Modified 2026-07-09, Tencent COS. Page label V11.0.05MR1 (matches owner's 11.0.5MR1 EU modulo naming). NOTE page-URL version mismatch: path says V2.0.0B05MR1 (internal REDMAGIC OS 11 versioning?) — resolve from payload properties after extraction (Q-05).
- Global sibling: `.../Europe&Asia/NX789J/V2.0.0B05MR/update.zip` (not yet fetched).
- Older: `GEN_NEEA_NX789JV1.0.0B13MR1` (V10.0.13, Android 15), `GEN_EEA_NX789JV1.0.0B10MR1`, V10.0.8/9 EU, `GEN_EEA_NX789SV2.0.0B04MR1` (Mar 2026, A16).
- Relevance: NX789J-native.

## F-09 — CN firmware leads exist but provenance is weak (PLAUSIBLE, 2026-10-01)

- `GEN_CN_NX789JV1.0.0B12MR1_SD_WO_ERA` ← Baidu Pan link only (romprovider, Apr 2025). `GEN_CN_NX789JV1.0.0B24_SD_WO_ERA` ← HalabTech listing (per brief; page not yet directly inspected — Q-06).
- `_SD_WO_ERA` suffix pattern matches ZTE FOTA full packages (cf. NX769J precedent, szescxz FOTA repo + SourceForge). Meaning of ERA qualifier unknown (Q-07).
- Suitability for EU hardware UNVERIFIED; cross-flash modem warning (F-10) applies. Do not download blindly.

## F-10 — CN-on-global modem breakage report (PLAUSIBLE, single report, 2026-07-31)

- Reddit r/RedMagic: global NX789J vendor-flashed to CN, Android 15 OK → Android 16 OTA → network drops, missing LTE bands, VoLTE failure; REDMAGIC support confirmed HW=global/FW=CN mismatch.
- Treat as cautionary single data point, not universal proof. Design consequence: preserve EU modem/radio/carrier/DSP/EFS/persist/NV; never overwrite with CN equivalents without evidence (drives approach-A preference).
- Relevance: NX789J-native (one device).

## F-11 — Unlock/EDL landscape volatile; device risk elevated (STRONG, 2026-10-01)

- ZTE Family Toolbox (SYXZ) free unlock: RM11/SM8850 supported; SM8750/RM10 in private beta Apr 2026, "DO NOT UPDATE to 11.0.13+" warnings + eFuse-theft concerns voiced by community (XDA thread 4780930). Owner on 11.0.5MR1 (below warned rev) — still, NO action authorized.
- EDL path exists (bkerler/edl, devprg.melf ~1.6 MB, LUN4 GPT map with vbmeta_b/init_boot_b sectors documented in XDA EDL-root guide, Feb 2025) but used only for research reference, never on owner device without authorization.
- Paid unlock/flash culture + password-locked EDL zips (sarhanroots, romprovider "pro help") = untrusted; never run closed flashing tools on host without analysis.
- Relevance: NX789J-native.

## F-12 — RM11 custom-ROM work is a pattern reference only (STRONG, 2026-10-01)

- Unofficial LineageOS 23.2 + EvolutionX 11.9 for NX809J (XDA, Jul–Aug 2026); RM11 TWRP tree (cmfnels) documents sun-platform details (super 19.3 GB, KeyMint SPU, Synaptics TCM via zte_tpd, wrappedkey_v0 FBE) useful for comparing generations.
- NEVER flash RM11 binaries to NX789J. Port concepts after NX789J-stock verification.
- Relevance: sibling (NX809J).

## F-14 — IronShing LOS 23.2 hybrid tree: approach-C reference, NOT our architecture (VERIFIED, 2026-10-01)

- Source: `sources/android_device_nubia_NX789J`, branch lineage-23.2, single commit 9b1b3df (2026-09-13).
- Design: builds system/system_ext/product from LineageOS 23.2, rides STOCK RMOS 11.0.13MR vendor/odm/dlkm + stock boot chain (6.6.92 GKI); hybrid super assembled at flash time; EDL flash. Status = bring-up/bootstrap only (diag logger, wifi glue) — no working triggers/Game Space/fingerprint.
- Stock facts reused: vendor is Android 15 / board API 202404 GRF-frozen while system is Android 16 (same seam LOS 23.2 needs); stock ships **EROFS** on all 7 logical partitions; vendor security patch 2026-05-01; super 16 GiB; recovery 100 MB block device; codename **aston**; CN variant **NX789S (overclocked)**; cameras OV16E1Q(UDC)/OV50E40/OV50D40/OV02F10; Goodix gf96xx; ZTE kernel tree has J/S config select; kernel source opensource.ztedevices.com → NX789S tarball (6.6.30, Kleaf/Bazel, ~2 GB); upstream base LOS oneplus/sm8750-common + dodge.
- Consequence for us: validates vendor seam + EROFS + partition sizes for our work; confirms NO working native ROM preserves the REDMAGIC stack (approach C/D would need to reimplement Game Space/triggers/UDFPS-HBM from F-04/F-05) → strengthens approach-A preference.
- Relevance: NX789J-native (bring-up, unverified boot).

## F-15 — Nubia OTAs are DELTA payloads; J vs S hardware split (STRONG, wiki + trees, 2026-10-01)

- Wiki rom-firmware: update.zips (~4 GB class) are incremental binary patches requiring the exact predecessor; local-install fails at payload_properties (~16 KB) otherwise; fresh-state flashing needs extracting/patching ~42 partitions. OUR EU download is 8.73 GB — larger; full-vs-delta to be determined from payload_properties after download (extraction may need source partitions if delta — risk for Phase 3, mitigated by payload-dumper-go + lpunpack already staged).
- Region/variant: EU/Global/EEA/Asia share NX789J; CN targets NX789S (overclocked SoC bin). Same kernel tree, config-selected. HalabTech "GEN_CN_NX789J" filenames therefore need extra scrutiny (Q-06): CN packages may actually be NX789S-targeted despite the name.
- Official EU full-version URL table captured (V1.0.0B10MR1 … V10.0.14, plus our V2.0.0B05MR1) — see SOURCES FW-01…FW-06.
- Relevance: NX789J-native.

## F-16 — Free RM10 unlock exists since May 2026, but no RM10 version matrix (STRONG, wiki 2026-08-29 + XDA, 2026-10-01)

- Toolbox 1.2.3+ → 1.2.4 (May 2 first free RM10 unlocks) → 1.2.7.7 stable → 1.2.8-beta2; native-Linux bkerler/edl port WIP ("do not use yet"); GhostLock CVE-2026-43499 temp-root supports RM10 shipping kernel.
- No published RM10 firmware↔unlock-compatibility matrix ("has to be an older version" — dev-reverse). RM11 matrix (11.0.18MR1_GB last fully-working incl. fingerprint fix; GBL patched in .19MR2; Aug-2026 abl+efisp downgrade bypass) is SIBLING-ONLY.
- EDL/firehose is the only write path (no working fastboot on stock); losing EDL access = losing all flashing/root — test plan must treat EDL availability as precondition.
- Owner device: NO action. Owner advisory (separate message): do not update, consider freezing updater.
- Relevance: NX789J-native (procedure), sibling (matrix).

## F-17 — Internal wiki contradiction on efisp/recovery (VERIFIED disagreement, 2026-10-01)

- partitions-avb.md: NX789J (SM8750) has NO efisp partition (121-entry by-name dump from 11.0.4MR1_GB lists ztecfg/uefi/uefivarstore, no efisp) → RM11 efisp procedures (Option 18, abl+efisp downgrade) do NOT port verbatim.
- reverse-engineering.md (same wiki): "both share the efisp partition and ABL behavior… mechanism ports". CONFLICT preserved; partitions-avb has the stronger evidence (device dump). Do not assume efisp on NX789J.
- Similarly: partitions-avb says recovery bundled into boot/init_boot (no dedicated recovery), but TWO independent trees (OrangeFox + IronShing BoardConfig: recovery 104857600) + working dd-to-recovery_a/b flash method prove the recovery_a/b block devices exist and boot. Likely: partition exists, stock boot flow ignores it. Preserved as Q-15.
- Relevance: NX789J-native.

## F-18 — Vendor gaming stack lives in vendor/ (STRONG, stock blob list, 2026-10-01)

- Source: `research/vendor-blob-signals.md` filtered from reminon/device_NX789J proprietary-files.txt (base: RedMagicOS10.0.15_NX789J_GB A15 vendor).
- `vendor/bin/fan_service` + init_fan_service.rc; `poweropt-service` + libgamepoweroptfeature/liboffscreenpoweroptfeature; aw_fan0-4 + fan_led/m_led/touch_led/aw22xxx firmware; nubia_all_rgb_* blobs; AAC Richtap haptics (odm config); `ztecmdaidl-service` + ifaaaidl-service + Goodix gf95xx HAL/libs/firmware; KeyMint/Gatekeeper SPU; consumerir.zte; zte radio/modem/subsys vendor libs; init.zte.perf.rc; touchscreen_zte.rc; multi-panel display calibs (CSOT nt37801 + Visionox r66451/vtdr6130).
- Consequence: approach A (keep vendor/odm) inherits fan/power/RGB/haptics/fingerprint/IR/radio daemons automatically — the core argument for A over C/D. System-side REDMAGIC APKs (Game Space) + their GMS edges remain Phase 5 work.
- Relevance: NX789J-native (A15 GB vendor; re-verify on EU A16 after extraction).

## F-13 — Stock dump mirrors + kernel source located (STRONG, 2026-10-01)

- dumps.tadiphone.dev/dumps/nubia/nx789j (Android Dumps GitLab) exists but predates 10.0.18 and looks incomplete (wiki rom-firmware, first-hand report). Not yet inspected (Q-08).
- Kernel source: opensource.ztedevices.com → NX789S tarball (Linux 6.6.30, Kleaf, ~2 GB, J+S configs). RM10 tree buildable per wiki (2026-08-09 check); reminon kernel GitHub repos are EMPTY (manifest only) — do not use. Tarball fetch deferred until needed for driver/sysfs reference (Q-09).

## F-19 — mKonic userspace HW-control app confirms NX789J sysfs (VERIFIED, 2026-10-01)

- Source: `sources/Redmagic-Control-Center` (mKonic fork, RM10-targeted; strings extracted from Kotlin sources 2026-10-01).
- NX789J-native nodes: fan `/sys/kernel/fan/{fan_enable,fan_speed_level,fan_speed_pwm,fan_speed_count}`; triggers `/sys/class/leds/sar0|sar1/mode_operation` + input devices `nubia_tgk_aw_sar0_ch0/1_ch0` (resolves Q-02 trigger-sysfs half); LEDs `aw22xxx_led/{effect,cfg}`; micropump `/proc/driver/micropump/{enable,freq,speed,mode}`; slider `/proc/driver/slider`; vibrator `/sys/class/leds/vibrator/*`; thermal zones 0-3.
- No charge-separation/bypass node found in this app — remains Phase 6 stock-vendor work.
- Relevance: NX789J-native (app targets RM10; stock-image cross-check still required).

## F-20 — Phase 5 static verdict: REDMAGIC stack is GMS-clean; GMS is bounded (VERIFIED, 2026-10-01)

- Method: aapt/apksigner inventory (574 APKs) + strict descriptor-level dex scan (scripts/20-gms-scan.py) over 104 ZTE/Nubia/RedMagic APKs + permission/allowlist/sysconfig/init review.
- Privileged Google core = 26 APKs (GmsCore+sidecar, GSF, Phonesky, Google SUW, PartnerSetup, OneTimeInitializer, ConfigUpdater, Velvet, ASI/PCS, Dialer, Messages, Turbo, Wellbeing, etc.) + NetworkStack/DocumentsUI/PackageInstaller/Tag (need AOSP swaps) + ~53 Google apps + ~15 overlays. No GMS init services; framework sysconfig Google-free; Mainline APEX stay.
- Gaming/hardware REDMAGIC packages show ZERO GMS class refs and ZERO Google permissions: GameSpace, GamePi, KeyMapCenter, NBFan, ChargeSeparation, ColorFulLight, GameFloat, PluginTrigger, ProjectionScreen, VirtualGameHandle, Thermal×2, PowerSaveMode, FingerprintService, SetupWizard_MFV (uses GSETTINGS perms — graceful unknown-perm post-GSF), SystemUI/Launcher/Telecom/SettingsProvider/Camera/ServiceManager.
- Dirty exceptions: ZBoard (heavy — replace), NBBrowser/Weather/Cleanup/Booking (remove), Wallpapers/PhotoEditor (remove/test), GameAssist (sign-in+MLKit — test), Settings_MFV (sign-in+FLP client lib — test), ZteAigc (sign-in — test), XRLauncher (play-asset — test).
- Artifacts: package-analysis/EU-google-removal-list.md, EU-redmagic-survival-list.md, EU-redmagic-gms-scan.tsv; docs/ARCHITECTURE.md recommends Approach A.
- Relevance: NX789J-native, owner-build exact. Runtime confirmation still required (static ≠ proof of no crash-loop).

## F-21 — Candidate v1 BUILT: 4 EROFS images + test-key AVB chain (VERIFIED, 2026-10-01)

- Images (firmware-manifests/CANDIDATE-v1-signed.sha256): system 5,565,849,600 B
  (lz4), system_ext 737,755,136 B (zstd), product 1,992,269,824 B (lz4),
  vendor 1,774,276,608 B (zstd) — every image EXACTLY its stock super-slot
  size; total candidate ~8.6 GB vs stock ~10.5 GB (more super headroom).
- Content: 105 removals (79 Google + 26 zte-replace/config), 10 additions
  (9 AOSP transplants from SHA-verified Google GSI BP2A.250605.031.A3 +
  derived allowlist XML), 2 ZTE allowlist patches (byte-exact verified).
- Labels: full census vs stock — 0 mismatches on all 4 partitions
  (original xattrs preserved via FUSE reads + tar pax headers; 23 new files
  labeled system_file via specificity-sorted file_contexts eval, matching
  removed counterparts' stock labels).
- Verification: 50-verify 11740 identical / 0 failures; APK inventory 495
  (0 google-packaged; 88 removed / 9 added reconciled); GMS scans match
  stock verdicts; transplants GMS-clean (WebView carries standard Chromium
  client stubs only); validator gates green; all 4 fsck rc=0; all 4
  hashtree footers verify_image-clean.
- AVB: fresh salts recorded; vbmeta_system re-signed RSA2048 test key
  (rollback 1775001600 = stock, flags 0); top vbmeta RSA4096 test key
  (rollback 0, flags 0; 3 chains + 7 hashes, vendor descriptor points at
  rebuilt vendor). No-FEC footers (fec binary absent on host; coherent
  with flags-3 disable-verification flash procedure).
- Untouched: boot/init_boot/vendor_boot/dtbo/recovery/odm/dlkm/modem/dsp/
  bluetooth/all firmware/modem/EFS/persist (hashes recorded; low-level
  firmware never written by any pipeline step).
- Virtual boot: BLOCKED (research/virtualization-blockers.md) — CHD needs
  AOSP target-files + ARM host + 100 GB build; Cuttlefish/QEMU/Emulator
  rejected with concrete grounds. Deepest off-device signal applied instead.

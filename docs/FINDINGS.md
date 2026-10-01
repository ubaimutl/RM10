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

## F-13 — Stock dump mirrors exist for static analysis (PLAUSIBLE, 2026-10-01)

- Android Dumps GitLab `nubia/nx789j` referenced from XDA (qssi_64-user-15-...RedMagicOS10.0.15_NX789J_GB). Not yet inspected (Q-08).
- ZTE opensource portal hosts kernel tarballs (NX769J precedent); NX789J kernel source not yet located (Q-09).

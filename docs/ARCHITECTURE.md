# Architecture recommendation (interim, evidence-backed, 2026-10-01)

## Recommendation: Approach A — rebuilt EU REDMAGIC OS (modified stock)

Rebuild `system / system_ext / product` from the pristine EU 11.0.5MR1 full OTA
(fingerprint nubia/NX789J-EEA/NX789J:16/BQ2A.250705.001-BP2A.250605.031.A3/20260519.002456),
removing the Google stack per package-analysis/EU-google-removal-list.md and
substituting AOSP equivalents, while keeping:

- ALL of vendor / odm / vendor_dlkm / system_dlkm (fan_service, poweropt, ztecmdaidl, Goodix, radio, IR, haptics, display calibs)
- ALL REDMAGIC system packages per package-analysis/EU-redmagic-survival-list.md
- stock boot chain (boot, init_boot, vendor_boot, dtbo) + stock modem/radio/EFS/persist untouched
- vbmeta re-signing strategy: test-key vbmeta_system + flags patch per wiki §vbmeta-header-flag-byte (offset 0x78, big-endian), unlocked bootloader required for flashing

## Why A wins (evidence)

1. **Vendor gaming stack is indivisible from vendor/** (F-18): fan_service, poweropt-service, ztecmdaidl-service, Goodix HAL+firmware, aw_fan*/RGB firmware, Richtap haptics, ZTE radio libs all live in vendor/odm with init rc + VINTF manifests. Approaches C/D would reimplement all of it; A inherits it.
2. **REDMAGIC system layer is GMS-clean** (Phase 5 scan): GameSpace, GamePi, KeyMapCenter, NBFan, ChargeSeparation, ColorFulLight, GameFloat, PluginTrigger, SystemUI_MFV, Launcher, Telecom, SettingsProvider, NubiaCamera, FingerprintService, SetupWizard_MFV, ProjectionScreen, VirtualGameHandle — zero GMS class refs, zero Google permissions. Removing GMS does not pull the rug from under them (static verdict; runtime confirmation still required).
3. **GMS contamination is bounded and replaceable**: 26 privileged Google APKs + ~53 Google apps + ~15 overlays + permission XMLs, with a known AOSP substitution set (WebView/NetworkStack/DocumentsUI/PackageInstaller/Tag/CaptivePortalLogin/Dialer/SMS/keyboard). No GMS init services exist; framework sysconfig is Google-free.
4. **Dirty REDMAGIC apps are non-critical**: ZBoard/NBBrowser/Weather/Cleanup/Booking are replaceable; GameAssist/Settings/ZteAigc/XRLauncher use guarded client-library patterns (sign-in/FLP/play-asset) expected to fail safe — runtime test will confirm, removal fallback exists for the non-privileged ones.
5. **Full OTA input, exact owner build**: 8.73 GB official EU image IS RedMagicOS11.0.5MR1_EU (owner's build) — no version skew, no delta-payload problem, pre-device=NX789J assert satisfied.
6. **Sibling approaches confirm the seam**: IronShing LOS tree proves system/vendor GRF seam (A16 system on A15-frozen vendor) and EROFS layout; wiki documents AVB patching + EDL-only write path constraints the test plan must respect.

## Why not B (EU + CN components)

- CN packages (GEN_CN_NX789J*) have unverified provenance (Baidu/HalabTech), target the NX789S variant (overclocked bin), and carry the F-10 modem-breakage risk. No evidence CN system is cleaner; EU already analyzes clean. B is fallback only if EU proves unworkable.

## Why not C/D (AOSP base / native port) first

- Would discard the working ZTE telephony/audio/camera/fingerprint/vendor stack and Game Space itself — maximum undocumented replacement work, directly against the selection criterion. Revisit only if A hits a hard blocker (e.g., Settings_MFV boot-dependency on GMS at runtime).

## Risks to retire before build (ordered)

1. R-06 (GMS crash-loops): static says guarded; RUNTIME test on unlocked device required before calling A viable. Smallest experiment: disable (not remove) GMS core via DSU/side-slot and observe — still needs unlock + authorization.
2. WebView replacement sourcing: need AOSP WebView Trichrome build compatible with SDK 36 + MFV framework-res. Investigate LineageOS/vendor_google alternatives (open-source builds only).
3. vbmeta re-sign + EROFS rebuild tooling: mkfs.erofs available (built); AVB test keys; partition size budget (super 16 GiB; stock slot-A ~8.8 GB leaves headroom).
4. Updater/OTAP paths: OTAP_stockplus + care_map reference stock partitions — rebuilt images must either preserve updateability story (document: no OTAs) or neutralize MountainView updater references.
5. privapp allowlist/SELinux/VINTF consistency after removal: automated check (Phase 9) comparing pre/post manifests.

## Next engineering steps

1. Set up GMS-off staging: copy of extracted trees with removal list applied (script-driven, reversible, manifest-diffed).
2. Build EROFS rebuild + vbmeta re-sign pipeline (Phase 8 scripts).
3. Static validation suite (Phase 9): avbtool verify, allowlist cross-check, init-rc service check, overlay-target check, apex consistency, size budget.
4. Safe hardware test plan for owner review (Phase 10) — NO execution without explicit authorization.

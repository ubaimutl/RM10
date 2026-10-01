# CHD/Cuttlefish/QEMU/Emulator — virtualization blocker analysis (2026-10-01)

Verdict for each method: GO or BLOCKED with concrete technical grounds.
Host: x86_64, /dev/kvm present, 8 CPUs, ~6 GB RAM avail, 23 GB disk free.

## 1. Cuttlefish Hybrid Device (CHD) — BLOCKED (3 independent grounds)

Source: source.android.com/docs/devices/cuttlefish/create-chd (2026-09-22).

How CHD works: `build_cf_hybrid_device.py` merges TWO `make dist`
target-files zips (Cuttlefish vendor target + physical-device target) via
`merge_target_files.py`, then `img_from_target_files` generates bootable
images. The physical device's system.img runs on Cuttlefish (vsoc) vendor/HALs.

- BLOCKER A (fatal): No AOSP target-files exist for NX789J. CHD requires
  `make dist` output for the physical device — i.e., a full AOSP build tree
  for REDMAGIC OS, which does not exist (proprietary ZTE build system, no
  device tree, no vendor makefiles). Cannot be worked around without
  reimplementing the entire OS build (approach C/D scope, months).
- BLOCKER B (fatal): Architecture. CHD instances matching an ARM64 system
  image require an ARM host ("server's CPU should have an ARM architecture
  equal to or higher"; Cuttlefish team runs ARM servers for CHD). Host is
  x86_64. ARM64-on-x86_64 has no KVM path (crosvm cannot translate ISA);
  TCG emulation of a full Android boot is orders of magnitude too slow and
  was not attempted (documented impractical, not merely slow).
- BLOCKER C (fatal): Resources. The Cuttlefish vendor side alone requires a
  full AOSP source checkout + build (100+ GB source, hours of build, 16+ GB
  RAM recommended). Host has 23 GB free. Not feasible.
- SIGNAL PROBLEM (even if built): REDMAGIC system on vsoc vendor would fail
  on missing ZTE HALs (ztecmdaidl, poweropt, fan_service, Goodix, ZTE radio).
  Every crash would need triage as artifact-vs-real. The test would measure
  the Frankenstein, not the candidate.

Per instruction not to force CHD: documented, moving on.

## 2. Stock Cuttlefish (x86_64 + transplant REDMAGIC portions) — BLOCKED

- Same host-arch problem in reverse: candidate binaries are ARM64
  (native daemons, APEX payloads, APK .so files). x86_64 Cuttlefish cannot
  execute them (no ARM translation in Cuttlefish guest; NDK translation
  exists only in the user-app path of the official Emulator, not for
  system components).
- Transplanting REDMAGIC priv-apps onto Cuttlefish AOSP requires the ZTE
  framework (framework-zte-res, nubia/zte system services, custom
  permissions) which only exists inside the candidate system — circular:
  transplanting the framework means transplanting the whole system image,
  which is back to CHD (blocked above).
- Booting Cuttlefish itself was NOT attempted: it would test Google's
  Cuttlefish, contributing zero signal about the candidate. Rejected as
  signal-free, not merely hard.

## 3. QEMU ARM64 full-system emulation of the candidate — BLOCKED (assessed, not attempted)

- The candidate's boot chain (boot.img, vendor_boot, dtbo, vbmeta) is built
  for the sun SoC (sun DTB, sun drivers, ZTE bootloader flow). QEMU `virt`
  needs a virt-compatible GKI kernel + crafted ramdisk + virtio storage/GPU
  plumbing — a from-scratch Frankenstein boot requiring a custom first-stage
  ramdisk, EROFS-on-virtio validation, and stub vendor services.
- Estimated effort: days; failure modes would be ~entirely Frankenstein
  artifacts (wrong kernel/drivers/SELinux policy load/vendor absence),
  indistinguishable from real candidate defects without sun hardware to
  calibrate against.
- Rejected per the no-excessive-forcing instruction. Revisit only if a
  sun-capable virtual platform appears.

## 4. Android Emulator (official, x86_64) + REDMAGIC APKs — REJECTED (signal-free)

- Emulator user-space ARM translation does not extend to privileged system
  components; REDMAGIC priv-apps hard-require ZTE framework services and
  signature-level permissions absent from the Emulator image. Expected
  outcome (install/boot crashes) is predetermined and reveals nothing about
  candidate bootability on NX789J hardware.

## What IS executed instead (signal-bearing, host-runnable)

1. Full candidate image build (EROFS rebuild + transplants + patches).
2. Re-extraction + byte-level intent verification.
3. Re-run of the complete audit battery on FINAL images (Google scan,
   REDMAGIC scan, inventory, manifests).
4. Extended static validation: framework-JAR refs to removed packages,
   WebView-provider config, role-holder defaults, privapp allowlists,
   VINTF/apex/init/symlink/xattr/permission/SELinux-label coverage,
   partition size budgets, AVB descriptor regeneration + verification.
5. Component-level dynamic checks that run on host: aapt full-parse of
   every candidate APK, dexdump verification, XML well-formedness +
   init-rc strict parse, EROFS fsck, avbtool verify.

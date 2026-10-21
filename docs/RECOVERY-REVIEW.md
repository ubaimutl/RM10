# Published OrangeFox image: offline review

Reviewed on 19 October 2026. These are measurements of a public recovery
artifact and the pinned EU firmware inputs, not a phone test.

Follow-up on 21 October: source HEAD is now
`a2e8ac30dbe28df75e1e7ae25e05e0619b86ee31`; README and BoardConfig are
unchanged from the previous inspection and the latest published image is
still the same June artifact. Extracting the pinned **stock** recovery
ramdisk also finds ext4 declarations for dynamic images that are EROFS.
Consequently that textual mismatch alone is not evidence that OrangeFox is
less compatible than stock; actual behavior still needs validation.
Additional OTA signature, snapshot-fallback and restore-tool findings are in
[OFFLINE-TEST-PATH.md](OFFLINE-TEST-PATH.md).

## Artifact identity

- Project: [plompomg/rm10pro-orangefox-recovery](https://github.com/plompomg/rm10pro-orangefox-recovery).
- Published release: [5 June 2026 UTC, tag release](https://github.com/plompomg/rm10pro-orangefox-recovery/releases/tag/release).
- File: recovery.img, 104,857,600 bytes.
- SHA-256: `1d98db121bc30b680e0392483a1040b7661b5ccd94c0fadd96502ac5e19e7bfc`.

The download matched the GitHub asset size and digest. Source HEAD advanced
to `7b1489cf1f9edb60b3c5035e7cd4f5a7d1253ee5` on 18 October UTC, but that
does not make the June binary a build of the newer source.

## Binary observations

`avbtool info_image` and host boot-image unpacking report:

- Android boot header v4, kernel size 0, ramdisk size 56,846,906 bytes and no
  boot signature. A kernel-free image depends on other boot components.
- AVB algorithm **NONE**, rollback index **0**, flags **0**. It is not signed
  with the ZTE key expected by the stock recovery chain descriptor.
- The pinned stock recovery image has rollback index 1. Stored device
  minima were not established, so acceptance of the release's lower value
  must not be assumed even if another verification-policy issue is addressed.
- Recovery fingerprint `nubia/NX789J-UN/NX789J:15/AQ3A.240812.002/RedMagicOS10.0.15_NX789J_GB:user/release-keys`.
- Boot OS version property 99.87.36 and patch property 2099-12-31. The patch
  date alone does not establish a high AVB rollback index: the actual footer
  index is zero. OEM acceptance and persistent-state behavior remain untested.

Replacing recovery with this image in an otherwise stock assembled host set
causes full-chain verification to fail at recovery's public-key comparison.
This establishes incompatibility with that verification chain. It does not
prove that no unlocked boot flow could ever load the image.

## Ramdisk configuration

The LZ4 ramdisk was decompressed and its CPIO read as data without installing
or running its contents. The embedded `system/etc/recovery.fstab`:

- Declares system, system_ext, product, vendor, ODM and vendor_dlkm as ext4;
  the pinned EU 11.0.5MR1 source images use EROFS.
- Includes odm_dlkm and omits system_dlkm; the EU payload has system_dlkm
  and no odm_dlkm image.
- Uses unsuffixed physical boot/recovery device names without explicit slot
  selection on those entries. Recovery's actual A/B name-resolution behavior
  therefore needs validation.
- Includes shared metadata, userdata and persist mount entries. Their
  presence is not proof of writes during every boot, but recovery behavior
  must be audited rather than assumed confined to an inactive slot.

These differences are compatibility concerns, not a demonstrated boot or
restore failure. Automatic filesystem detection or recovery-specific code
could affect behavior; no matching-firmware hardware evidence was obtained.

## What would establish a recovery route

The project's installation instructions write both recovery copies using
root or an already running custom recovery and say fastboot boot/flash
recovery are unsupported. No installation was attempted here. That route
cannot be treated as an already available fallback on a stock setup.

Before relying on this recovery, validate the exact binary's boot entry,
kernel/firmware dependencies, AVB and rollback policy, EROFS/slot behavior,
decryption and a complete stock restore on matching EU firmware, preferably
using a spare device. Any changed recovery chain or additional partition
writes need a separate reviewed plan. The runtime feature table in the
upstream README does not establish those conditions for this project.

Hardware testing remains blocked by [TEST-PLAN-DRAFT.md](TEST-PLAN-DRAFT.md).

# AVB / Verified Boot analysis for the candidate (2026-10-01)

Measured on the pristine EU 11.0.5MR1 images with avbtool (host).

## Stock chain

- `vbmeta` (SHA256_RSA4096, ZTE key sha1 c0b5900a…, flags 0, rollback 0):
  - CHAIN boot (rollback loc 3), recovery (loc 1), vbmeta_system (loc 2, key sha1 4c630744…, RSA2048)
  - HASH descriptors: dtbo, init_boot, vendor_boot, odm, system_dlkm, vendor, vendor_dlkm
- `vbmeta_system` (SHA256_RSA2048, flags 0, rollback index 1775001600):
  - HASH descriptors: pvmfw, product, system, system_ext

## What the candidate changes

Rebuilt: system, system_ext, product, vendor (2 overlay APKs removed).
Untouched: boot, init_boot, vendor_boot, dtbo, recovery, odm, dlkm, modem,
radio, vbmeta* (all originals retained; logical .imgs re-extractable from the
official zip at any time — hashes in firmware-manifests/EU-logical-images.sha256).

## What a hardware test requires (unlocked bootloader assumed)

1. `avbtool add_hashtree_footer` (or full re-sign) for each rebuilt image,
   generating new descriptors.
2. Rebuild `vbmeta_system` with the new descriptors, signed by OUR test key
   (external/avb testkey or fresh 2048-bit key generated at build time and
   recorded). Rollback index MUST be >= 1775001600 or the bootloader rejects
   (use 1775001600 exactly to avoid an irreversible bump).
3. Rebuild top-level `vbmeta` (chain to new vbmeta_system digest + test key),
   flags patched to 0x03 at offset 0x78 big-endian per wiki procedure
   (verification disabled). Rollback index stays 0.
4. Flash ONLY: system_b, system_ext_b, product_b, vendor_b, vbmeta_system_b,
   vbmeta_b (inactive slot B in the test plan). Everything else stays stock.

## Consequences (must disclose to owner before any test)

- Test-key signatures: device boots ORANGE state; Play Integrity / SafetyNet
  fail permanently on the candidate; Widevine L1 → L3 (keybox bound to
  verified boot state).
- No ZTE private keys are involved at any point; we never forge stock signatures.
- Rollback: restoring stock vbmeta* + stock logical images returns to GREEN
  (keys match stock again) except Widevine/fingerprint-calibration state,
  which must be verified post-restore.
- The OFF-DEVICE deliverable stops at: rebuilt images + regenerated descriptors
  + unsigned vbmeta staging + this procedure. No flashing tooling is run here.

## Off-device verification performed

- avbtool info_image parse of stock chain (descriptors enumerated above).
- After rebuild: `avbtool verify_image` on each candidate image (planned,
  Phase 9 re-run) + descriptor diff vs stock (only the 4 rebuilt partitions
  may differ; all other descriptors must be byte-identical).

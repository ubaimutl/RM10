# Candidate AVB design

V1's complete chain failed: its boot/recovery chain descriptors named a test key while the retained stock images used ZTE's key. Individual logical-image checks did not detect it. V1 remains historical and must not be used for a hardware test.

## Pinned stock chain

For EU 11.0.5MR1, top-level vbmeta uses SHA256_RSA4096. It chains boot at rollback location 3, recovery at 1 and vbmeta_system at 2; it also describes dtbo, init_boot, vendor_boot, ODM, system_dlkm, vendor and vendor_dlkm. vbmeta_system uses SHA256_RSA2048 and describes pvmfw, product, system and system_ext. Its stock rollback index is 1775001600.

Source-image metadata does not establish the stored rollback indexes or trusted-key policy of a particular bootloader.

## V2 construction

The pinned host pipeline implements these rules:

1. Rebuilt logical images receive explicit deterministic salts and SHA-256 hashtrees without FEC. Their footer metadata has algorithm NONE; authenticity comes from the signed parent metadata.
2. Replace only rebuilt-image descriptors in vbmeta_system. Preserve pvmfw, properties and every unchanged descriptor byte for byte. Sign with the local system test key.
3. Replace only the vbmeta_system chain public key in top-level vbmeta, plus the vendor descriptor for the full profile. Preserve stock boot/recovery chain descriptors, ZTE public keys, flags and rollback locations. Sign with the local top-level test key.
4. Retain stock rollback indexes and locations. Keep verification enabled with flags **0**. Do not substitute flags 3 or skipped chain-key checks for a consistent image set.
5. Keep stock vbmeta file envelopes, compare serialized descriptors and run `avbtool verify_image --follow_chain_partitions` against the entire assembled set.

System-only gets its own metadata retaining stock product, system_ext and vendor descriptors. Full-profile metadata must not be reused with those stock images.

The parser/encoder comes from the pinned avbtool Python implementation; its binary hash and tool dependencies are locked because the pipeline uses its internal API for exact descriptor preservation. Test-key public fingerprints are pinned; private keys stay local. No ZTE private key is used.

## Hardware limits

A host pass establishes consistency under embedded keys. It does not make the test keys trusted by a locked bootloader, prove acceptance on an unlocked NX789J, read stored rollback values or validate a stock restore. Receipts mark locked-bootloader compatibility false and hardware testing unauthorized.

See [OFFLINE-BUILD.md](OFFLINE-BUILD.md), [PARTITION-WRITES.md](PARTITION-WRITES.md) and [TEST-PLAN-DRAFT.md](TEST-PLAN-DRAFT.md).

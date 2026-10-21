# Offline investigation of installation and recovery paths

Reviewed 21 October 2026. **NOT READY for hardware testing.** This review
uses the pinned EU 11.0.5MR1 OTA, extracted binaries and public source code.
It does not describe any particular phone's slot state or measurements.
Machine-readable evidence: [offline-path-audit.json](../build/offline-path-audit.json).

## 1. What the official updater actually uses

The OTA's CrAU v2 manifest was read directly from the ZIP. It is a full
payload (minor version 0, `partial_update=false`) with 42 partition updates.
Its dynamic group contains system, system_ext, product, vendor, ODM,
system_dlkm and vendor_dlkm. The group maximum is 17,175,674,880 bytes;
this is a source-package limit, not a measurement of free storage.

The manifest enables snapshots, VABC, LZ4, COW version 3 and a compression
factor of 65,536. The extracted vendor properties independently enable
userspace compressed snapshots. There are no requested postinstall steps.
The stock manifest's seven COW estimates sum to 10,082,897,743 bytes.
That is a source-package estimate, not the candidate's space requirement or
proof that any target has enough space.

Raw writes through an inactive logical mapping are not a substitute for
snapshot creation. A full candidate also cannot be assumed to fit as a
second independent physical system. Every target requires its own layout
and available-space checks.

## 2. Stock update trust is separate from AVB

Both the extracted system and stock recovery contain an otacerts ZIP with
one `releasekey.x509.pem`. Its SPKI SHA-256 is
`d4b0eaebe9974885528b9b9ffe7a365fc363e17a1508f1a0c85f79d23aa4d3d0`.
The official package certificate has that same key. The payload metadata
signature verifies with this key from both stores.

Neither candidate signing key matches it. A synthetic negative control
also verifies a candidate signature with its own key and rejects it with
the stock update key. This is a cryptographic trust check, not a submitted
update package or an OEM runtime acceptance test.

AOSP recovery verifies the outer ZIP against its certificate store before
installation. Update_engine separately verifies the payload. Its Android
implementation uses the certificate ZIP when available; the stock binary
contains that path and verification diagnostics. Bootloader unlock does
not itself add a key to either store. An AVB-valid image directory cannot
therefore be treated as a stock-accepted OTA. No OEM bypass is established.

## 3. A partial payload can write more than its listed images

In the reviewed Android 16 implementation, `DeltaPerformer` invokes
`GenerateOperationsForPartitionsNotInPayload` for a partial update. The
Android generator reads `ro.vendor.build.ab_ota_partitions`, skips dynamic
partitions, and generates SOURCE_COPY operations for omitted physical A/B
partitions. The host build explicitly skips this generation: host verification
alone would miss these device-side writes.

Using the pinned source properties and either proposed six-image full
profile or three-image system-only payload projects **32 extra physical
partition copies**. They include modem, boot, recovery, init_boot, vendor_boot,
ABL, XBL, UEFI, TZ and keymaster. These are source-to-target copies, not CN
firmware substitution, but they are still writes outside the proposed scope.
Relevant generation diagnostics are present in the stock update_engine binary.
The projection is not a record of actual writes on a phone.

An unmodified partial OTA is therefore unsuitable for the current exclusions.
Partial updates also require snapshot support and valid per-partition
timestamps; simply setting a manifest flag is not a complete package design.

## 4. Recovery may abandon snapshot isolation

`PreparePartitionsForUpdate` attempts snapshot creation. In Android mode,
snapshot preparation failure returns failure. In recovery mode, that failure
can instead set `delete_source=true` and proceed to overwrite existing
partitions. The overwrite diagnostic is present in the stock updater binary.

An eventual installer must reject this fallback. A recovery feature labelled
"ZIP flashing" or "fastbootd" does not establish snapshot-preserving behavior.
Super metadata, /metadata/ota, COW backing storage (potentially userdata),
boot-control state and logs/preferences also belong in the write inventory.

Snapshot fallback is temporary. Once merge starts, the original base blocks
are replaced and normal cancellation is refused by libsnapshot. A normal
successful boot is not a promise of a permanent stock slot. Shared userdata
and its migrations are not rolled back by selecting another slot either.

## 5. Bootloader analysis: supporting evidence, not a boot test

The official ABL image is an ELF containing a firmware volume. Its guided
LZMA section was decompressed on the host and the ARM64 PE image inspected
with llvm-objdump. Code references exist for the diagnostics saying that an
unlocked state skips verification or continues after an AvbSlotVerify result.
The evidence JSON records original/expanded/PE hashes and reference RVAs.

This supports the expected unlocked verification policy. It does not establish
all OEM branches, persistent rollback values, current bootloader identity,
recovery selection or successful candidate boot. No modified bootloader is
needed or proposed by this analysis. AOSP libavb and fs_mgr allow verification
errors in unlocked mode under their respective policies; that reference
behavior is not proof of a particular OEM execution path.

## 6. Recovery tools and restore scope

On 21 October, the OrangeFox source HEAD is
`a2e8ac30dbe28df75e1e7ae25e05e0619b86ee31`, but the latest published image is
still the June release with SHA-256
`1d98db121bc30b680e0392483a1040b7661b5ccd94c0fadd96502ac5e19e7bfc`.
Its README and BoardConfig are unchanged from the previous review.
It supplies no new matching-EU restore demonstration. See
[RECOVERY-REVIEW.md](RECOVERY-REVIEW.md).

The extracted **stock** recovery fstab also declares ext4 for dynamic
partitions whose source images are EROFS. Therefore that textual mismatch
alone must not be used to reject OrangeFox. Actual mount/restore behavior,
slot resolution and compatibility still require evidence.

The official OTA has neither a matched Firehose programmer nor factory
rawprogram/patch XML. The initial local inventory did not contain a programmer.
A subsequent static toolbox review obtained an NX789J programmer candidate
with matching embedded OEM root and verified signed ELF components; outer
bundle handling and hardware acceptance remain unproven. See [PROGRAMMER-REVIEW.md](PROGRAMMER-REVIEW.md).
Public EDL client code is transport tooling, not
proof that a compatible signed programmer will be accepted. A chipset name
or another model's programmer is insufficient. No complete EDL recovery
kit or demonstrated restore has been established by this review.

The 42 OTA images are firmware inputs, not a complete backup of shared state,
provisioning, GPT, userdata or other device-specific partitions. An official
OTA may be a useful restore input if a functioning accepted installer remains
available; its existence does not provide an independent unbrick route.

## 7. Concrete next engineering path

| Route | Offline conclusion |
| --- | --- |
| Raw writes to inactive logical devices | Cannot establish isolation; reject overlapping mappings |
| Stock local update or stock sideload | Candidate keys are outside the measured stock update trust |
| Unmodified partial OTA | Adds physical copies outside the current write scope |
| Full super replacement | Replaces shared storage and sacrifices the proposed stock fallback |
| Snapshot-aware nonpartial payload with all seven dynamic images plus two vbmeta images | Design option requiring a separately trusted, reviewed updater |
| OrangeFox or EDL restore | No demonstrated matching-firmware recovery route established |

The nine-image design would include the three unchanged ODM/DLKM images
explicitly, preserving the entire seven-partition group without using the
partial-update static-copy generator. It increases deliberate writes from
six to nine. It must not silently add other firmware writes. All retained
target boot/firmware bytes must first match the assembled AVB set; a mismatch
blocks installation. It also requires regenerated payload signatures,
care-map/verification metadata, accurate COW sizing and an explicit policy
for snapshot preparation, boot success, merge and rollback.

This is a proposal, not a built or validated installation artifact. Before
building a deployable package, select an available trusted execution path
and a credible independent restore mechanism. Host integration tests must
then exercise the exact installer with Virtual A/B, assert its complete write
set, and inject space exhaustion and interrupted-update failures. Reference
AOSP behavior and binary markers do not replace testing the selected updater.

Offline analysis has narrowed the choices. The remaining obstacle is obtaining
and validating the installer/recovery path, not waiting for an external reply.
No hardware procedure, unlock or write is authorized by this document.

## Primary sources

- [Payload schema](https://android.googlesource.com/platform/system/update_engine/+/2da98fe459c01d8902ea68b3fb2090578f49c8f6/update_metadata.proto), [partial-update expansion](https://android.googlesource.com/platform/system/update_engine/+/2da98fe459c01d8902ea68b3fb2090578f49c8f6/payload_consumer/delta_performer.cc), [Android copy generator](https://android.googlesource.com/platform/system/update_engine/+/2da98fe459c01d8902ea68b3fb2090578f49c8f6/payload_consumer/partition_update_generator_android.cc).
- [Snapshot preparation and recovery fallback](https://android.googlesource.com/platform/system/update_engine/+/2da98fe459c01d8902ea68b3fb2090578f49c8f6/aosp/dynamic_partition_control_android.cc), [payload signature verification](https://android.googlesource.com/platform/system/update_engine/+/2da98fe459c01d8902ea68b3fb2090578f49c8f6/payload_consumer/payload_verifier.cc).
- [Recovery package verification](https://android.googlesource.com/platform/bootable/recovery/+/80fbea7e9af1dd883f2046e9b299d6fe45a0f693/install/install.cpp), [libsnapshot cancellation and merge](https://android.googlesource.com/platform/system/core/+/68be0c2c0006a0740d0b1809abe4717308f90d15/fs_mgr/libsnapshot/snapshot.cpp).
- [AVB reference](https://android.googlesource.com/platform/external/avb/+/5ac0c3a071d811846a62412383dd6e259f341e6e/README.md), [fs_mgr verification policy](https://android.googlesource.com/platform/system/core/+/68be0c2c0006a0740d0b1809abe4717308f90d15/fs_mgr/libfs_avb/fs_avb.cpp).
- [OrangeFox release](https://github.com/plompomg/rm10pro-orangefox-recovery/releases/tag/release), [EDL client source](https://github.com/bkerler/edl/tree/1cda1a616748d608667b2d13b73a28d3197ceb45).

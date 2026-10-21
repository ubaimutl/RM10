# Hardware-test gates — blocked

The former draft assumed B was inactive and A was an independent stock fallback. Neither is a project default. This document replaces that execution recipe with requirements; it does not authorize phone operations.

## Gate 0: host artifacts

- Choose an installer execution/trust path and audit runtime writes, not only payload entries. Reject the partial-update implicit-copy and recovery overwrite fallbacks identified in [OFFLINE-TEST-PATH.md](OFFLINE-TEST-PATH.md).

- Reassemble the stage from pinned stock inputs and donors and verify its content identity.
- Build twice with pinned compression, UUIDs, timestamps, salts, keys and tools. Compare tar, raw EROFS and final image hashes.
- Require a complete passing AVB chain with stock boot/recovery descriptors and rollback policy preserved. Verify each experimental profile independently.
- Produce a complete image manifest, descriptor diff and partition-write inventory.
- Model an explicit layout without assuming slot state, fallback contents, reclaimable extents or physical independence.

Results belong in [STATUS.md](STATUS.md) and the validation report. Host checks are necessary, but do not establish hardware acceptance.

## Gate 1: demonstrate recovery before destructive work

Remain blocked until there is evidence for:

- A feasible backup scope, acquisition method and restore route on the exact test firmware. Establish what can be read before a destructive transition; do not schedule the first required backup after unlocking.
- Recovery entry and stock write capability after boot failure, preferably demonstrated on matching spare hardware. A read-back checksum is not a restore demonstration.
- Exact recovery image hashes and validated slot, filesystem, decryption, restore, AVB and rollback behavior if custom recovery is involved.
- A restore design avoiding modem/EFS/persist/regional/provisioning writes. Operations affecting both slots or shared storage must be explicit.
- Accounted-for data loss and device-state transitions before any later hardware authorization.

An OTA ZIP alone is not a complete device-specific recovery image. Unreadable boot-control or rollback values remain unresolved.

[RECOVERY-REVIEW.md](RECOVERY-REVIEW.md) records the published OrangeFox
binary's unsigned AVB metadata, older Global fingerprint and filesystem/slot
configuration concerns. None has been resolved by a matching-firmware restore test.

## Gate 2: validate the actual hardware procedure

Only after Gate 1 can a procedure be reviewed against a particular target:

- Establish firmware identity, active slot, boot-control flags, rollback constraints and snapshot state through a separately authorized inspection method.
- Verify that every retained image at the intended target matches the pinned stock set. The running build's identity does not prove another slot's boot, recovery or firmware contents. Revise the image/write plan if any retained input differs.
- Resolve logical-image and physical boot/vbmeta capacities, shared extents and every allocation change. Demonstrate protection of the running system or explicitly abandon any protected-fallback claim.
- Choose a validated snapshot/update or allocation mechanism. An offline capacity calculation does not prove it works.
- Identify every image write and shared-state change, with a recovery action for failure at each stage. Never relock around modified images.
- Account for shared userdata changes during candidate boot and any migration or app-state incompatibility on fallback; switching system slots is not a data restore.
- Obtain explicit authorization for the concrete destructive procedure. Off-device development does not authorize unlocking, rebooting, installation, slot switching or flashing.

## Gate 3: runtime acceptance

If a controlled test is eventually authorized, use [TEST-MATRIX.md](TEST-MATRIX.md) for boot, networking, camera, fingerprint, charging and REDMAGIC behavior. Static checks cannot establish full functionality. System-only remains a dependency probe with Google components in other partitions.

Runtime success does not prove relocking or stock restoration safe; those are separate procedures with their own evidence requirements.

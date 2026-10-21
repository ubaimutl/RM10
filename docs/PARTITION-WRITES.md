# Partition-write inventory

This is a design inventory. No executable hardware procedure is validated.

**This table lists deliberate candidate image replacements, not every write
an installer might perform.** The 21 October review found that the AOSP partial
update path can synthesize additional physical A/B copies. With the pinned
source properties, either proposed profile projects 32 such copies, including
modem and boot firmware. That path violates the exclusions below and is not
approved by this inventory. A nonpartial snapshot design would explicitly
include the three unchanged ODM/DLKM images too, increasing the image list
from six to nine. See [OFFLINE-TEST-PATH.md](OFFLINE-TEST-PATH.md).

| Image | Full profile | System-only profile | Storage constraint |
| --- | --- | --- | --- |
| system | Rebuilt | Rebuilt | Logical partition in shared super; check actual mapping and overlap |
| system_ext | Rebuilt | Stock, no image write | Shared super constraints when rebuilt |
| product | Rebuilt | Stock, no image write | Shared super constraints when rebuilt |
| vendor | Rebuilt; two overlays removed | Stock, no image write | Shared super constraints when rebuilt |
| vbmeta_system | Regenerated | Regenerated for this profile | Physical A/B; stock envelope and rollback policy retained |
| vbmeta | Regenerated | Regenerated for this profile | Physical A/B; stock boot/recovery chain keys retained |
| boot, recovery, init_boot, vendor_boot, dtbo, pvmfw, ODM, DLKM and remaining stock inputs | No candidate image write | No candidate image write | Included unchanged for host verification |
| modem, EFS/modemst, persist, regional configuration, provisioning storage | Excluded | Excluded | No experiment writes designed or authorized |

The receipt records exact sizes and hashes. Inclusion in the assembled verification directory does not place an image on the write list.

This inventory assumes the retained images at the intended target match the
pinned stock inputs used for the assembled host check. Their actual bytes
must be verified before treating them as unchanged. A running build name or
partition-size match does not establish the contents of another slot. A
mismatch requires a new reviewed image set and write inventory; copying
additional boot or firmware partitions is not implicitly authorized.

Writing dynamic partitions can require shared super metadata/allocation changes. A suffix does not isolate physical storage. Raw writes to an overlapping inactive mapping cannot preserve the running system. The model checks overlap and capacity bounds; it does not create Android snapshots or validate fastbootd behavior. A snapshot-aware update design or separately validated allocation procedure is still required.

Any eventual procedure must also account for:

- Boot-control state changes when selecting a slot.
- Unlock state changes and a userdata wipe if unlocking is needed.
- Normal candidate boot writes shared userdata and can migrate settings,
  databases and app state. Selecting another system slot does not restore
  that data to its previous state.
- Super/shared update metadata changes during snapshot creation, merge or reallocation; userdata-backed COW storage is also possible. Establish the actual chosen implementation's writes.
- Recovery's possible overwrite fallback after snapshot allocation failure; reject that fallback before treating the update as source-preserving.
- Automatic merge after update verification. Once base blocks are merged, selecting the previous suffix does not restore the original system.
- Separate recovery installation. The inspected OrangeFox instructions write both recovery copies; this cannot silently become part of a slot-isolated experiment.

The published recovery binary's headers and ramdisk were inspected directly;
see [RECOVERY-REVIEW.md](RECOVERY-REVIEW.md). It is not a validated fallback
for the pinned EU source build.

Physical capacities, rollback storage, boot-control flags and recovery entry may be inaccessible to the ordinary Android shell. Unknown values remain unresolved. A host AVB pass does not establish them.

The image-write inventory covers deliberate firmware writes. It does not
prove that running Android services make no automatic changes to other
shared state. The layout model does not simulate those services or userdata
migrations; the recovery/data plan must account for them separately.

An official OTA or backup checksum does not demonstrate a working restore write path. Testing stays blocked until stock recovery is demonstrated on matching firmware, preferably using a spare device. Relocking around modified images is outside the design.

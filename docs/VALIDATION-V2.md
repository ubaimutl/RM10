# V2 offline validation — 19 October 2026

**Host artifact checks pass. Hardware testing remains NOT READY.** No phone
operation was performed during this development work.

## Reproducibility and integrity

Two fresh full builds from the same pinned stage, metadata, tools, keys and
byte budgets produced identical tar hashes, raw EROFS hashes and all **42**
assembled image hashes. Both passed complete chained AVB verification under
the embedded test keys. The source OTA inventory also has exactly 42 images;
all extracted names and sizes match it.

The full profile deliberately changes six images: system, system_ext,
product, vendor, vbmeta_system and vbmeta. Every unchanged AVB descriptor is
retained, including the stock ZTE boot/recovery keys, rollback locations and
values. Flags remain zero. This does not establish locked-bootloader trust.

Twelve host regression tests pass. The separately reassembled stage matches
the earlier stage's content hash. Content-intent verification reports 11,740
unchanged entries, 105 removals, 10 additions and zero failures.

## Encoded filesystem validation

| Image | Inodes checked against intended archive | Surviving stock metadata retained | Extracted content/symlink tree matches stage |
| --- | ---: | ---: | --- |
| system | 5,241 | 5,230 | PASS |
| system_ext | 1,458 | 1,458 | PASS |
| product | 533 | 525 | PASS |
| vendor | 4,518 | 4,518 | PASS |

All 11,750 encoded inodes passed ownership, mode and xattr comparison. This
includes roots, symlink labels and binary capabilities that v1 mishandled.
The final codec census reports LZ4 only for all rebuilt images. LZ4HC uses
the same decoder family.

After independent construction and hash comparison, the second build's four
identical large payload files were replaced with links to the first build
to recover host space. Its independent build logs, audit results, manifests
and comparison receipt remain available locally.

## System-only profile

A separate fresh system-only build passes full-chain verification. Its
system image matches the full profile exactly; product, system_ext and
vendor remain stock with their original descriptors. Its deliberate image
writes are system, vbmeta_system and vbmeta.

This profile is a dependency probe. The source inventory contains 70
Google-namespaced or Play Store APK entries outside system, so it cannot
deliver the Google-free goal.

## Storage and hardware limits

The build accepts explicit capacities from a supplied layout. Images were
successfully constructed within the chosen budgets, with footers at their
specified envelope boundaries. These capacities are not NX789J defaults.

The host model still blocks raw writes to the supplied target mappings
because they overlap active extents. It does not construct Android snapshots,
prove reclaimable space, validate fastbootd, simulate userdata migration or
establish a usable fallback. No physical write procedure has been validated.

The exact retained target image contents, hardware key acceptance, rollback
storage, physical capacities and boot-control state remain hardware gates.
The [published OrangeFox binary](RECOVERY-REVIEW.md) is not a demonstrated
matching-firmware recovery route. Runtime REDMAGIC functionality is untested.

## Evidence and artifacts

- [Build recipe](../build/candidate-v2.json) and [pinned inputs/tools](../build/candidate-v2-inputs.json).
- [Machine-readable validation](../build/validation-v2.json).
- [Official source image inventory](../firmware-manifests/EU-source-image-inventory-v2.json).
- [Full generated-image manifest](../firmware-manifests/CANDIDATE-v2-full.sha256).
- [System-only generated-image manifest](../firmware-manifests/CANDIDATE-v2-system-only.sha256).
- [Reproduction workflow](OFFLINE-BUILD.md), [write inventory](PARTITION-WRITES.md) and [hardware gates](TEST-PLAN-DRAFT.md).

Images and build logs remain ignored local artifacts under `.work/`.
Current complete sets are `v2-full-first` and `v2-system-only`; their own
`SHA256SUMS` cover all assembled images. Private signing keys and local layout
budgets are not distributed. Reproducing final signed hashes requires those
same inputs; raw content hashes can be compared independently.

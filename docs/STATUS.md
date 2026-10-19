# RM10 status

Updated: 19 October 2026.

**Verdict: NOT READY FOR HARDWARE TESTING.** Two complete v2 builds pass host verification and have identical output bytes. The separate system-only profile also passes its complete host AVB chain. No hardware test is authorized or performed.

## Established results

- Official EU 11.0.5MR1 input hash and local stock full AVB chain verified.
- Candidate stage independently reassembled from stock trees and donor APKs; content hash matches the previous stage.
- Content-intent validation: 11,740 unchanged entries, 105 absent removals, 10 valid additions, zero failures.
- Twelve host regression tests pass, covering real miniature signed AVB chains, preserved descriptors, wrong-key rejection, deterministic signing/tar order, image-size rejection, staging hardlinks, direct original metadata extraction, root/symlink/binary xattrs, content round-trip auditing and layout gates.
- V1 is superseded: complete-chain mismatch and EROFS metadata defects are documented in findings F-21/F-22.
- The source OTA contains 42 images; extracted names and sizes match its payload inventory. Both complete assembled v2 sets contain all 42 images and pass full-chain AVB verification.
- Repeat builds match on every final image, raw EROFS image and tar hash, using the same pinned inputs, keys, tools and envelope budgets. This is an observed repeat-build result, not a cross-host or hardware test.
- The system-only image matches the full profile's system image, with product, system_ext and vendor retained from stock and independently matched parent metadata. It does not meet the Google-free goal.
- The final compression census reports LZ4 only on every rebuilt full-profile image.

## V2 engineering

The new pipeline pins inputs and tools, reconstructs original metadata directly from stock images, preserves boot/recovery key descriptors, retains rollback policy, keeps AVB verification enabled, and constructs a matched image set for each profile. All 11,750 encoded inodes in the full profile pass metadata checks, and extracted bytes/symlink trees match the stage on all four rebuilt partitions.

The host layout model evaluates only its supplied snapshot. Device-specific slot states, allocations and measurements are not recorded here as general NX789J facts.

## Hardware blockers

1. A validated Virtual A/B write mechanism and complete shared-state inventory remain unproven. Image fit does not establish isolated writes or a usable fallback.
2. A feasible backup scope and demonstrated stock restore route on matching firmware are still required before destructive work.
3. Hardware test-key acceptance, physical capacities, stored rollback constraints, boot-control flags and the bytes of retained target images must be established for the specific target.
4. Boot and the REDMAGIC hardware/network acceptance matrix have not been run. Relocking is a separate unvalidated procedure.

The full profile changes four logical images plus two vbmeta images. System-only changes system plus its two parents, but retains Google components outside system. Neither profile is a ready ROM release.

See [OFFLINE-BUILD.md](OFFLINE-BUILD.md), [AVB-CANDIDATE.md](AVB-CANDIDATE.md), [PARTITION-WRITES.md](PARTITION-WRITES.md) and [TEST-PLAN-DRAFT.md](TEST-PLAN-DRAFT.md).

Observed results and artifact references: [VALIDATION-V2.md](VALIDATION-V2.md).
Machine-readable evidence: [build/validation-v2.json](../build/validation-v2.json).
The published recovery binary review is in [RECOVERY-REVIEW.md](RECOVERY-REVIEW.md).

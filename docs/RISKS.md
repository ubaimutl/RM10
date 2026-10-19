# Engineering risks

Hardware testing remains blocked by [TEST-PLAN-DRAFT.md](TEST-PLAN-DRAFT.md). These risks are distinct; passing one gate does not retire the others.

| Risk | Current treatment | Remaining evidence |
| --- | --- | --- |
| Shared Virtual A/B storage and unsafe fallback assumptions | Model an explicit saved layout; reject active targets, overlapping raw writes and unverified allocation changes | A validated snapshot/update or allocation procedure that accounts for every shared write |
| No demonstrated stock recovery | Require a feasible backup scope and a tested recovery write route before destructive transitions | Matching-firmware recovery evidence, preferably on a spare device |
| AVB consistency and hardware trust | Preserve unchanged stock descriptors/rollback policy and verify the assembled chain under test keys | Hardware acceptance, stored rollback values and a reviewed return-to-stock procedure |
| Metadata corruption during EROFS reconstruction | Include the original root inode and decode binary xattrs; audit encoded metadata against both tar and surviving stock paths | Continued regression coverage and runtime validation |
| Build drift | Pin files, donor APKs, recipes, tools, libraries and public keys; two fresh full builds match on all 42 final images, raw EROFS and tar hashes | Revalidate any changed input/toolchain; cross-host behavior is untested |
| Google-dependent runtime behavior | Preserve the REDMAGIC stack and audit removals/transplants statically | Boot and the complete hardware test matrix |
| Firmware provenance or version mismatch | Use the recorded official EU input and complete image hashes | Reverify each new source build and its compatibility before changing inputs |
| Extra writes introduced by recovery tooling | Keep recovery installation separate from the ROM image-write inventory | Inspect the exact binary, headers, filesystem/slot behavior and restore path |
| Stock updates against a modified system | No tested update procedure exists for this candidate | A separately designed and validated upgrade/restore workflow |
| Host storage exhaustion | Use new workspace outputs and sequential temporary extraction; preserve prior inputs | Check free space before large rebuilds; failed outputs remain unauthorized |

The experimental candidate does not write modem, EFS/modemst, persist, regional radio configuration or provisioning storage. Any eventual restore design must preserve that exclusion. A proposed recovery tool must not silently expand the touch list.

No irreversible DRM, calibration or attestation effect is asserted without matching evidence. Relocking a modified image set is outside the design; a host signature check cannot establish that stock restoration or relocking will succeed.

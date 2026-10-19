# Architecture: rebuilt EU REDMAGIC OS

The project rebuilds selected Android filesystem images from official EU 11.0.5MR1 firmware for NX789J-EEA. The goal is Google removal while retaining REDMAGIC gaming, camera, fingerprint, charging and hardware control. Runtime preservation is unproven.

## Full candidate

The full profile rebuilds system, system_ext, product and vendor. Vendor changes include the two overlay removals recorded in the stage; vendor is not entirely untouched. Boot, recovery, init_boot, vendor_boot, dtbo, ODM, DLKM, modem and remaining low-level stock inputs are retained.

The transformation uses recorded removal lists, selected ZTE removals, AOSP donor APKs and permission allowlists. Stage assembly preserves pristine input and records changes. The transplant map and static dependency research are in `build/` and `package-analysis/`.

The proprietary REDMAGIC services and interfaces motivate retaining the stock framework/vendor relationship. Static scans suggest many gaming packages lack direct GMS dependencies, but guarded calls, permissions and framework behavior still need runtime validation. This is not evidence that every feature survives removal.

## System-only probe

System-only changes system and the two parent vbmeta images, retaining product, system_ext, vendor and their descriptors from stock. It reduces experimental scope but cannot meet the Google-free goal: core Google components remain outside system. Each profile has matched metadata and its own image-write inventory.

## Integrity and storage

V2 uses deterministic EROFS construction with pinned tools and inputs. It preserves ZTE boot/recovery keys, unchanged descriptors and rollback values, signing rebuilt metadata with local test keys while keeping verification enabled. A host pass does not confer locked-bootloader trust; see [AVB-CANDIDATE.md](AVB-CANDIDATE.md).

Partition budgets come from explicit local layout inputs. No slot state, size or fallback is a project default. Virtual A/B shares dynamic-partition storage; slot suffixes do not provide independent test systems. The host model reports overlap and capacity bounds without producing or authorizing writes.

A reliable recovery route and runtime acceptance remain unproven. Hardware testing is blocked by [TEST-PLAN-DRAFT.md](TEST-PLAN-DRAFT.md). See [OFFLINE-BUILD.md](OFFLINE-BUILD.md) for reproduction and its limits.

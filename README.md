# RM10: Google-free REDMAGIC OS research

I'm rebuilding the EU REDMAGIC OS firmware for the **REDMAGIC 10 Pro (NX789J)** to remove the privileged Google app/services stack while retaining the original REDMAGIC features: Game Space, triggers, fan, RGB, cameras, fingerprint and charging controls.

**This is an experimental research project. Hardware testing is blocked.** The candidate has not booted on hardware, and full functionality is unproven. Current results and remaining gates are in [STATUS.md](docs/STATUS.md).

## Approach

The full candidate rebuilds `system`, `system_ext`, `product` and `vendor` from EU **RedMagicOS11.0.5MR1**. The recorded transformation removes 105 files/trees, adds nine AOSP donor APKs plus an allowlist, and patches two ZTE permission/configuration files. Vendor changes include two overlay removals; it is not entirely untouched.

Boot, recovery, init_boot, vendor_boot, dtbo, ODM, DLKM, modem and other low-level stock inputs are retained. Preserving the stock stack is the approach to keeping REDMAGIC functionality; static dependency scans cannot prove that every feature still works.

The Google-free goal is not a verified release claim. Removing Google-packaged APKs does not prove the absence of every Google-derived component or network dependency. Proprietary components such as the stock Widevine APEX remain, and runtime/network acceptance is still pending.

## Firmware input

The source is the [official EU full OTA](https://rom.download.nubia.com/Europe/NX789J/V2.0.0B05MR1/update.zip), identified as `RedMagicOS11.0.5MR1_EU`, Android 16, for `NX789J-EEA`.

- Local filename: `firmware/NX789J_EU_V2.0.0B05MR1_update.zip`
- Size: 8,733,027,332 bytes
- SHA-256: `07eaf8be5036f5b7192294c379e46d0b947f9e6114c5c437c6951211a12d5027`

Firmware images, extracted trees, tools, donor APKs and private test keys are local ignored inputs. They are not included in a Git checkout. Hashes identify the inputs and artifacts; filenames alone are insufficient.

## Offline build and validation

The v2 workflow adds:

- Metadata extraction directly from stock EROFS images, including root ownership, symlink labels and binary capabilities.
- Deterministic tar order, filesystem UUIDs, timestamps, per-partition LZ4/LZ4HC settings and AVB salts, with pinned inputs, tools and public keys.
- Matched AVB metadata preserving stock boot/recovery keys, unchanged descriptors and rollback policy, with verification flags kept at zero.
- A complete assembled image manifest, required-write inventory and full-chain verification.
- Encoded metadata checks against the intended archive and surviving stock paths, plus extraction and comparison of all staged file bytes and symlink targets.
- A host model for an explicitly supplied Virtual A/B layout. It checks capacities and physical overlap without generating flashing commands.

See [OFFLINE-BUILD.md](docs/OFFLINE-BUILD.md) for commands, prerequisites and the reproducibility boundary. Private keys are not distributed; different keys produce different metadata hashes. Repeat-build results are recorded in [STATUS.md](docs/STATUS.md).

[The v2 validation report](docs/VALIDATION-V2.md) records two byte-identical
full builds and passing host AVB chains for both full and system-only profiles.

V1 is historical: its complete AVB chain fails, and its root metadata, binary capabilities and symlink-label handling were defective. Do not use the old v1 manifests or readiness claims as a validated test set. Findings F-21/F-22 explain the corrections.

## Smaller system-only probe

The system-only profile rebuilds system and its parent metadata while keeping product, system_ext and vendor stock. It is a narrower dependency experiment, but it cannot meet the Google-free goal: the stock inventory contains 70 Google-namespaced or Play Store APK entries outside system. It has a separate matching metadata set and remains subject to the same recovery and storage gates.

## Remaining hardware gates

A passing host AVB check does not establish that the bootloader accepts test keys. A/B logical names do not guarantee independent physical storage or a usable fallback. Every intended target needs its own verified layout, rollback constraints, write procedure and demonstrated stock recovery route.

No procedure here authorizes unlocking, flashing, switching slots or relocking. Modem/EFS/persist/regional/provisioning writes remain outside the experimental design. [TEST-PLAN-DRAFT.md](docs/TEST-PLAN-DRAFT.md) lists the gates, and [PARTITION-WRITES.md](docs/PARTITION-WRITES.md) lists the image and shared-state effects that any future procedure must account for.

## Repository map

| Path | Contents |
| --- | --- |
| [docs/](docs/) | Current status, architecture, AVB design, build workflow, risks and acceptance gates |
| [scripts/](scripts/) | Extraction, staging, inventory, deterministic image construction and offline checks |
| [tests/](tests/) | Host regression tests with miniature AVB images and synthetic layouts |
| [build/](build/) | Removal/transplant specifications, permission changes, recipe and input lock |
| [firmware-manifests/](firmware-manifests/) | Source hashes, APK inventories and historical artifact manifests |
| [package-analysis/](package-analysis/) | Google removal and REDMAGIC dependency research |
| [research/](research/) | Hardware-interface notes, compression analysis and virtualization limits |

Slot state, partition allocation and recovery must be established for each intended target.

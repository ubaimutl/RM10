# SOURCES

All URLs verified live 2026-10-01 unless noted. Commit hashes are the cloned states in `sources/`.

## Cloned repositories (primary evidence, in `sources/`)

| ID | Repo | Branch/HEAD | Date | Notes |
|----|------|-------------|------|-------|
| S-01 | plompomg/rm10pro-orangefox-recovery | main e1bce74 | 2026-09-30 | First working OrangeFox NX789J; FBE decrypt, fan init, partition map |
| S-02 | reminon/twrp_device_nubia_nx789j | twrp-16.0 5aa121c | 2026-03-12 | TWRP NX789J; touch bring-up history, Goodix libs, ztethp |
| S-03 | sequencode/redmagic-10-pro-udfps-fix | master | 2026-06-25 | ZteFodDaemon (decompiled → research/udfps-zte-protocol.md) |
| S-04 | sequencode/redmagic-10-pro-bt-fix | master | 2026-09-21 | A2DP offload watchdog |
| S-05 | sequencode/redmagic-10-pro-call-fix | master | 2026-06-26 | IHalAdapterVendorExtension registrar |
| S-06 | sequencode/redmagic-10-pro-udc-fix | master | 2026-09-24 | UDC cutout overlay app (a11y) — camera-area handling reference |
| S-07 | cmfnels/RM-11-Pro-Hardware-Mapping | main | 2026-? | RM11 (NX809J) fan/LED/trigger/slider sysfs map — sibling reference |
| S-08 | cmfnels/RM11-Pro-Fan-Control | main | 2026-? | Companion fan app (Kotlin helpers) |
| S-09 | zampierilucas/RedTrigger (+makardr fork) | main | 2026-? | System-wide triggers via nubia_game_scene + watchdog; SAR KEY_F7/F8 |

## Firmware sources

| ID | Artifact | Source | Provenance |
|----|----------|--------|------------|
| FW-01 | EU V2.0.0B05MR1 (page: V11.0.05MR1) update.zip, 8733027332 B, 2026-07-09 | https://rom.download.nubia.com/Europe/NX789J/V2.0.0B05MR1/update.zip (official Nubia CDN, Tencent COS) | HIGH — official; downloading |
| FW-02 | Global V2.0.0B05MR update.zip | https://rom.download.nubia.com/Europe%26Asia/NX789J/V2.0.0B05MR/update.zip (official) | HIGH — official; not yet fetched |
| FW-03 | Global GEN_NEEA_NX789JV1.0.0B13MR1 (V10.0.13, A15) | rom.download.nubia.com/Europe&Asia/NX789J/V10.0.13/update.zip via romprovider | MED — official CDN, second-hand link |
| FW-04 | CN GEN_CN_NX789JV1.0.0B12MR1_SD_WO_ERA | Baidu Pan link via romprovider (2025-04-27) | LOW — inaccessible, unverified |
| FW-05 | CN GEN_CN_NX789JV1.0.0B24_SD_WO_ERA | HalabTech listing (per brief, page not yet inspected) | LOW — unverified |
| FW-06 | EU V10.0.8/V10.0.9, GEN_EEA_NX789JV1.0.0B10MR1, GEN_EEA_NX789SV2.0.0B04MR1 | unofficialtwrp/romprovider listings | LOW–MED — not yet fetched |

## Community / documentation

| ID | Source | Date seen | Notes |
|----|--------|-----------|-------|
| C-01 | XDA REDMAGIC 10 Pro thread (4711211), incl. p.9 GSI report, p.23 EDL root guide + GPT/LUN4 map | 2026-10-01 | Partition sectors, devprg.melf method (reference only) |
| C-02 | XDA RM11 bootloader-unlock thread (4780930, ZTE Family Toolbox/SYXZ) | 2026-10-01 | SM8750 beta + 11.0.13 fuse warnings |
| C-03 | Reddit r/RedMagic 2026-07-31 CN-on-global modem breakage | 2026-10-01 | Single-report caution |
| C-04 | Reddit r/RedMagic 2026-03-14 RM11 hardware control guide (seafrogtreefrog/cmfnels) | 2026-10-01 | Sysfs map discussion |
| C-05 | XDA RM11 hardware control guide (4782482) | 2026-03-17 | Same as C-04 |
| C-06 | REDMAGIC official EU download page (gorgias.help) | 2026-07-09 content | FW-01 link origin |
| C-07 | Red Magic Wiki (per brief; URL to be pinned) | — | NOT YET INSPECTED — TODO |
| C-08 | RM11 unofficial LineageOS 23.2 (XDA 4791285) / EvolutionX 11.9 (XDA 4797197) | 2026-07/08 | NOT YET INSPECTED — TODO |

## Tooling

- payload-dumper-go (ssut) — OTA payload.bin extraction (to be vendored as documented dependency, not blob).
- bkerler/edl — EDL protocol reference (study only; no device use).
- jadx (host-present) — dex decompilation (used for F-04).
- erofs-utils / avbtool / lpunpack / simg2img — to be installed for Phase 3.

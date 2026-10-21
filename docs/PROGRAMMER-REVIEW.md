# NX789J programmer and toolbox review

Reviewed 21 October 2026. **NOT READY for hardware testing.** A concrete
NX789J programmer has now been obtained for static analysis. Finding the file
does not establish a working restore route. No downloaded toolbox executable,
script, unlock payload or programmer was run against hardware.

## Artifacts obtained

The community-linked ZTE Family Toolbox 1.2.4-beta1 archive is 35,983,533
bytes, SHA-256
`82965b165615cbe498ab48aaf2a1612d22ec8f8b6071dc1e206560583241d416`.
The link came from the RM10 wiki's download table; the original XDA page was
inaccessible during this review. No independent publisher digest was
established. These hashes identify downloaded bytes, not publisher approval.

The archive's NX789J resources include:

| Resource | Bytes | SHA-256 |
| --- | ---: | --- |
| `bin/res/NX789J/devprg` | 1,679,780 | `0aab3f764c8ffa28ae84dee5bafb26f8ad21d6ee626adb375b1a1b483316783c` |
| `bin/res/NX789J/uefi_unlock.img` | 2,707,456 | `87f077c1dd566fd8e98324c9e8c8232161528bb4a0cfce10424b1957e742d17d` |

The device profile explicitly selects NX789J, UFS, an AVB unlock route,
FRP modification, A/B with dedicated recovery, init_boot and ZTE-specific
Firehose configuration. These are toolbox declarations, not measurements
or compatibility guarantees for a particular phone or firmware.

The downloaded archive and extracted resources are held outside this Git
repository. Only general findings, hashes and host checker code are included
here. The archive's binaries and scripts are not redistributed by this project.

## Cryptographic checks

The programmer contains a small ELF container and four further ELF images
with MBNv7 signing metadata. Its embedded Qualcomm and ZTE certificate chains
contain 18 certificates; every certificate has a verified issuer signature
link within the bundle, including the self-signed roots. This checks embedded
signatures, not certificate policy, device fuses or secure-boot acceptance.

The ZTE root SPKI SHA-256 is
`89c9ce097415b63292860aa5dae1fc5feaf79b44cad665ebd1bf09926525bd3b`.
It matches the embedded root key in the pinned official EU ABL and UEFI
images. This supports further analysis; it does not prove PBL acceptance or
compatibility with a target's hardware binding and rollback policy.

All nonzero SHA-384 segment entries match the referenced bytes. OEM-only
MBNv7 signatures verify for the components at bundle offsets 1,163,604 and
1,478,988, with software IDs 3 and 37 respectively. The latter component
has no unresolved zero-hash entries outside its own hash segment.

The two dual-authority components also verify: each authority signs a view
with the other authority's signature/certificate lengths and metadata bytes
zeroed while retaining their positions. The checker verifies both the QTI and
OEM ECDSA signatures on these measured images. All four OEM signatures and
both QTI signatures therefore pass. The other zero-hash entries correspond
to empty file segments; no nonempty data segment remains excluded.

This authenticates the measured signed ELF components and their file data
under the embedded keys. It does not authenticate the small outer bundle
container as a separate signed object or establish hardware binding,
rollback policy, PBL acceptance or safe programmer behavior.

The host script [56-audit-programmer.py](../scripts/56-audit-programmer.py)
reads local files and has no USB, transport or flashing implementation. Its
JSON reports no local input paths or device identifiers. It requires the host
`cryptography` package. Example host invocation:

```sh
python3 scripts/56-audit-programmer.py /path/to/devprg \
  --reference /path/to/official/abl.img \
  --reference /path/to/official/uefi.img \
  --output /path/to/new-report.json
```

Five synthetic signed-image tests check valid OEM/dual-authority signatures,
changed code bytes, changed signed hash tables and corrupted QTI signatures.
Controls using the official ABL also detect both code and signed-table changes.
Evidence: [programmer-audit.json](../build/programmer-audit.json) and
[recovery-tool-inventory.json](../build/recovery-tool-inventory.json).

## The bundled unlock flow changes shared state

Static inspection of this archive's NX789J AVB flow finds:

1. Backup of FRP, the selected LUN4 GPT and the current boot partition.
2. Temporary removal of GPT entries named `vbmeta_a` and `pvmfw_<current>`.
   The script hardcodes `vbmeta_a`; its suitability is not inferred here.
3. Writing the unlock payload into `boot_<current>` and an unlock image into FRP.
4. Entering an unlock interface and issuing the unlock request.
5. Attempted restoration of FRP, GPT and the saved boot image, slot selection,
   and a misc wipe request when unlocking has been confirmed.

These are observed script operations, not an executable project procedure.
Automatic attempts to restore state do not prove success after interruption.
Unlocking through this flow is not confined to an inactive slot and must not
be silently included in a candidate test. The old research description of
an "EDL/firehose path" was too broad to convey these writes.

## EDL client selection

The ZTE-specific SnowFuhrer/edl-ng fork at
`f709579ceb8d4fee54a167e5cb1b9970b8d543d1` explicitly warns that its rawprogram
restore path can flash incorrectly and brick devices. That path is excluded
as a recovery recommendation. Its read commands are separate code paths,
but have not been validated here as a complete connection and read session.
The static `read-part` path reaches partition lookup, geometry acquisition
and `ReadToStream`, which builds a Firehose read request. Connection setup
can automatically upload a loader and reset the Sahara state machine; a
command named "read" therefore does not mean no device code is executed.
The manager can guess UFS sector size when storage information is unavailable,
and the read helper can proceed after an ACK without the raw-mode indicator.
These behaviors must fail closed in a backup workflow: require confirmed
geometry, the expected protocol state, exact lengths and repeatable bytes.
No safe end-to-end backup session is claimed from this source review.
The subsequent [guarded reader implementation](READ-TOOLS.md) removes those
fallbacks in a new narrow client and tests its protocol with simulated I/O.
It attaches only to an already established Firehose session and does not
bootstrap or upload the loader. Hardware interoperability remains untested.
The fork inserts `Oem="ZTE"` in Firehose configuration, consistent with the
toolbox configuration. Neither fact demonstrates a safe restore implementation.

A loader's `SkipWrite` setting is not a substitute for a host command
allowlist. This programmer includes a diagnostic indicating that SkipWrites
can select a NULL storage device; successful reads in such a mode would need
independent validation before being trusted as backups.

## Next gates

The "missing programmer file" issue is narrowed to a candidate with matching
embedded OEM root and verified signed components. Before using it:

- Check the outer bundle handling, hardware-binding fields and rollback
  requirements; component signatures do not establish device compatibility.
- Validate hardware interoperability of the guarded reader with a separately
  reviewed bootstrap/session, with no geometry or protocol guesses.
  It must not automatically invoke unlock, GPT edits, program, erase,
  provisioning, slot changes or reset commands.
- Define hardware binding, sector-size and LUN/GPT validation, repeated-read
  hashes, and backup coverage before any restore capability is claimed.

Only after that review would a separately authorized hardware session be
appropriate. Entering EDL requires a mode change; uploading a programmer runs
code in device RAM and initializes hardware. That is not ordinary non-mutating
ADB inspection and is not authorized by this offline investigation. A first
session would establish identity/read access, not flash or unlock anything.

Even correct reads do not prove recovery writes. A restore demonstration on
matching firmware remains necessary before relying on this path to protect
a candidate test. The snapshot-aware installation design in
[OFFLINE-TEST-PATH.md](OFFLINE-TEST-PATH.md) remains unimplemented.

## Sources

- [Community download table](https://mkonic.github.io/redmagic-wiki/rm10pro/zte-family-toolbox), [linked archive page](https://drive.google.com/file/d/1DfpTdhVx4uGPiFJQh0Xw9wKP5BGwbpBP/view).
- [ZTE EDL client and author warning](https://github.com/SnowFuhrer/edl-ng/tree/f709579ceb8d4fee54a167e5cb1b9970b8d543d1).
- [Coreboot Qualcomm image-format definitions](https://github.com/coreboot/coreboot/blob/812d0e2f626dfea7e7deb960a8dc08ff0e026bc1/util/qualcomm/mbn_tools.py).

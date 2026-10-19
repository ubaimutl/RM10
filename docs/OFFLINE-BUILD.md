# Reproducing the offline candidate

This workflow constructs research artifacts on a Linux host. It contains no device transport or flashing operations. Hardware testing remains blocked by [TEST-PLAN-DRAFT.md](TEST-PLAN-DRAFT.md).

## Inputs and reproducibility boundary

The build starts from extracted official EU 11.0.5MR1 stock images, a staged filesystem tree, original metadata tables, donor APKs and local test keys. The source ZIP hash is recorded in `firmware-manifests/EU-V2.0.0B05MR1.sha256`.

`build/candidate-v2-inputs.json` pins staged file bytes and symlink targets, metadata tables, every stock image, each donor APK, transformation specifications, building scripts, tool binaries and their dynamic libraries. It records signing public-key fingerprints. The build rejects mismatches. Ownership, modes and labels come from pinned metadata tables and file contexts; host directory insertion order and mtimes do not define the output.

`build/candidate-v2.json` pins per-partition compression, worker count, block size and timestamp. Filesystem UUIDs and AVB salts are deterministic. RSA signing is deterministic with the same keys. Private test keys remain local and ignored by Git; different keys produce different metadata hashes even when raw EROFS hashes match. A different reviewed key, input or tool set requires deliberate regeneration of the lock.

The reproducibility boundary is the pinned extracted/staged inputs. A fresh extraction on another host and a different toolchain are not automatically covered. Recreate a stage in a new directory with:

```sh
bash scripts/45-assemble-stage.sh \
  .work/fs .work/donor-apks .work/new-stage
```

The assembler rejects existing outputs and missing donors, replaces staged hardlinks before writing replacement files, and records changes. A separately reassembled stage was compared to the earlier candidate stage; see the validation report.

Generate original metadata directly from the stock images in a new directory:

```sh
python3 scripts/46c-stock-meta.py --output .work/meta-v2
```

This replaces the legacy FUSE-derived tables. It includes the root and
symlink labels and represents all xattr bytes losslessly. The output tables
are pinned by the input lock; the image build uses `.work/meta-v2` by default.

## Explicit local partition budgets

Keep device-specific snapshots under `.work/` or outside the repository. One phone's active slot or allocations are not project defaults. The host model reads previously captured `lpdump --all` text; it requires both maps, a consistent active slot, usable bounds and snapshot state. Unsupported extent types or malformed ranges fail closed.

Set `RM10_TARGET_SLOT` explicitly from the intended scenario, then run:

```sh
python3 scripts/53-model-layout.py \
  --layout .work/local-layout.txt \
  --candidate .work/candidate-signed \
  --target-slot "$RM10_TARGET_SLOT" \
  --output .work/old-candidate-model.json \
  --write-sizes .work/target-sizes.json
```

The size JSON supplies byte capacities, not allocation commands. The model reserves extents from all stored maps and COW entries conservatively. It separately calculates an optimistic free-capacity bound preserving only active base extents, without authorizing reclamation. It does not simulate the snapshot service, choose write addresses or produce flashing commands. A capacity pass never enables hardware testing.

Physical overlap is checked against the union of all active logical extents.

## Build and verify

With matching pinned inputs and keys:

```sh
python3 scripts/52-build-offline.py \
  --stage .work/new-stage \
  --sizes .work/target-sizes.json \
  --profile full \
  --output .work/v2-full
```

The stage must match the lock; its directory name need not match. Outputs must be new directories. Each partition is built from a sorted tar, checked by fsck, and given a deterministic SHA-256 hashtree without FEC. The footer envelope uses the supplied capacity, including tree and metadata overhead. Content that cannot fit is rejected. A shorter file is not assumed to place its footer at the end of a larger actual allocation.

Final image hashes also depend on the supplied envelope capacities. Raw
EROFS hashes can be compared independently of those capacities and signing
keys; reproducing the final signed set requires the same budgets and keys.

The build regenerates matched metadata, preserves unchanged stock descriptors byte for byte, retains rollback values/locations, keeps flags zero and follows the complete assembled AVB chain. See [AVB-CANDIDATE.md](AVB-CANDIDATE.md).

V2 also explicitly preserves the original filesystem root metadata and
decodes getfattr's binary xattr notation before archive encoding. These fix
two inherited v1 defects; see findings F-22. Before signing, the pipeline
uses `54-audit-erofs.py` to compare every encoded inode's ownership, mode and
xattr bytes with the intended tar and surviving stock paths. It extracts
each partition temporarily and compares all file bytes, paths and symlink
targets against the staged tree. Failed audits stop the build.

Each output contains:

- Rebuilt logical images and metadata, with unchanged stock images linked into the same directory for full verification. It depends on the local stock inputs and is not a standalone distribution archive.
- `SHA256SUMS` for the assembled image set; `receipt.json` with image writes, descriptor changes, raw EROFS hashes and blocking gates.
- Copies of the recipe, pinned inputs and byte budgets, plus tar hashes and build/fsck/AVB logs.
- `hardware_test_authorized: false` and `locked_bootloader_compatible: false`.

For reproducibility, repeat with another new output and compare both manifests plus raw/tar hashes in the receipts. Verify a manifest with `sha256sum -c SHA256SUMS` from its output directory. `--reuse-raw` is a separately labelled packaging mode whose receipt says `rebuilt_from_stage: false`; it is not a fresh source rebuild.

## System-only probe

`--profile system-only` rebuilds system and matching parent metadata, retaining product, system_ext and vendor images/descriptors from stock. Its image writes are system + vbmeta_system + vbmeta. It does not meet the Google-free goal: the source APK inventory has 70 Google-namespaced or Play Store APK entries outside system, including core services in product/system_ext. Runtime acceptance is unknown.

## Tests

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Tests use miniature signed AVB chains and synthetic layouts to cover the original wrong-key regression, descriptor preservation, deterministic signing, image-size rejection, deterministic tar order, pristine-hardlink preservation, missing donors, snapshot/active-slot gates and physical overlap.

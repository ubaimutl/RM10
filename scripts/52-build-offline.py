#!/usr/bin/env python3
"""Build or package a pinned research image set entirely on the host.

Outputs are experimental artifacts, never a flashing authorization. Stock
inputs and prior candidates are read only; an existing output is rejected.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

sys.dont_write_bytecode = True
from rm10_offline import (ROOT, PARTITIONS, input_state, package_images, run,
                          sha256, write_json)


def arguments():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", type=Path, default=ROOT / ".work/candidate-fs")
    p.add_argument("--meta", type=Path, default=ROOT / ".work/meta-v2")
    p.add_argument("--stock", type=Path, default=ROOT / ".work/extract-eu/images")
    p.add_argument("--donor", type=Path, default=ROOT / ".work/donor-apks")
    p.add_argument("--config", type=Path, default=ROOT / "build/candidate-v2.json")
    p.add_argument("--input-lock", type=Path, default=ROOT / "build/candidate-v2-inputs.json")
    p.add_argument("--top-key", type=Path, default=ROOT / ".work/candidate-signed/candidate-topkey.pem")
    p.add_argument("--system-key", type=Path, default=ROOT / ".work/candidate-signed/candidate-testkey.pem")
    p.add_argument("--record-inputs", action="store_true",
                   help="record a NEW input lock after deliberate input review")
    p.add_argument("--profile", choices=["full", "system-only"], default="full")
    p.add_argument("--sizes", type=Path, help="JSON mapping partition names to target byte capacities")
    p.add_argument("--output", type=Path, help="new output directory")
    p.add_argument("--reuse-raw", type=Path,
                   help="package existing raw EROFS inputs; not a source rebuild")
    return p.parse_args()


def main():
    args = arguments()
    for name in ("stage", "meta", "stock", "donor", "config", "input_lock",
                 "top_key", "system_key", "sizes", "reuse_raw"):
        value = getattr(args, name)
        if value is not None:
            setattr(args, name, value.resolve())
    config = json.loads(args.config.read_text())
    if set(config["partitions"]) != set(PARTITIONS):
        raise ValueError("recipe must explicitly define all four partitions")
    if config["workers"] != 1 or config["block_size"] != 4096:
        raise ValueError("only the pinned single-worker 4K recipe is implemented")
    state = input_state(args.stage, args.meta, args.stock, args.donor, args.config)
    with tempfile.TemporaryDirectory(prefix="rm10-public-keys-") as tmp:
        state["public_keys"] = {}
        for name, key in [("top", args.top_key), ("system", args.system_key)]:
            public = Path(tmp) / name
            run(["avbtool", "extract_public_key", "--key", key, "--output", public])
            state["public_keys"][name] = sha256(public)
    if args.record_inputs:
        if args.input_lock.exists():
            raise ValueError("refusing to replace an existing input lock")
        write_json(args.input_lock, state)
        print("Recorded input lock:", args.input_lock, flush=True)
        return
    locked = json.loads(args.input_lock.read_text())
    if state != locked:
        different = [k for k in set(state) | set(locked) if state.get(k) != locked.get(k)]
        raise ValueError("pinned input mismatch: " + ", ".join(sorted(different)))
    if args.output is None or args.sizes is None:
        raise ValueError("--output and --sizes are required to build")
    sizes = json.loads(args.sizes.read_text())
    changed = list(PARTITIONS) if args.profile == "full" else ["system"]
    for part in changed:
        if not isinstance(sizes.get(part), int) or sizes[part] <= 0 or sizes[part] % 4096:
            raise ValueError("missing/invalid target capacity: " + part)
    output = args.output.resolve()
    # Never mutate stock, the staged tree, raw inputs or an earlier output.
    if output.exists():
        raise ValueError("output must not exist")
    for source in [args.stock, args.stage, args.meta, args.reuse_raw]:
        if source and (output.is_relative_to(source.resolve())
                       or source.resolve().is_relative_to(output)):
            raise ValueError("output and input directory trees must be separate")
    output.mkdir(parents=True)
    write_json(output / "pinned-inputs.json", state)
    write_json(output / "partition-sizes.json", sizes)
    write_json(output / "recipe.json", config)
    raw = args.reuse_raw.resolve() if args.reuse_raw else output
    raw_hashes, tar_hashes = {}, {}
    if not args.reuse_raw:
        scratch = output / ".scratch"
        scratch.mkdir()
        plat = args.stage / "system/system/etc/selinux/plat_file_contexts"
        for part in changed:
            print("Building deterministic EROFS:", part, flush=True)
            tar = scratch / (part + ".tar")
            root_meta = scratch / (part + "-root.json")
            write_json(root_meta, config["partitions"][part]["root"])
            prefix = "-" if part == "system" else "/" + part
            fc = plat if part == "system" else args.stage / part / "etc/selinux" / (part + "_file_contexts")
            run([sys.executable, ROOT / "scripts/47-build-tar.py", args.stage / part,
                 args.meta / (part + "-meta.tsv"), fc,
                 "-" if part == "system" else plat, prefix, tar,
                 "--mtime", config["mtime"], "--root-metadata", root_meta], output / (part + "-tar.txt"))
            tar_hashes[part] = sha256(tar)
            recipe = config["partitions"][part]
            cmd = [ROOT / "tools/erofs/bin/mkfs.erofs", "-z" + recipe["compressor"],
                   "-b4096", "--workers=1", "-U" + str(uuid.uuid5(uuid.NAMESPACE_URL,
                    "rm10-eu1105-v2/" + part)), "-T" + str(config["mtime"]), "--mkfs-time"]
            if recipe["cluster_bytes"]:
                cmd.append("-C" + str(recipe["cluster_bytes"]))
            cmd += [output / (part + ".img"), "--tar=f", tar]
            run(cmd, output / (part + "-mkfs.txt"))
            run([ROOT / "tools/erofs/bin/fsck.erofs", output / (part + ".img")],
                output / (part + "-fsck.txt"))
            print("Auditing encoded bytes and metadata:", part, flush=True)
            run([sys.executable, ROOT / "scripts/54-audit-erofs.py",
                 "--image", output / (part + ".img"), "--stock-image", args.stock / (part + ".img"),
                 "--stage", args.stage / part, "--tar", tar,
                 "--output", output / (part + "-audit.json")], output / (part + "-audit.txt"))
            raw_hashes[part] = sha256(output / (part + ".img"))
            tar.unlink()
            root_meta.unlink()
        scratch.rmdir()
    else:
        print("Packaging existing raw inputs (this run does not rebuild EROFS).", flush=True)
        raw_hashes = {p: sha256(raw / (p + ".img")) for p in changed}
    print("Generating matched descriptors and verifying the complete AVB chain...", flush=True)
    receipt = package_images(raw, args.stock.resolve(), output, sizes, args.profile,
                             args.top_key, args.system_key, config)
    receipt.update(raw_erofs_sha256=raw_hashes, tar_sha256=tar_hashes,
                   rebuilt_from_stage=not bool(args.reuse_raw),
                   input_lock_sha256=sha256(args.input_lock),
                   recipe_sha256=sha256(args.config),
                   partition_sizes_sha256=sha256(args.sizes))
    write_json(output / "receipt.json", receipt)
    print("OFF-DEVICE CHAIN PASS. Hardware testing remains BLOCKED.", flush=True)
    print(output, flush=True)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, KeyError) as exc:
        sys.exit(str(exc))

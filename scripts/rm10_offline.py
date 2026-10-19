"""Host-only helpers. No device transport or flashing operations."""
import copy
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
PARTITIONS = ("system", "system_ext", "product", "vendor")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def tree_digest(root):
    """Paths, directory presence, symlink targets and file bytes; no host mtimes."""
    root = Path(root)
    h = hashlib.sha256()
    for dp, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        for name in sorted(dirs + files):
            p = Path(dp) / name
            rel = p.relative_to(root).as_posix()
            kind, value = ("link", os.readlink(p)) if p.is_symlink() else (
                ("dir", "") if p.is_dir() else ("file", sha256(p)))
            h.update(json.dumps([rel, kind, value], ensure_ascii=True,
                                separators=(",", ":")).encode() + b"\n")
    return h.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run(args, log=None):
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                       env={**os.environ, "LC_ALL": "C", "TZ": "UTC"})
    if log:
        Path(log).write_text(r.stdout + r.stderr)
    if r.returncode:
        raise RuntimeError(f"host command failed ({r.returncode}): {args[0]}\n"
                           + (r.stdout + r.stderr)[-4000:])
    return r.stdout


def load_avb():
    path = shutil.which("avbtool")
    if not path:
        raise RuntimeError("avbtool is required")
    loader = importlib.machinery.SourceFileLoader("rm10_avb", path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def parse_image(avb, path):
    image = avb.ImageHandler(str(path), read_only=True)
    try:
        footer, header, descriptors, _ = avb.Avb()._parse_image(image)
        offset = footer.vbmeta_offset if footer else 0
        image.seek(offset + header.SIZE + header.authentication_data_block_size
                   + header.public_key_offset)
        key = bytes(image.read(header.public_key_size))
        return header, descriptors, key
    finally:
        image._image.close()


def identity(desc):
    if hasattr(desc, "partition_name"):
        return type(desc).__name__, desc.partition_name
    if hasattr(desc, "key"):
        return type(desc).__name__, desc.key
    return type(desc).__name__, desc.encode().hex()


def metadata(avb, source, replacements, output, private_key):
    """Replace only explicitly named descriptors; preserve all other bytes.

    The pinned avbtool implementation supplies its encoder and signing code.
    Its private helper is intentionally version/hash locked by the build.
    """
    header, old, _ = parse_image(avb, source)
    old_ids = [identity(d) for d in old]
    if len(set(old_ids)) != len(old_ids):
        raise ValueError("duplicate source descriptor identities")
    if not set(replacements).issubset(old_ids):
        raise ValueError("replacement descriptor absent from source")
    updated = [replacements.get(identity(d), d) for d in old]
    algorithm = avb.lookup_algorithm_by_type(header.algorithm_type)[0]
    blob = avb.Avb()._generate_vbmeta_blob(
        algorithm_name=algorithm, key_path=str(private_key),
        public_key_metadata_path=None, descriptors=updated,
        chain_partitions_use_ab=None, chain_partitions_do_not_use_ab=None,
        rollback_index=header.rollback_index, flags=header.flags,
        rollback_index_location=header.rollback_index_location,
        props=None, props_from_file=None, kernel_cmdlines=None,
        setup_rootfs_from_kernel=None, ht_desc_to_setup=None,
        include_descriptors_from_image=None, signing_helper=None,
        signing_helper_with_files=None, release_string=None,
        append_to_release_string=None,
        required_libavb_version_minor=header.required_libavb_version_minor)
    # Retain the stock image's physical envelope, including trailing padding.
    size = Path(source).stat().st_size
    if len(blob) > size:
        raise ValueError("regenerated metadata exceeds stock image envelope")
    Path(output).write_bytes(blob + bytes(size - len(blob)))
    new_h, new_ds, _ = parse_image(avb, output)
    if [d.encode() for d in new_ds] != [d.encode() for d in updated]:
        raise ValueError("serialized descriptors changed unexpectedly")
    for field in ("flags", "rollback_index", "rollback_index_location"):
        if getattr(new_h, field) != getattr(header, field):
            raise ValueError(f"metadata changed {field}")


def chain_replacement(avb, stock_vbmeta, public_key):
    _, ds, _ = parse_image(avb, stock_vbmeta)
    chains = [d for d in ds if isinstance(d, avb.AvbChainPartitionDescriptor)
              and d.partition_name == "vbmeta_system"]
    if len(chains) != 1:
        raise ValueError("expected exactly one stock vbmeta_system chain")
    d = copy.deepcopy(chains[0])
    d.public_key = Path(public_key).read_bytes()
    return d


def runtime_files():
    """Pin binaries and their dynamic libraries, not only version labels."""
    tools = {"avbtool": Path(shutil.which("avbtool")),
             "openssl": Path(shutil.which("openssl")),
             "python3": Path(shutil.which("python3")).resolve(),
             "mkfs.erofs": ROOT / "tools/erofs/bin/mkfs.erofs",
             "dump.erofs": ROOT / "tools/erofs/bin/dump.erofs",
             "fsck.erofs": ROOT / "tools/erofs/bin/fsck.erofs"}
    files = set(tools.values())
    import re
    for name, path in tools.items():
        if name == "avbtool":
            continue
        r = subprocess.run(["ldd", str(path)], capture_output=True, text=True)
        for p in re.findall(r"(?:=>\s+)?(/\S+)\s+\(", r.stdout):
            if Path(p).is_file():
                files.add(Path(p))
    def label(p):
        return "repo:" + p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p)
    return {label(p): sha256(p) for p in sorted(files)}


def input_state(stage, meta, stock, donor, config):
    print("Hashing pinned stage, metadata, stock images, donors and tools...", flush=True)
    recipes = [Path(__file__), ROOT / "scripts/47-build-tar.py",
               ROOT / "scripts/46c-stock-meta.py",
               ROOT / "scripts/erofs_metadata.py", ROOT / "scripts/54-audit-erofs.py",
               ROOT / "scripts/42-label-tree.py", ROOT / "scripts/45-assemble-stage.sh",
               ROOT / "scripts/48-rebuild-all.sh", ROOT / "scripts/52-build-offline.py",
               Path(config)]
    recipes += sorted((ROOT / "build").glob("*-v1.txt"))
    recipes += [ROOT / "build/privapp-permissions-aosp-transplants.xml"]
    return {"schema": 1, "stage_tree_sha256": tree_digest(stage),
            "metadata_tree_sha256": tree_digest(meta),
            "stock_images": {p.name: sha256(p) for p in sorted(Path(stock).glob("*.img"))},
            "donor_apks": {p.name: sha256(p) for p in sorted(Path(donor).glob("*.apk"))},
            "recipes": {str(p.relative_to(ROOT)): sha256(p) for p in recipes},
            "runtime_files": runtime_files()}


def package_images(raw, stock, output, sizes, profile, top_key, system_key, config):
    """Assemble a complete host-verifiable set. Caller provides a NEW directory."""
    avb = load_avb()
    stock, output, raw = Path(stock), Path(output), Path(raw)
    changed = list(PARTITIONS) if profile == "full" else ["system"]
    if config["vbmeta_flags"] != 0 or config["fec"]:
        raise ValueError("only verification-enabled, no-FEC research policy is implemented")
    for name in ("vbmeta.img", "vbmeta_system.img"):
        if parse_image(avb, stock / name)[0].flags != 0:
            raise ValueError("unexpected stock metadata flags")
    for p in stock.glob("*.img"):
        if p.stem not in changed + ["vbmeta", "vbmeta_system"]:
            (output / p.name).symlink_to(p.resolve())
    replacements = {}
    for part in changed:
        target = output / (part + ".img")
        if not target.exists():
            shutil.copyfile(raw / target.name, target)
        with target.open("rb") as f:
            f.seek(1024)
            if f.read(4) != b"\xe2\xe1\xf5\xe0":
                raise ValueError("raw input is not EROFS: " + part)
        size = sizes.get(part)
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size % 4096:
            raise ValueError(f"invalid target partition size for {part}: {size}")
        salt = hashlib.sha256((config["name"] + "/" + part).encode()).hexdigest()
        run(["avbtool", "add_hashtree_footer", "--image", target,
             "--partition_name", part, "--partition_size", size,
             "--hash_algorithm", "sha256", "--block_size", 4096,
             "--salt", salt, "--do_not_generate_fec"])
        _, ds, _ = parse_image(avb, target)
        descs = [d for d in ds if isinstance(d, avb.AvbHashtreeDescriptor)
                 and d.partition_name == part]
        if len(descs) != 1 or target.stat().st_size != size:
            raise ValueError("image envelope or hashtree descriptor mismatch")
        replacements[part] = descs[0]
    public = output / "test-system.avbpubkey"
    run(["avbtool", "extract_public_key", "--key", system_key, "--output", public])
    sub = {identity(d): d for p, d in replacements.items() if p != "vendor"}
    metadata(avb, stock / "vbmeta_system.img", sub,
             output / "vbmeta_system.img", system_key)
    chain = chain_replacement(avb, stock / "vbmeta.img", public)
    top = {identity(chain): chain}
    if "vendor" in replacements:
        top[identity(replacements["vendor"])] = replacements["vendor"]
    metadata(avb, stock / "vbmeta.img", top, output / "vbmeta.img", top_key)
    # Compare untouched descriptors directly as well as following the chain.
    diffs = {}
    for filename, allowed in [("vbmeta.img", top), ("vbmeta_system.img", sub)]:
        _, old, _ = parse_image(avb, stock / filename)
        _, new, _ = parse_image(avb, output / filename)
        changed_ids = [identity(a) for a, b in zip(old, new) if a.encode() != b.encode()]
        if not set(changed_ids).issubset(allowed):
            raise ValueError("unexpected descriptor diff")
        diffs[filename] = changed_ids
    run(["avbtool", "verify_image", "--image", output / "vbmeta.img",
         "--follow_chain_partitions"], output / "avb-full-chain.txt")
    paths = sorted(output.glob("*.img"))
    hashes = {p.name: sha256(p) for p in paths}
    (output / "SHA256SUMS").write_text("".join(f"{h}  {p}\n" for p, h in hashes.items()))
    writes = [{"partition": p, "slot": "target (must be independently established)",
               "bytes": (output / (p + ".img")).stat().st_size,
               "storage": "shared super logical allocation" if p in PARTITIONS else "physical A/B"}
              for p in changed + ["vbmeta_system", "vbmeta"]]
    receipt = {"profile": profile, "image_sha256": hashes,
               "changed_descriptors": diffs, "required_image_writes": writes,
               "additional_effects_requiring_review": ["super metadata/allocation and snapshot handling",
                 "boot-control state on slot selection", "unlock state and userdata wipe if unlocking",
                 "recovery partitions if a separate recovery installation is chosen"],
               "stock_images_are_symlinks": True, "vbmeta_flags": 0,
               "locked_bootloader_compatible": False,
               "full_removal_candidate": profile == "full",
               "google_free_runtime_verified": False,
               "hardware_test_authorized": False,
               "blocking_gates": ["hardware trust acceptance", "validated virtual A/B write procedure",
                                  "proven stock recovery route", "runtime feature testing"]}
    write_json(output / "receipt.json", receipt)
    return receipt

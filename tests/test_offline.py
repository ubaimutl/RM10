"""Host-only regression tests for AVB composition, determinism and layout gates."""
import copy
import base64
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from rm10_offline import (PARTITIONS, chain_replacement, identity, load_avb,
                          metadata, package_images, parse_image, run, sha256)
from erofs_metadata import ErofsImage
spec = importlib.util.spec_from_file_location("layout53", ROOT / "scripts/53-model-layout.py")
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


def sample_layout(disjoint=False):
    blocks = ["Current slot: _b\n"]
    for slot, suffix in [(0, "a"), (1, "b")]:
        blocks.append(f"Slot {slot}:\nPartition table:\n------------------------\n")
        for i, part in enumerate(PARTITIONS):
            sector = 2048 + i * 2048 + (16384 if disjoint and slot == 0 else 0)
            blocks.append(f"  Name: {part}_{suffix}\n  Group: dynamic_{suffix}\n"
                          "  Attributes: readonly\n  Extents:\n"
                          f"    0 .. 2047 linear super {sector}\n------------------------\n")
        blocks.append("Super partition layout:\nBlock device table:\n"
                      "  Partition name: super\n  First sector: 2048\n"
                      "  Size: 67108864 bytes\n")
    blocks.append("---------------\nSnapshot state:\n---------------\nUpdate state: none\nCurrent slot: _b\n")
    return "".join(blocks)


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for p in PARTITIONS:
            with (self.root / (p + ".img")).open("wb") as f:
                f.truncate(1048576)

    def tearDown(self):
        self.tmp.cleanup()

    def test_shared_extents_block_even_when_images_fit(self):
        report = layout.model(layout.parse_layout(sample_layout()), self.root, "a", "full")
        self.assertTrue(all(r["fits"] for r in report["images"]))
        self.assertTrue(all(r["overlap_with_active_bytes"] == 1048576 for r in report["images"]))
        self.assertFalse(report["hardware_test_authorized"])
        self.assertIn("proposed target writes overlap active physical extents", report["blocking_reasons"])

    def test_disjoint_fit_still_requires_recovery(self):
        report = layout.model(layout.parse_layout(sample_layout(True)), self.root, "a", "full")
        self.assertTrue(all(r["overlap_with_active_bytes"] == 0 for r in report["images"]))
        self.assertFalse(report["hardware_test_authorized"])
        self.assertIn("stock recovery and hardware acceptance are not established", report["blocking_reasons"])

    def test_active_slot_and_snapshot_are_blocked(self):
        parsed = layout.parse_layout(sample_layout().replace("Update state: none", "Update state: merging"))
        report = layout.model(parsed, self.root, "b", "system-only")
        self.assertIn("target is the active slot", report["blocking_reasons"])
        self.assertIn("snapshot update state is not none", report["blocking_reasons"])

    def test_short_envelope_and_oversize_are_not_accepted(self):
        with (self.root / "system.img").open("wb") as f:
            f.truncate(1048576 + 4096)
        with (self.root / "product.img").open("wb") as f:
            f.truncate(4096)
        r = layout.model(layout.parse_layout(sample_layout()), self.root, "a", "full")
        self.assertIn("one or more images exceed the target allocation", r["blocking_reasons"])
        self.assertIn("image footer envelopes do not match current target capacities", r["blocking_reasons"])

    def test_missing_state_unknown_extents_and_bad_ranges_fail_closed(self):
        for text in [sample_layout().replace("Update state: none\n", ""),
                     sample_layout().replace("linear super", "zero", 1),
                     sample_layout().replace("0 .. 2047", "1 .. 2047", 1),
                     sample_layout().replace("linear super 2048", "linear super 200000", 1)]:
            with self.subTest(text=text[:40]), self.assertRaises(ValueError):
                layout.parse_layout(text)


class TarTests(unittest.TestCase):
    def test_directory_insertion_order_does_not_change_archive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fc = root / "file_contexts"
            fc.write_text("/.* u:object_r:system_file:s0\n")
            meta = root / "meta.tsv"
            meta.write_text(".\t0\t0\t755\td\t\tsecurity.selinux=u:object_r:system_file:s0\n")
            hashes = []
            for i, order in enumerate([("z", "a"), ("a", "z")]):
                stage = root / str(i); stage.mkdir()
                for name in order:
                    (stage / name).mkdir()
                    (stage / name / "content").write_text(name)
                tar = root / (str(i) + ".tar")
                run([sys.executable, ROOT / "scripts/47-build-tar.py", stage,
                     meta, fc, "-", "-", tar, "--mtime", 1779121582])
                hashes.append(sha256(tar))
            self.assertEqual(hashes[0], hashes[1])

    def test_root_ownership_label_and_binary_capability_survive_erofs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); stage = root / "stage"; stage.mkdir()
            (stage / "executable").write_bytes(b"test bytes\n")
            (stage / "link").symlink_to("executable")
            cap = bytes.fromhex("01000002c0000000000000000000000000000000")
            meta = root / "meta.tsv"
            meta.write_text(".\t0\t2000\t755\td\t\tsecurity.selinux=u:object_r:vendor_file:s0\n"
                "executable\t0\t2000\t750\tf\t\tsecurity.selinux=u:object_r:runas_exec:s0;security.capability=0s"
                + base64.b64encode(cap).decode() + "\n"
                "link\t0\t0\t644\tl\t\tsecurity.selinux=u:object_r:system_file:s0\n")
            fc = root / "fc"; fc.write_text("/.* u:object_r:system_file:s0\n")
            tar = root / "image.tar"
            run([sys.executable, ROOT / "scripts/47-build-tar.py", stage, meta, fc, "-", "-", tar])
            image = root / "image.erofs"
            run([ROOT / "tools/erofs/bin/mkfs.erofs", "-zlz4", "-T1779121582", image, "--tar=f", tar])
            with ErofsImage(image) as erofs:
                original_root = erofs.inode(erofs.root_nid)
                self.assertEqual((original_root["uid"], original_root["gid"], original_root["mode"]), (0, 2000, 0o755))
                self.assertEqual(original_root["xattrs"]["security.selinux"], b"u:object_r:vendor_file:s0")
                inode = erofs.inode(erofs.nid_for_path(ROOT / "tools/erofs/bin/dump.erofs", "/executable"))
                self.assertEqual(inode["xattrs"]["security.capability"], cap)
                self.assertEqual(set(erofs.paths(ROOT / "tools/erofs/bin/dump.erofs")), {".", "executable", "link"})
                link = erofs.inode(erofs.nid_for_path(ROOT / "tools/erofs/bin/dump.erofs", "/link"))
                self.assertEqual(link["xattrs"]["security.selinux"], b"u:object_r:system_file:s0")
            audit_cmd = [sys.executable, ROOT / "scripts/54-audit-erofs.py",
                         "--image", image, "--stock-image", image, "--stage", stage,
                         "--tar", tar, "--output", root / "audit.json"]
            run(audit_cmd)
            self.assertTrue(json.loads((root / "audit.json").read_text())["pass"])
            stock_dir = root / "stock"; stock_dir.mkdir()
            for part in PARTITIONS:
                shutil.copyfile(image, stock_dir / (part + ".img"))
            regenerated = root / "regenerated-meta"
            run([sys.executable, ROOT / "scripts/46c-stock-meta.py", "--stock", stock_dir, "--output", regenerated])
            table = (regenerated / "system-meta.tsv").read_text()
            self.assertIn(".\t0\t2000\t755\td\t", table)
            self.assertIn("link\t0\t0\t644\tl\t\tsecurity.selinux=0s", table)
            self.assertIn("security.capability=0s" + base64.b64encode(cap).decode(), table)
            (stage / "executable").write_bytes(b"different bytes\n")
            with self.assertRaisesRegex(RuntimeError, "extracted bytes or symlink targets differ"):
                run(audit_cmd)


class StageTests(unittest.TestCase):
    def test_replacing_existing_paths_does_not_modify_pristine_hardlinks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for d in ("scripts", "build", "pristine/system/system/etc/permissions",
                      "pristine/system_ext", "pristine/product", "pristine/vendor", "donor"):
                (root / d).mkdir(parents=True, exist_ok=True)
            for name in ("45-assemble-stage.sh", "common.sh"):
                shutil.copyfile(ROOT / "scripts" / name, root / "scripts" / name)
            for name in ("gms-removal-v1.txt", "zte-replace-v1.txt", "zte-allowlist-patches-v1.txt"):
                (root / "build" / name).write_text("")
            (root / "build/transplants-v1.txt").write_text("donor:new.apk | system/same.apk | test | replaces\n")
            (root / "donor/new.apk").write_text("replacement")
            original = root / "pristine/system/same.apk"; original.write_text("original")
            xml = root / "pristine/system/system/etc/permissions/privapp-permissions-aosp-transplants.xml"
            xml.write_text("original XML")
            (root / "build/privapp-permissions-aosp-transplants.xml").write_text("replacement XML")
            run(["bash", root / "scripts/45-assemble-stage.sh", root / "pristine", root / "donor", root / "output"])
            self.assertEqual(original.read_text(), "original")
            self.assertEqual(xml.read_text(), "original XML")
            self.assertEqual((root / "output/system/same.apk").read_text(), "replacement")
            (root / "donor/new.apk").unlink()
            with self.assertRaisesRegex(RuntimeError, "missing required donor"):
                run(["bash", root / "scripts/45-assemble-stage.sh", root / "pristine", root / "donor", root / "missing-output"])
            self.assertFalse((root / "missing-output").exists())


class AvbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.stock = cls.root / "stock"; cls.stock.mkdir()
        cls.raw = cls.root / "raw"; cls.raw.mkdir()
        cls.avb = load_avb()
        cls.config = json.loads((ROOT / "build/candidate-v2.json").read_text())
        cls.sizes = {p: 1048576 for p in PARTITIONS}
        cls.keys = {}
        for name, bits in [("stock", 4096), ("stock-system", 2048), ("top", 4096), ("system", 2048)]:
            key = cls.root / (name + ".pem")
            run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", f"rsa_keygen_bits:{bits}", "-out", key])
            cls.keys[name] = key
            run(["avbtool", "extract_public_key", "--key", key, "--output", cls.root / (name + ".pub")])
        source = cls.root / "fs"; source.mkdir()
        (source / "example").write_text("test contents\n")
        erofs = cls.root / "base.erofs"
        run([ROOT / "tools/erofs/bin/mkfs.erofs", "-zlz4", "-T1779121582", "-U00000000-0000-0000-0000-000000000001", erofs, source])
        for p in PARTITIONS:
            shutil.copyfile(erofs, cls.raw / (p + ".img"))
            target = cls.stock / (p + ".img")
            shutil.copyfile(erofs, target)
            run(["avbtool", "add_hashtree_footer", "--image", target,
                 "--partition_name", p, "--partition_size", 1048576,
                 "--hash_algorithm", "sha256", "--salt", "aabb", "--do_not_generate_fec"])
        for p, rollback in [("boot", 1775001600), ("recovery", 1)]:
            target = cls.stock / (p + ".img"); target.write_bytes(bytes(4096))
            run(["avbtool", "add_hash_footer", "--image", target,
                 "--partition_name", p, "--partition_size", 1048576,
                 "--algorithm", "SHA256_RSA4096", "--key", cls.keys["stock"],
                 "--salt", "aabb", "--rollback_index", rollback])
        cmd = ["avbtool", "make_vbmeta_image", "--output", cls.stock / "vbmeta_system.img",
               "--padding_size", 4096, "--algorithm", "SHA256_RSA2048",
               "--key", cls.keys["stock-system"], "--rollback_index", 1775001600,
               "--prop", "retain.property:unchanged"]
        for p in ("system", "system_ext", "product"):
            cmd += ["--include_descriptors_from_image", cls.stock / (p + ".img")]
        run(cmd)
        run(["avbtool", "make_vbmeta_image", "--output", cls.stock / "vbmeta.img",
             "--padding_size", 8192, "--algorithm", "SHA256_RSA4096", "--key", cls.keys["stock"],
             "--chain_partition", f"boot:3:{cls.root / 'stock.pub'}",
             "--chain_partition", f"recovery:1:{cls.root / 'stock.pub'}",
             "--chain_partition", f"vbmeta_system:2:{cls.root / 'stock-system.pub'}",
             "--include_descriptors_from_image", cls.stock / "vendor.img",
             "--prop", "retain.top.property:unchanged"])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def package(self, name, profile="full", sizes=None):
        output = self.root / name; output.mkdir()
        result = package_images(self.raw, self.stock, output, sizes or self.sizes,
                                profile, self.keys["top"], self.keys["system"], self.config)
        return output, result

    def test_full_chain_passes_and_is_byte_reproducible(self):
        first, a = self.package("full-first")
        second, b = self.package("full-second")
        self.assertEqual(a["image_sha256"], b["image_sha256"])
        self.assertFalse(a["hardware_test_authorized"])
        self.assertFalse(a["locked_bootloader_compatible"])
        self.assertEqual(sha256(first / "boot.img"), sha256(self.stock / "boot.img"))
        self.assertEqual(sha256(first / "recovery.img"), sha256(self.stock / "recovery.img"))
        old_h, old, _ = parse_image(self.avb, self.stock / "vbmeta.img")
        new_h, new, _ = parse_image(self.avb, first / "vbmeta.img")
        self.assertEqual(old_h.flags, new_h.flags)
        for a, b in zip(old, new):
            if getattr(a, "partition_name", "") not in ("vendor", "vbmeta_system"):
                self.assertEqual(a.encode(), b.encode())

    def test_system_only_keeps_other_images_and_descriptors_stock(self):
        output, receipt = self.package("system-only", "system-only")
        self.assertFalse(receipt["full_removal_candidate"])
        self.assertEqual({r["partition"] for r in receipt["required_image_writes"]},
                         {"system", "vbmeta_system", "vbmeta"})
        for p in ("product", "system_ext", "vendor"):
            self.assertEqual(sha256(output / (p + ".img")), sha256(self.stock / (p + ".img")))
        _, old, _ = parse_image(self.avb, self.stock / "vbmeta_system.img")
        _, new, _ = parse_image(self.avb, output / "vbmeta_system.img")
        for a, b in zip(old, new):
            if getattr(a, "partition_name", "") != "system":
                self.assertEqual(a.encode(), b.encode())

    def test_wrong_boot_chain_key_is_rejected(self):
        output, _ = self.package("bad-chain")
        _, ds, _ = parse_image(self.avb, output / "vbmeta.img")
        boot = copy.deepcopy(next(d for d in ds if getattr(d, "partition_name", "") == "boot"))
        boot.public_key = (self.root / "top.pub").read_bytes()
        metadata(self.avb, output / "vbmeta.img", {identity(boot): boot},
                 output / "vbmeta-bad.img", self.keys["top"])
        with self.assertRaisesRegex(RuntimeError, "does not match key in chained descriptor"):
            run(["avbtool", "verify_image", "--image", output / "vbmeta-bad.img", "--follow_chain_partitions"])

    def test_too_small_partition_rejected(self):
        sizes = dict(self.sizes); sizes["system"] = 4096
        with self.assertRaises(RuntimeError):
            self.package("undersized", sizes=sizes)


if __name__ == "__main__":
    unittest.main()

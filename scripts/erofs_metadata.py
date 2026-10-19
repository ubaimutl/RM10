"""Read ordinary EROFS inode metadata/xattrs without mounting an image.

Supports compact/extended inodes and standard inline/shared xattr prefixes.
Unknown prefixes/layouts fail rather than silently discarding attributes.
The on-disk definitions are in erofs-utils/include/erofs_fs.h.
"""
from pathlib import Path
import re
import struct
import subprocess

PREFIXES = {0: b"", 1: b"user.", 2: b"system.posix_acl_access",
            3: b"system.posix_acl_default", 4: b"trusted.",
            5: b"lustre.", 6: b"security."}


class ErofsImage:
    def __init__(self, path):
        self.path = Path(path)
        self.file = self.path.open("rb")
        self.length = self.path.stat().st_size
        sb = self.read(1024, 128)
        if sb[:4] != b"\xe2\xe1\xf5\xe0":
            self.file.close()
            raise ValueError("not an ordinary EROFS image")
        self.block_size = 1 << sb[12]
        self.root_nid = struct.unpack_from("<H", sb, 14)[0]
        self.meta_base = struct.unpack_from("<I", sb, 40)[0] * self.block_size
        self.xattr_base = struct.unpack_from("<I", sb, 44)[0] * self.block_size

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.file.close()

    def read(self, offset, size):
        if offset < 0 or size < 0 or offset + size > self.length:
            raise ValueError("EROFS metadata read outside image")
        self.file.seek(offset)
        data = self.file.read(size)
        if len(data) != size:
            raise ValueError("short EROFS metadata read")
        return data

    def entry(self, offset):
        name_len, index, value_size = struct.unpack("<BBH", self.read(offset, 4))
        if index not in PREFIXES:
            raise ValueError("unsupported EROFS xattr prefix")
        if not (name_len or index or value_size):
            raise ValueError("empty EROFS xattr entry")
        data = self.read(offset + 4, name_len + value_size)
        name = (PREFIXES[index] + data[:name_len]).decode("utf-8")
        return name, data[name_len:], (4 + name_len + value_size + 3) // 4 * 4

    def inode(self, nid):
        start = self.meta_base + nid * 32
        data = self.read(start, 32)
        fmt, count, mode = struct.unpack_from("<HHH", data)
        version = fmt & 1
        if version:
            data = self.read(start, 64)
            uid, gid = struct.unpack_from("<II", data, 24)
        else:
            uid, gid = struct.unpack_from("<HH", data, 24)
        attrs = {}
        if count:
            offset = start + (64 if version else 32)
            size = 12 + (count - 1) * 4
            body = self.read(offset, size)
            shared = body[4]
            cursor = 12 + shared * 4
            if cursor > size:
                raise ValueError("invalid EROFS shared xattr list")
            for i in range(shared):
                index = struct.unpack_from("<I", body, 12 + 4 * i)[0]
                name, value, _ = self.entry(self.xattr_base + index * 4)
                if name in attrs:
                    raise ValueError("duplicate EROFS xattr")
                attrs[name] = value
            while cursor < size:
                name, value, length = self.entry(offset + cursor)
                if cursor + length > size or name in attrs:
                    raise ValueError("invalid EROFS inline xattr extent")
                attrs[name] = value
                cursor += length
        return {"uid": uid, "gid": gid, "mode": mode & 0o7777,
                "kind": mode >> 12, "xattrs": attrs}

    def nid_for_path(self, dump, path):
        r = subprocess.run([str(dump), "--path=" + path, str(self.path)],
                           capture_output=True, text=True, check=True)
        m = re.search(r"^NID: (\d+)\s", r.stdout, re.M)
        if not m:
            raise ValueError("dump.erofs did not report inode")
        return int(m.group(1))

    def paths(self, dump):
        paths = {".": self.root_nid}
        queue = [("", self.root_nid)]
        while queue:
            parent, nid = queue.pop()
            r = subprocess.run([str(dump), "--ls", "--nid=" + str(nid), str(self.path)],
                               capture_output=True, text=True, check=True)
            listing = r.stdout.split("FILENAME", 1)
            if len(listing) != 2:
                raise ValueError("missing EROFS directory listing")
            for line in listing[1].splitlines():
                if not line.strip():
                    continue
                m = re.fullmatch(r"\s*(\d+)\s+(\d+)\s{2,}(.*)", line)
                if not m:
                    raise ValueError("unsupported EROFS directory listing")
                child, kind, name = int(m[1]), int(m[2]), m[3]
                if name in (".", ".."):
                    continue
                rel = parent + "/" + name if parent else name
                if "/" in name or rel in paths:
                    raise ValueError("invalid EROFS directory path")
                paths[rel] = child
                if kind == 2:
                    queue.append((rel, child))
        return paths

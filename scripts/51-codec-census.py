#!/usr/bin/env python3
"""51-codec-census.py — per-inode compression census from EROFS map headers.

Reads superblock + iterates nid slots, parses compact/extended inodes
(struct defs from erofs-utils include/erofs_fs.h), locates the map header
(round_up(inode_end + inline_xattr, 8)) for compressed layouts (1, 3),
and tallies h_algorithmtype nibbles (0=LZ4 1=LZMA 2=DEFLATE 3=ZSTD).
Also counts flat/chunk/inline layouts. Validates each parse; skips padding.

Usage: 51-codec-census.py <image> [--limit-nid N]
"""
import struct
import sys

ALG = {0: "LZ4", 1: "LZMA", 2: "DEFLATE", 3: "ZSTD"}
LAY = {0: "flat-plain", 1: "compressed-full", 2: "flat-inline", 3: "compressed-compact", 4: "chunk"}


def main(img_path, limit=None, nidfile=None):
    import mmap
    fh = open(img_path, "rb")
    d = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
    assert d[1024:1028] == b"\xe2\xe1\xf5\xe0", "not erofs"
    # superblock: magic(0,4) checksum(4,4) feature_compat(8,4)
    # blkszbits(12,1) sb_extslots(13,1) root_nid(14,2) inos(16,8)
    # build_time_nsec(32,4) blocks(36,4) meta_blkaddr(40,4) xattr_blkaddr(44,4)
    magic, _, _, blkszbits, _, root_nid, inos = struct.unpack("<III BBH Q", d[1024:1048])
    blocks, meta_blk, xattr_blk = struct.unpack("<III", d[1024 + 36:1024 + 48])
    blksz = 1 << blkszbits
    meta_base = meta_blk * blksz
    print(f"blksz={blksz} root_nid={root_nid} inos={inos} meta_blk={meta_blk}")
    max_nid = limit or (inos + 128)
    if nidfile:
        nids = [int(x) for x in open(nidfile) if x.strip().isdigit()]
    else:
        nids = None
    tally_alg, tally_lay = {}, {}
    n_reg = n_dir = n_lnk = n_other = n_skip = 0
    def nid_iter():
        if nids is not None:
            yield from nids
            return
        nid = 0
        while nid < max_nid:
            yield nid
            nid += 1
    for nid in nid_iter():
        off = nid * 32  # nid encodes global 32B slot
        if off + 64 > len(d):
            n_skip += 1
            continue
        fmt, icount, mode = struct.unpack("<HHH", d[off:off + 6])
        ver = fmt & 1
        lay = (fmt >> 1) & 7
        ftype = (mode >> 12) & 0xF
        if ftype not in (0x4, 0x8, 0xA) or lay > 4:
            nid += 1
            n_skip += 1
            continue
        isize = 64 if ver else 32
        if ver == 0:
            imode, nlink, isize_f, uid, gid = mode, struct.unpack("<H", d[off + 6:off + 8])[0], struct.unpack("<I", d[off + 8:off + 12])[0], 0, 0
        else:
            imode = mode
            isize_f = struct.unpack("<Q", d[off + 8:off + 16])[0]
        if isize_f > len(d):
            n_skip += 1
            continue
        if ftype == 0x4:
            n_dir += 1
        elif ftype == 0xA:
            n_lnk += 1
        else:
            n_reg += 1
        tally_lay[LAY.get(lay, lay)] = tally_lay.get(LAY.get(lay, lay), 0) + 1
        if lay in (1, 3):
            xa_bytes = 0 if icount == 0 else 12 + (icount - 1) * 4
            mh = off + isize + xa_bytes
            mh = (mh + 7) // 8 * 8
            if mh + 8 <= len(d):
                # map header: u32 frag/extents_lo, u16 advise, u8 algtype, u8 clusterbits
                _lo, _adv, algt, _cb = struct.unpack("<IHB B".replace(" ", ""), d[mh:mh + 8])
                for nib in (algt & 0xF, (algt >> 4) & 0xF):
                    if nib <= 3:
                        k = ALG[nib]
                        tally_alg[k] = tally_alg.get(k, 0) + 1
    print(f"reg={n_reg} dir={n_dir} lnk={n_lnk} skipped-slots={n_skip}")
    print("layouts:", tally_lay)
    print("algorithms (HEAD1+HEAD2 nibbles over compressed files):", tally_alg)


if __name__ == "__main__":
    lim = None
    nf = None
    args = sys.argv[1:]
    if "--nids" in args:
        nf = args[args.index("--nids") + 1]
        args = [a for a in args if a != "--nids" and a != nf]
    img = args[0]
    main(img, lim, nf)

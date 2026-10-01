# Compression audit: candidate vs stock vs kernel support (2026-10-01)

Question: do the candidate's EROFS codecs match stock, and does the NX789J
kernel support every codec used? Method: direct evidence only, no assumptions.

## 1. Exact mkfs.erofs invocations (candidate v1 final)

Common flags: `-T1779121582 --mkfs-time` (deterministic timestamps), `--tar=f`
(label-faithful tarball, scripts/47-build-tar.py). erofs-utils 1.9.4 (built
from kernel.org main + --enable-fuse), run unprivileged.

| Image | Compressor flags | Content bytes | Slot bytes | Headroom |
|---|---|---|---|---|
| system | `-zlz4` | 5,462,474,752 | 5,565,849,600 | 103 MB |
| system_ext | `-zlz4hc,level=12` | 722,948,096 | 737,755,136 | 15 MB |
| product | `-zlz4` | 592,109,568 | 1,992,269,824 | 1.4 GB |
| vendor | `-zlz4hc,level=12 -C131072` | 1,623,154,688 | 1,774,276,608 | 151 MB |

Slot bytes = stock vbmeta hash-descriptor Image Size (super allocation).
All footers (sha256, no-FEC) verified with avbtool verify_image.

History (why not uniform): v1 used `-zlz4` everywhere except zstd for
sext/vendor (size-driven). The codec audit below forced zstd OUT and
lz4hc/128K-clusters IN for those two. No content changed in the process
(same tar builder, same metadata; only the compressor differed).

## 2. Stock codec census (measured, scripts/51-codec-census.py)

Method: per-inode map-header parse (h_algorithmtype nibbles; enum from
erofs-utils include/erofs_fs.h: 0=LZ4 1=LZMA 2=DEFLATE 3=ZSTD), nid lists
from fsck traversal. Validated: inode census matches `dump.erofs -S`
exactly on every image (e.g. system 4634/284/335).

| Image | Compressed files | LZ4 | LZMA | DEFLATE | ZSTD |
|---|---|---|---|---|---|
| system | 2430 | 2430 | 0 | 0 | 0 |
| system_ext | 950 | 950 | 0 | 0 | 0 |
| product | 258 | 258 | 0 | 0 | 0 |
| vendor | 2740 | 2740 | 0 | 0 | 0 |
| odm | 2 | 2 | 0 | 0 | 0 |
| vendor_dlkm | 284 | 284 | 0 | 0 | 0 |
| system_dlkm | 95 | 95 | 0 | 0 | 0 |

STOCK IS LZ4-ONLY. (An earlier draft of the census misreported LZMA/DEFLATE
hits — that was a nid-mapping bug reading wrong offsets; fixed and revalidated.)

## 3. Candidate codec census (same tool, final images)

| Image | Compressed files | LZ4 | other |
|---|---|---|---|
| system | 2305 | 2305 | 0 |
| system_ext | 940 | 940 | 0 |
| product | 192 | 192 | 0 |
| vendor | 2746 | 2746 | 0 |

CANDIDATE IS LZ4-ONLY. Codec set identical to stock (lz4hc uses the same
LZ4 decoder; cluster size is decoder-agnostic).

## 4. Kernel support proof (shipping kernel, not a tarball)

Binary: boot.img kernel, `Linux version 6.6.92-android15-8-g3637f4904cf5`
= the exact string on the owner's device. Embedded IKCONFIG extracted
(`IKCFG_ST` magic → gzip → 7746 lines, saved as .work/nx789j-kernel-config.txt):

- `CONFIG_EROFS_FS=y`, `CONFIG_EROFS_FS_XATTR=y`,
  `CONFIG_EROFS_FS_POSIX_ACL=y`, `CONFIG_EROFS_FS_SECURITY=y`,
  `CONFIG_EROFS_FS_ZIP=y` (compressed files + SELinux labels enforced)
- `CONFIG_EROFS_FS_ZIP_LZMA` unset, `CONFIG_EROFS_FS_ZIP_DEFLATE` unset
- `CONFIG_LZ4_DECOMPRESS=y`, `CONFIG_CRYPTO_LZ4=y` (decoder present)

Binary symbol audit (kernel.bin strings): `z_erofs_lz4_decompress`,
`z_erofs_load_lz4_config`, `erofs_sb_lz4_info` PRESENT; zero
`z_erofs_*zstd*` code symbols; `Z_EROFS_COMPRESSION_ZSTD` string ABSENT;
zero lzma/deflate erofs code symbols. (Generic `zstd_decompress_*` lib
exists for other subsystems but is NOT wired into erofs.)

## 5. Verdict

- Every codec in the candidate (LZ4 incl. lz4hc streams, flat/inline layouts)
  is: (a) used by stock on the same partitions, (b) enabled in the shipping
  kernel config, (c) present as code in the shipping kernel binary.
- The zstd experiment is REMOVED from the candidate (would not mount:
  no erofs-zstd wiring in this kernel). No super-resize needed; all slots fit.
- NOTHING was changed except the two compressor selections (content,
  labels, sizes-budget all re-verified after rebuild; AVB chain regenerated).

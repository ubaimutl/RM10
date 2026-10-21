# Guarded Firehose reads — host-tested implementation

Implemented 21 October 2026. **Not hardware validated; not a flashing tool.**
No phone, USB endpoint or programmer was accessed during this implementation.
All transport tests use simulated endpoints and responses.

## Scope

- [rm10_read_guard.py](../scripts/rm10_read_guard.py) implements bounded
  protocol parsing, request construction and repeated reads.
- [57-read-firehose.py](../scripts/57-read-firehose.py) validates plans offline
  by default. USB is imported only for explicit existing-Firehose attachment.
- [test_read_guard.py](../tests/test_read_guard.py) exercises the actual
  protocol and file writer with simulated traffic and corrupt GPT data.
- [read-guard-validation.json](../build/read-guard-validation.json) records
  source hashes and the scope of host verification.

This is a new narrow reader, not a patched or validated build of edl-ng.
It does not implement entering EDL, Sahara handshakes, programmer upload,
unlock, restore, reset or slot selection. An existing reviewed Firehose
session is a prerequisite for its hardware attachment mode. A shared USB
product ID alone does not prove that such a session is running.

## Implemented controls

The outbound XML command set is limited to `configure`, `getstorageinfo` and
`read`. There is no raw XML input or firmware-data upload path. Configuration
uses fixed UFS/ZTE attributes. `SkipWrite=1` is not used as a substitute for
this host restriction because it can select NULL storage on the reviewed
programmer. Configuration initializes storage: limiting host commands cannot
prove that arbitrary device code has no persistent side effects.

Before reads, every planned LUN must return two matching geometry reports.
Missing, conflicting, ambiguous or unsupported geometry is rejected. The
reader requires UFS identity, a reported physical count, supported sector
size and capacity; it does not substitute default values. These are repeated
device reports, not independent hardware measurements.

Every read must be within an explicitly planned numeric range and the
reported capacity. The default total output budget is 64 MiB, chunks are at
most 1 MiB, and each chunk is read twice and compared before being returned.
Wire traffic is approximately twice the saved bytes, plus protocol queries.
Each operation has a deadline, XML frames are limited to 64 KiB and response
processing to 32 frames. Nested/invalid XML and entity declarations fail.

Read ACKs must explicitly confirm raw mode. The reader consumes exactly the
requested raw bytes and requires a final ACK explicitly leaving raw mode.
Short/extra data, NAKs, timeouts, partial host sends and differing repeat reads
stop the session. Faulted sessions cannot resume or automatically retry.
Unexpected framing is rejected rather than repaired by guessing offsets.
Hardware may expose unsupported framing; no compatibility claim is made yet.

The USB adapter requires explicit VID/PID, bus/address, interface, active
alternate setting and bulk endpoints. It reads the current configuration and
alternate setting and rejects a mismatch. Only already-active alternate
setting zero is supported; others are rejected rather than changing the
device or PyUSB's private state. It does not set a configuration,
change an alternate setting, detach drivers, clear endpoints, reset, upload a
loader or reconnect. It releases host resources when closed.

Output uses new private directories and refuses existing destination files.
An individual range is published only after all its chunks pass their repeat
checks; failed partial files are removed. If a later range fails, earlier
completed files may remain, but there is no complete receipt. Data captures
are rejected inside public repository paths; ignored `.work/` is permitted.
Device logs and serial fields are not copied into the receipt or error output.

## Offline validation

A read plan has exactly this schema. The following values are **synthetic**,
not an NX789J layout or a recommended hardware read:

```json
{
  "schema": 1,
  "ranges": [
    {"name": "synthetic", "lun": 0, "start": 0, "count": 2}
  ]
}
```

Only numeric ranges are accepted; no disk-size expressions or partition-name
guessing is performed. Names cannot contain paths, and JSON duplicate fields,
unknown fields, booleans in numeric fields and LBA overflow are rejected.

```sh
python3 scripts/57-read-firehose.py --plan /path/to/read-plan.json
python3 -m unittest discover -s tests -p test_read_guard.py -v
```

The first command validates a file without importing USB. No hardware command
is supplied here as an installation recipe. Hardware attachment requires the
explicit attachment flag plus all selectors and a private output path. It
also requires the host PyUSB/libusb runtime and access to the selected USB
interface; the tool does not install dependencies or elevate permissions.

## GPT validation

`audit_gpt_pair` checks saved primary/backup header sectors and entry arrays
against supplied geometry. It validates header signatures, revisions, CRCs,
reciprocal header LBAs, matching disk identity and array definitions, array
CRCs and bytes, table placement, usable ranges, partition GUID uniqueness,
partition bounds and overlap. It supports 512-byte and 4096-byte sectors.
It is a pure host function and emits no read or write requests.

This check is deliberately separate from a completed read receipt. Two
identical reads of zeros do not establish that storage was read correctly;
zero-filled data fails GPT validation. A valid GPT pair still does not prove
that every requested image belongs to the intended firmware or that restore
writes will work. Repeated chunks also do not establish a globally consistent
snapshot of changing storage. The read scope must be matched to the target
and backup/recovery requirements before a complete backup can be claimed.

## Test coverage and remaining gates

Twenty additional tests exercise fragmented and coalesced XML/raw traffic,
geometry conflicts and malformed reports, range and byte budgets, forbidden
commands, ACK/raw-mode errors, truncation/excess, repeat mismatches, timeouts,
deadlines, log floods, atomic output, offline-only startup, mocked USB
attachment, and primary/backup GPT corruption or semantic inconsistencies.
The full host suite contains 37 passing tests.

The host safeguards are implemented. The remaining reader gate is actual
interoperability with an independently reviewed, explicitly authorized loader
session. The outer programmer container, hardware binding, rollback behavior
and session bootstrap are separate review items; this reader does not solve
them by automatically executing the downloaded toolbox. No mode change or
RAM execution is authorized by the tests or this document.

Read success is not a restore demonstration. The snapshot installer and
independent stock recovery remain required before a candidate flash test.

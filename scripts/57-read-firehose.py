#!/usr/bin/env python3
"""Validate a read plan offline, or explicitly attach to existing Firehose.

Does not enter EDL, upload a loader, unlock, flash, reset or select a slot.
Hardware use requires separate review/authorization; no such use is tested here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from rm10_read_guard import GuardError, ReadGuard, integer, parse_plan


class UsbBulkTransport:
    def __init__(self, args):
        # Import and enumerate only after an explicit hardware invocation.
        import usb.core
        import usb.util
        self.util = usb.util
        self.device = None
        self.claimed = False
        try:
            self._open(args, usb.core)
        except BaseException:
            self.close()
            raise

    def _open(self, args, core):
        # PyUSB's endpoint lookup starts with alternate setting zero. Do not
        # alter its private context or issue SET_INTERFACE to support others.
        if args.alternate_setting != 0:
            raise GuardError('only an already-active alternate setting zero is supported')
        devices = [d for d in core.find(find_all=True, idVendor=args.vid, idProduct=args.pid)
                   if d.bus == args.bus and d.address == args.address]
        if len(devices) != 1:
            raise GuardError('explicit USB identity did not match exactly one device')
        device = devices[0]
        self.device = device
        self.interface = args.interface
        # No set_configuration, alternate-setting change, driver detach,
        # endpoint reset, clear_halt, device reset or auto-reconnect.
        configuration = device.get_active_configuration()
        current_alt = device.ctrl_transfer(0x81, 0x0a, 0, args.interface, 1, timeout=1000)
        if len(current_alt) != 1 or current_alt[0] != args.alternate_setting:
            raise GuardError('explicit USB alternate setting is not active')
        interface = configuration[(args.interface, args.alternate_setting)]
        endpoints = {e.bEndpointAddress: e for e in interface}
        try:
            self.rx, self.tx = endpoints[args.in_endpoint], endpoints[args.out_endpoint]
        except KeyError as exc:
            raise GuardError('explicit endpoints are unavailable') from exc
        if (self.rx.bEndpointAddress & 128 != 128 or self.tx.bEndpointAddress & 128
                or self.rx.bmAttributes & 3 != 2 or self.tx.bmAttributes & 3 != 2):
            raise GuardError('expected one bulk input and one bulk output endpoint')
        if device.is_kernel_driver_active(args.interface):
            raise GuardError('kernel driver attached; automatic detachment is disabled')
        self.util.claim_interface(device, args.interface)
        self.claimed = True

    def send(self, packet):
        return self.tx.write(packet, timeout=1000)

    def receive(self, limit, timeout):
        return bytes(self.rx.read(limit, timeout=max(1, int(timeout*1000))))

    def close(self):
        if self.device is not None:
            try:
                if self.claimed:
                    self.util.release_interface(self.device, self.interface)
            finally:
                self.util.dispose_resources(self.device)
                self.device = None


def private_output(path):
    target = path.resolve()
    repo = Path(__file__).resolve().parent.parent
    if target.is_relative_to(repo) and not target.is_relative_to(repo/'.work'):
        raise GuardError('device output must be outside the repository or inside ignored .work')
    return target


def save_ranges(reader, output):
    """Publish only complete, twice-read files. Never overwrite existing files."""
    receipts = []
    for span in reader.ranges:
        partial = output/(span.name+'.partial')
        final = output/(span.name+'.bin')
        if final.exists() or partial.exists():
            raise GuardError('refusing to overwrite read output')
        digest, count = hashlib.sha256(), 0
        created = False
        try:
            with partial.open('xb') as stream:
                created = True
                sector = reader.geometry[span.lun].sector_bytes
                chunk_sectors = reader.MAX_CHUNK//sector
                start = span.start
                while start < span.start+span.count:
                    n = min(chunk_sectors, span.start+span.count-start)
                    data = reader.read_chunk(span.lun, start, n)
                    stream.write(data)
                    digest.update(data)
                    count += len(data)
                    start += n
                stream.flush()
                os.fsync(stream.fileno())
            # link() refuses an existing destination, unlike rename().
            os.link(partial, final)
            partial.unlink()
        except BaseException:
            if created:
                partial.unlink(missing_ok=True)
            raise
        receipts.append({'name': span.name, 'lun': span.lun, 'start': span.start,
                         'sectors': span.count, 'bytes': count, 'sha256': digest.hexdigest(),
                         'each_chunk_read_twice_with_matching_hashes': True})
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--attach-existing-firehose', action='store_true')
    parser.add_argument('--output', type=Path)
    for name in ['vid', 'pid', 'bus', 'address', 'interface', 'alternate-setting', 'in-endpoint', 'out-endpoint']:
        parser.add_argument('--'+name, type=lambda v: int(v, 0))
    parser.add_argument('--max-total-bytes', type=int, default=64*1024*1024)
    args = parser.parse_args()
    if args.plan.stat().st_size > 65536:
        raise GuardError('read plan exceeds size limit')
    ranges = parse_plan(args.plan.read_text())
    if not args.attach_existing_firehose:
        print('Read plan valid. Offline validation only; USB was not imported or accessed.')
        return
    if args.output is None or any(getattr(args, n) is None for n in
            ['vid', 'pid', 'bus', 'address', 'interface', 'alternate_setting', 'in_endpoint', 'out_endpoint']):
        raise GuardError('hardware attachment requires output and every explicit USB selector')
    for name, lower, upper in [('vid', 1, 65535), ('pid', 1, 65535), ('bus', 1, 255),
                                ('address', 1, 127), ('interface', 0, 255),
                                ('alternate_setting', 0, 255), ('in_endpoint', 129, 255),
                                ('out_endpoint', 1, 127)]:
        integer(getattr(args, name), lower, upper)
    output = private_output(args.output)
    # Validate all guard settings before even enumerating USB devices.
    reader = ReadGuard(None, ranges, max_total_bytes=args.max_total_bytes)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    transport = None
    try:
        transport = UsbBulkTransport(args)
        reader.transport = transport
        reader.configure()
        for lun in sorted({r.lun for r in ranges}):
            reader.confirm_geometry(lun)
        receipts = save_ranges(reader, output)
        with (output/'receipt.json').open('x') as stream:
            json.dump({'schema': 1, 'device_reported_geometry_confirmed_twice':
                       {str(lun): vars(g) for lun, g in reader.geometry.items()},
                       'ranges': receipts, 'complete_backup_or_restore_proven': False}, stream, indent=2)
        print('Completed planned repeated reads. This does not establish a complete backup or restore.')
    finally:
        if transport is not None:
            transport.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Avoid printing device log strings or USB exception data/identifiers.
        print('Read stopped: '+(str(exc) if isinstance(exc, GuardError) else type(exc).__name__), file=sys.stderr)
        sys.exit(1)

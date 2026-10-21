"""Exercise the real read protocol and output writer against simulated I/O."""
import importlib.util
import json
import struct
import types
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zlib

SCRIPTS = Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0, str(SCRIPTS))
from rm10_read_guard import GuardError, ReadGuard, ReadRange, parse_plan, audit_gpt_pair

spec = importlib.util.spec_from_file_location('read_cli', SCRIPTS/'57-read-firehose.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def xml_response(*, logs=(), value='ACK', raw=None):
    root = ET.Element('data')
    for log in logs:
        ET.SubElement(root, 'log', {'value': log})
    attrs = {'value': value}
    if raw is not None:
        attrs['rawmode'] = 'true' if raw else 'false'
    ET.SubElement(root, 'response', attrs)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


class SimulatedFirehose:
    def __init__(self, fault=None, fragment=65536):
        self.fault, self.fragment = fault, fragment
        self.pending = bytearray()
        self.requests = []
        self.queries = self.reads = 0

    def send(self, packet):
        root = ET.fromstring(packet)
        command = root[0]
        self.requests.append((command.tag, dict(command.attrib)))
        if self.fault == 'short-send':
            return len(packet)-1
        if command.tag == 'configure':
            if self.fault == 'oversized-frame':
                self.pending.extend(b'x'*(65536+1))
            elif self.fault == 'entity':
                self.pending.extend(b'<!DOCTYPE data><data><response value="ACK"/></data>')
            else:
                self.pending.extend(xml_response(value='NAK' if self.fault == 'configure-nak' else 'ACK'))
        elif command.tag == 'getstorageinfo':
            self.queries += 1
            info = {'block_size': 512, 'total_blocks': 1000, 'num_physical': 2, 'mem_type': 'UFS'}
            if self.fault == 'changed-geometry' and self.queries == 2:
                info['total_blocks'] += 1
            if self.fault == 'boolean-size':
                info['block_size'] = True
            if self.fault == 'wrong-memory':
                info['mem_type'] = 'emmc'
            if self.fault == 'unsupported-size':
                info['block_size'] = 2048
            log = 'INFO: '+json.dumps({'storage_info': info})
            if self.fault == 'duplicate-json':
                log = 'INFO: {"storage_info": {}, "storage_info": {}}'
            self.pending.extend(xml_response(logs=[] if self.fault == 'missing-geometry' else [log]))
        elif command.tag == 'read':
            self.reads += 1
            self.pending.extend(xml_response(raw=False if self.fault == 'no-raw' else True))
            length = int(command.attrib['num_partition_sectors'])*512
            data = (bytes(range(256))*(length//256+1))[:length]
            if self.fault == 'mismatch' and self.reads == 2:
                data = bytes([data[0]^1])+data[1:]
            if self.fault == 'short-data':
                self.pending.extend(data[:-1])
                return len(packet)
            self.pending.extend(data)
            if self.fault == 'excess-data':
                self.pending.extend(b'x')
            self.pending.extend(xml_response(value='NAK' if self.fault == 'final-nak' else 'ACK',
                                              raw=None if self.fault == 'final-mode-missing' else False))
        else:
            raise AssertionError('mutating or unexpected request reached transport')
        return len(packet)

    def receive(self, maximum, timeout):
        if self.fault == 'timeout':
            raise TimeoutError('simulated')
        count = min(len(self.pending), maximum, self.fragment)
        data = bytes(self.pending[:count])
        del self.pending[:count]
        return data


def session(fault=None, fragment=65536, **kwargs):
    transport = SimulatedFirehose(fault, fragment)
    reader = ReadGuard(transport, [ReadRange('sample', 0, 10, 2)], **kwargs)
    return reader, transport


class ReadGuardTests(unittest.TestCase):
    def ready(self, fault=None, fragment=65536, **kwargs):
        reader, transport = session(fault, fragment, **kwargs)
        reader.configure()
        reader.confirm_geometry(0)
        return reader, transport

    def test_fragmented_and_coalesced_xml_binary_reads_match(self):
        for fragment in [1, 7, 1024, 65536]:
            with self.subTest(fragment=fragment):
                reader, transport = self.ready(fragment=fragment)
                data = reader.read_chunk(0, 10, 2)
                self.assertEqual(data, bytes(range(256))*4)
                self.assertEqual([c for c, _ in transport.requests],
                                 ['configure', 'getstorageinfo', 'getstorageinfo', 'read', 'read'])

    def test_missing_conflicting_or_invalid_geometry_blocks_all_reads(self):
        for fault in ['changed-geometry', 'missing-geometry', 'boolean-size', 'wrong-memory',
                      'unsupported-size', 'duplicate-json']:
            with self.subTest(fault=fault):
                reader, transport = session(fault)
                reader.configure()
                with self.assertRaises(GuardError):
                    reader.confirm_geometry(0)
                self.assertFalse(any(c == 'read' for c, _ in transport.requests))
                self.assertEqual(reader.state, 'faulted')

    def test_protocol_data_and_repeat_errors_poison_session(self):
        for fault in ['no-raw', 'short-data', 'excess-data', 'final-nak', 'final-mode-missing', 'mismatch']:
            with self.subTest(fault=fault):
                reader, transport = self.ready(fault)
                with self.assertRaises(GuardError):
                    reader.read_chunk(0, 10, 2)
                before = len(transport.requests)
                with self.assertRaises(GuardError):
                    reader.read_chunk(0, 10, 2)
                self.assertEqual(len(transport.requests), before)

    def test_nak_bad_framing_short_write_and_timeout_stop(self):
        for fault in ['configure-nak', 'oversized-frame', 'entity', 'short-send', 'timeout']:
            with self.subTest(fault=fault):
                reader, transport = session(fault)
                with self.assertRaises((GuardError, TimeoutError)):
                    reader.configure()
                self.assertEqual(reader.state, 'faulted')
                self.assertEqual(len(transport.requests), 1)

    def test_out_of_plan_ranges_and_unknown_luns_never_send_read(self):
        for values in [(0, 9, 2), (0, 11, 2), (1, 10, 2), (0, 10, 0), (True, 10, 1)]:
            reader, transport = self.ready()
            before = len(transport.requests)
            with self.assertRaises(GuardError):
                reader.read_chunk(*values)
            self.assertEqual(len(transport.requests), before)

    def test_capacity_and_total_budget_are_checked_before_read(self):
        reader, transport = session(max_total_bytes=512)
        reader.configure()
        with self.assertRaises(GuardError):
            reader.confirm_geometry(0)
        self.assertEqual(transport.reads, 0)
        reader = ReadGuard(transport, [ReadRange('overflow', 0, 999, 2)])
        reader.configure()
        with self.assertRaises(GuardError):
            reader.confirm_geometry(0)

    def test_mutating_commands_cannot_cross_guard(self):
        for command in ['program', 'erase', 'patch', 'power', 'setbootablestoragedrive', 'provision']:
            reader, transport = self.ready()
            before = len(transport.requests)
            with self.assertRaises(GuardError):
                reader._send(command, {})
            self.assertEqual(len(transport.requests), before)

    def test_plan_rejects_injection_overflow_duplicates_and_booleans(self):
        valid = {'schema': 1, 'ranges': [{'name': 'one', 'lun': 0, 'start': 0, 'count': 1}]}
        for field, value in [('name', '../escape'), ('lun', True), ('start', 2**32), ('count', 0)]:
            plan = json.loads(json.dumps(valid))
            plan['ranges'][0][field] = value
            with self.assertRaises(GuardError):
                parse_plan(json.dumps(plan))
        with self.assertRaises(GuardError):
            parse_plan('{"schema":1,"schema":1,"ranges":[]}')

    def test_failed_repeat_does_not_publish_or_leave_partial_file(self):
        reader, _ = self.ready('mismatch')
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(GuardError):
                cli.save_ranges(reader, Path(directory))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_completed_reads_publish_once_and_never_overwrite(self):
        reader, _ = self.ready()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipts = cli.save_ranges(reader, root)
            self.assertEqual(receipts[0]['bytes'], 1024)
            self.assertEqual((root/'sample.bin').read_bytes(), bytes(range(256))*4)
            with self.assertRaises(GuardError):
                cli.save_ranges(reader, root)

    def test_offline_cli_never_imports_usb(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = Path(directory)/'plan.json'
            plan.write_text('{"schema":1,"ranges":[{"name":"synthetic","lun":0,"start":0,"count":1}]}')
            with patch.object(sys, 'argv', ['reader', '--plan', str(plan)]), \
                 patch.object(cli, 'UsbBulkTransport', side_effect=AssertionError('hardware path reached')):
                cli.main()

    def test_device_outputs_cannot_go_in_public_repo(self):
        with self.assertRaises(GuardError):
            cli.private_output(SCRIPTS.parent/'build'/'device-capture')

    def test_deadline_stops_before_reading_when_time_expires(self):
        ticks = iter([0.0, 11.0])
        reader, transport = session(clock=lambda: next(ticks))
        with self.assertRaisesRegex(GuardError, 'deadline'):
            reader.configure()
        self.assertEqual(reader.state, 'faulted')

    def test_log_flood_stops_at_frame_limit(self):
        reader, transport = session()
        def send(packet):
            transport.pending.extend(b'<data><log value="waiting"/></data>'*33)
            return len(packet)
        transport.send = send
        with self.assertRaisesRegex(GuardError, 'frame-count'):
            reader.configure()


def gpt_fixture(sector=512, overlap=False):
    table = bytearray(512)
    table[:16] = b'A'*16
    table[16:32] = b'B'*16
    struct.pack_into('<QQ', table, 32, 10, 20)
    if overlap:
        table[128:144] = b'A'*16
        table[144:160] = b'C'*16
        struct.pack_into('<QQ', table, 160, 20, 30)
    def header(current, other, entries):
        h = bytearray(struct.pack('<8sIIIIQQQQ16sQIII', b'EFI PART', 0x10000, 92, 0, 0,
                                  current, other, 3, 125, b'D'*16, entries, 4, 128,
                                  zlib.crc32(table) & 0xffffffff))
        struct.pack_into('<I', h, 16, zlib.crc32(h) & 0xffffffff)
        return bytes(h).ljust(sector, b'\0')
    return header(1, 127, 2), header(127, 1, 126), bytes(table), bytes(table)


class GptGuardTests(unittest.TestCase):
    def test_primary_and_backup_validate_at_both_supported_sector_sizes(self):
        for sector in [512, 4096]:
            result = audit_gpt_pair(*gpt_fixture(sector), sector, 128)
            self.assertEqual(result['partition_count'], 1)
            self.assertFalse(result['restore_proven'])

    def test_header_and_entry_corruption_are_rejected(self):
        p, b, entries, other = gpt_fixture()
        changed = bytearray(p); changed[40] ^= 1
        with self.assertRaisesRegex(GuardError, 'CRC'):
            audit_gpt_pair(bytes(changed), b, entries, other, 512, 128)
        changed = bytearray(entries); changed[100] ^= 1
        with self.assertRaisesRegex(GuardError, 'CRC'):
            audit_gpt_pair(p, b, bytes(changed), other, 512, 128)

    def test_wrong_geometry_or_inconsistent_backup_is_rejected(self):
        p, b, entries, other = gpt_fixture()
        with self.assertRaisesRegex(GuardError, 'locations'):
            audit_gpt_pair(p, b, entries, other, 512, 129)
        changed = bytearray(b)
        changed[56] ^= 1
        changed[16:20] = bytes(4)
        struct.pack_into('<I', changed, 16, zlib.crc32(changed[:92]) & 0xffffffff)
        with self.assertRaisesRegex(GuardError, 'disagree'):
            audit_gpt_pair(p, bytes(changed), entries, other, 512, 128)

    def test_valid_crcs_do_not_hide_overlapping_partitions(self):
        with self.assertRaisesRegex(GuardError, 'overlap'):
            audit_gpt_pair(*gpt_fixture(overlap=True), 512, 128)

    def test_zero_data_and_truncated_arrays_are_not_accepted_as_gpt(self):
        with self.assertRaises(GuardError):
            audit_gpt_pair(bytes(512), bytes(512), bytes(512), bytes(512), 512, 128)
        p, b, entries, other = gpt_fixture()
        with self.assertRaisesRegex(GuardError, 'length'):
            audit_gpt_pair(p, b, entries[:-1], other, 512, 128)


class UsbAdapterTests(unittest.TestCase):
    def test_real_adapter_with_simulated_endpoints_has_no_reset_or_loader_calls(self):
        server = SimulatedFirehose(fragment=7)
        events = []
        rx = types.SimpleNamespace(bEndpointAddress=0x81, bmAttributes=2,
                                   read=lambda maximum, timeout: server.receive(maximum, timeout/1000))
        tx = types.SimpleNamespace(bEndpointAddress=1, bmAttributes=2,
                                   write=lambda data, timeout: server.send(bytes(data)))
        device = types.SimpleNamespace(bus=1, address=2,
                                       get_active_configuration=lambda: {(0, 0): [rx, tx]},
                                       is_kernel_driver_active=lambda _: False,
                                       ctrl_transfer=lambda *args, **kwargs: (events.append('get-interface') or bytes([0])))
        package = types.ModuleType('usb'); package.__path__ = []
        core, util = types.ModuleType('usb.core'), types.ModuleType('usb.util')
        core.find = lambda **kwargs: (events.append('find') or [device])
        util.claim_interface = lambda d, i: events.append('claim')
        util.release_interface = lambda d, i: events.append('release')
        util.dispose_resources = lambda d: events.append('dispose')
        package.core, package.util = core, util
        args = types.SimpleNamespace(vid=1, pid=2, bus=1, address=2, interface=0,
                                     alternate_setting=0, in_endpoint=0x81, out_endpoint=1)
        with patch.dict(sys.modules, {'usb': package, 'usb.core': core, 'usb.util': util}):
            adapter = cli.UsbBulkTransport(args)
            reader = ReadGuard(adapter, [ReadRange('sample', 0, 10, 2)])
            reader.configure(); reader.confirm_geometry(0)
            self.assertEqual(len(reader.read_chunk(0, 10, 2)), 1024)
            adapter.close()
            before = list(events)
            bad = types.SimpleNamespace(**{**vars(args), 'alternate_setting': 1})
            with self.assertRaises(GuardError):
                cli.UsbBulkTransport(bad)
            self.assertEqual(events, before)
            device.ctrl_transfer = lambda *a, **kw: (events.append('get-interface') or bytes([1]))
            with self.assertRaises(GuardError):
                cli.UsbBulkTransport(args)
        self.assertEqual(events, ['find', 'get-interface', 'claim', 'release', 'dispose',
                                  'find', 'get-interface', 'dispose'])
        self.assertEqual({tag for tag, _ in server.requests}, ReadGuard.COMMANDS)


if __name__ == '__main__':
    unittest.main()

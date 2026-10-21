"""Bounded Firehose read protocol. No USB discovery or loader/bootstrap code.

Only configure, getstorageinfo and read XML can be sent through this API.
This restricts host requests, not the side effects of arbitrary device code.
"""
from dataclasses import dataclass
import hashlib
import json
import re
import struct
import time
import xml.etree.ElementTree as ET
import zlib


class GuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReadRange:
    name: str
    lun: int
    start: int
    count: int


@dataclass(frozen=True)
class Geometry:
    sector_bytes: int
    total_blocks: int
    physical_count: int


def integer(value, lower, upper):
    if type(value) is not int or not lower <= value <= upper:
        raise GuardError('missing or out-of-range integer')
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise GuardError('duplicate JSON field')
        result[key] = value
    return result


def parse_plan(text):
    try:
        plan = json.loads(text, object_pairs_hook=unique_object)
    except (ValueError, TypeError) as exc:
        raise GuardError('invalid read plan') from exc
    if type(plan) is not dict or set(plan) != {'schema', 'ranges'} or type(plan['schema']) is not int or plan['schema'] != 1:
        raise GuardError('unsupported read-plan schema')
    if type(plan['ranges']) is not list or not 1 <= len(plan['ranges']) <= 128:
        raise GuardError('invalid range list')
    result, names = [], set()
    for item in plan['ranges']:
        if type(item) is not dict or set(item) != {'name', 'lun', 'start', 'count'}:
            raise GuardError('unexpected range fields')
        name = item['name']
        if type(name) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', name) or name in names:
            raise GuardError('invalid or duplicate range name')
        names.add(name)
        lun = integer(item['lun'], 0, 31)
        start = integer(item['start'], 0, 2**32-1)
        count = integer(item['count'], 1, 2**32-1)
        if start + count > 2**32:
            raise GuardError('range exceeds supported LBA space')
        result.append(ReadRange(name, lun, start, count))
    return tuple(result)


def audit_gpt_pair(primary_header, backup_header, primary_entries, backup_entries,
                   sector_bytes, total_blocks):
    """Check saved GPT bytes only. Returns observations, never a write plan."""
    integer(total_blocks, 8, 2**32)
    if type(sector_bytes) is not int or sector_bytes not in (512, 4096):
        raise GuardError('unsupported GPT sector size')
    fmt = '<8sIIIIQQQQ16sQIII'

    def header(data, expected_lba):
        if not isinstance(data, bytes) or len(data) != sector_bytes:
            raise GuardError('GPT header must be exactly one confirmed sector')
        h = struct.unpack_from(fmt, data)
        if h[0] != b'EFI PART' or h[1] != 0x10000 or h[4] != 0 or not 92 <= h[2] <= sector_bytes:
            raise GuardError('unsupported GPT header')
        checked = bytearray(data[:h[2]])
        checked[16:20] = bytes(4)
        if zlib.crc32(checked) & 0xffffffff != h[3]:
            raise GuardError('GPT header CRC mismatch')
        if h[5] != expected_lba or h[6] != (total_blocks-1 if expected_lba == 1 else 1):
            raise GuardError('GPT header locations do not match storage geometry')
        if h[9] == bytes(16) or not 2 <= h[7] <= h[8] < total_blocks-1:
            raise GuardError('invalid GPT disk identity or usable range')
        if not 1 <= h[11] <= 4096 or not 128 <= h[12] <= 1024 or h[12] % 128:
            raise GuardError('unsupported GPT entry dimensions')
        return h

    p, b = header(primary_header, 1), header(backup_header, total_blocks-1)
    if tuple(p[i] for i in (7, 8, 9, 11, 12, 13)) != tuple(b[i] for i in (7, 8, 9, 11, 12, 13)):
        raise GuardError('primary and backup GPT disagree')
    size = p[11]*p[12]
    sectors = (size+sector_bytes-1)//sector_bytes
    if not 2 <= p[10] or p[10]+sectors > p[7]:
        raise GuardError('primary entry array overlaps usable storage')
    if b[10] <= b[8] or b[10]+sectors > total_blocks-1:
        raise GuardError('backup entry array overlaps usable storage or header')
    for table in (primary_entries, backup_entries):
        if not isinstance(table, bytes) or len(table) not in (size, sectors*sector_bytes):
            raise GuardError('GPT entry-array length mismatch')
        if zlib.crc32(table[:size]) & 0xffffffff != p[13]:
            raise GuardError('GPT entry-array CRC mismatch')
    if primary_entries[:size] != backup_entries[:size]:
        raise GuardError('GPT entry arrays differ')
    used, guids = [], set()
    for offset in range(0, size, p[12]):
        entry = primary_entries[offset:offset+p[12]]
        if entry[:16] == bytes(16):
            continue
        guid = entry[16:32]
        start, end = struct.unpack_from('<QQ', entry, 32)
        if guid == bytes(16) or guid in guids or not p[7] <= start <= end <= p[8]:
            raise GuardError('invalid or duplicate GPT partition')
        guids.add(guid)
        used.append((start, end+1))
    used.sort()
    if any(right[0] < left[1] for left, right in zip(used, used[1:])):
        raise GuardError('GPT partitions overlap')
    return {'sector_bytes': sector_bytes, 'total_blocks': total_blocks,
            'partition_count': len(used), 'entry_array_sha256': hashlib.sha256(primary_entries[:size]).hexdigest(),
            'matching_headers_and_arrays': True, 'restore_proven': False}


class ReadGuard:
    MAX_FRAME = 64*1024
    MAX_CHUNK = 1024*1024
    COMMANDS = frozenset(('configure', 'getstorageinfo', 'read'))

    def __init__(self, transport, ranges, *, timeout=10.0, max_total_bytes=64*1024*1024,
                 clock=time.monotonic):
        # Revalidate typed callers as strictly as JSON callers.
        self.ranges = parse_plan(json.dumps({'schema': 1, 'ranges': [vars(r) for r in ranges]}))
        if not 0 < timeout <= 30:
            raise GuardError('timeout must be positive and at most 30 seconds')
        integer(max_total_bytes, 1, 2**40)
        self.transport, self.timeout, self.clock = transport, timeout, clock
        self.max_total_bytes = max_total_bytes
        self.buffer = bytearray()
        self.state = 'new'
        self.geometry = {}

    def _receive(self, deadline):
        remaining = deadline-self.clock()
        if remaining <= 0:
            raise GuardError('response deadline exceeded')
        data = self.transport.receive(self.MAX_FRAME, remaining)
        if not isinstance(data, bytes) or not data or len(data) > self.MAX_FRAME:
            raise GuardError('empty, oversized or invalid transport response')
        self.buffer.extend(data)

    def _xml(self, deadline):
        while True:
            end = self.buffer.find(b'</data>')
            if end >= 0:
                end += len(b'</data>')
                if end > self.MAX_FRAME:
                    raise GuardError('XML frame exceeds limit')
                raw = bytes(self.buffer[:end]).strip()
                del self.buffer[:end]
                if b'<!' in raw or not (raw.startswith(b'<?xml ') or raw.startswith(b'<data>')):
                    raise GuardError('unexpected XML framing')
                try:
                    root = ET.fromstring(raw)
                except ET.ParseError as exc:
                    raise GuardError('invalid response XML') from exc
                if root.tag != 'data' or root.attrib or root.text and root.text.strip():
                    raise GuardError('unexpected response container')
                if not len(root):
                    raise GuardError('empty XML frame')
                return root
            if len(self.buffer) >= self.MAX_FRAME:
                raise GuardError('XML frame exceeds limit')
            self._receive(deadline)

    def _response(self, deadline, *, raw_mode=None):
        logs = []
        for _ in range(32):
            frame = self._xml(deadline)
            response = None
            for child in frame:
                if len(child) or child.text and child.text.strip() or child.tail and child.tail.strip():
                    raise GuardError('unexpected nested response content')
                if child.tag == 'log' and set(child.attrib) == {'value'}:
                    logs.append(child.attrib['value'])
                elif child.tag == 'response' and response is None:
                    response = child.attrib
                else:
                    raise GuardError('unexpected or duplicate response element')
            if response is None:
                continue
            if response.get('value') != 'ACK':
                raise GuardError('device rejected request')
            mode = response.get('rawmode')
            if mode is not None and mode not in ('true', 'false'):
                raise GuardError('invalid raw-mode indicator')
            if raw_mode is not None and mode != ('true' if raw_mode else 'false'):
                raise GuardError('required raw-mode state not confirmed')
            if raw_mode is None and mode == 'true':
                raise GuardError('unexpected raw transfer')
            return logs
        raise GuardError('response frame-count limit exceeded')

    def _send(self, command, attributes):
        if command not in self.COMMANDS or self.state == 'faulted':
            raise GuardError('command unavailable')
        root = ET.Element('data')
        ET.SubElement(root, command, {k: str(v) for k, v in attributes.items()})
        packet = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        # All callers below construct fixed attributes. No raw XML or firmware
        # data is ever accepted as an outbound request.
        sent = self.transport.send(packet)
        if type(sent) is not int or sent != len(packet):
            raise GuardError('short transport write')

    def _run(self, action):
        if self.state == 'faulted':
            raise GuardError('session already faulted; no automatic recovery')
        try:
            return action(self.clock()+self.timeout)
        except Exception:
            self.state = 'faulted'
            self.geometry.clear()
            raise

    def configure(self):
        def action(deadline):
            if self.state != 'new':
                raise GuardError('session already configured')
            self._send('configure', {'MemoryName': 'ufs', 'Verbose': 0, 'AlwaysValidate': 0,
                       'MaxDigestTableSizeInBytes': 8192, 'MaxPayloadSizeToTargetInBytes': 1048576,
                       'ZlpAwareHost': 1, 'SkipStorageInit': 0, 'SkipWrite': 0, 'Oem': 'ZTE'})
            self._response(deadline)
            self.state = 'configured'
        return self._run(action)

    def confirm_geometry(self, lun):
        def action(deadline):
            integer(lun, 0, 31)
            if self.state != 'configured' or lun not in {r.lun for r in self.ranges}:
                raise GuardError('LUN not configured or outside plan')
            observations = []
            for _ in range(2):
                self._send('getstorageinfo', {'physical_partition_number': lun, 'MemoryName': 'ufs', 'slot': 0})
                logs = self._response(deadline)
                infos = []
                for log in logs:
                    if log.startswith('INFO: '):
                        log = log[6:]
                    if not log.startswith('{'):
                        continue
                    try:
                        data = json.loads(log, object_pairs_hook=unique_object)
                    except (ValueError, TypeError) as exc:
                        raise GuardError('invalid storage-info JSON') from exc
                    if type(data) is dict and 'storage_info' in data:
                        infos.append(data['storage_info'])
                if len(infos) != 1 or type(infos[0]) is not dict:
                    raise GuardError('missing or ambiguous storage geometry')
                info = infos[0]
                size = integer(info.get('block_size'), 512, 4096)
                if size not in (512, 4096):
                    raise GuardError('unsupported sector size')
                total = integer(info.get('total_blocks'), 1, 2**32)
                physical = integer(info.get('num_physical'), 1, 32)
                if lun >= physical or str(info.get('mem_type', '')).lower() != 'ufs':
                    raise GuardError('storage identity does not match request')
                observations.append(Geometry(size, total, physical))
            if observations[0] != observations[1]:
                raise GuardError('storage geometry changed between queries')
            self.geometry[lun] = observations[0]
            confirmed = self.geometry
            for r in self.ranges:
                if r.lun in confirmed and r.start+r.count > confirmed[r.lun].total_blocks:
                    raise GuardError('planned read exceeds storage capacity')
            if len(confirmed) == len({r.lun for r in self.ranges}):
                size = sum(r.count*confirmed[r.lun].sector_bytes for r in self.ranges)
                if size > self.max_total_bytes:
                    raise GuardError('planned read exceeds host byte budget')
            return observations[0]
        return self._run(action)

    def _read_once(self, lun, start, count, deadline):
        geometry = self.geometry[lun]
        self._send('read', {'physical_partition_number': lun, 'MemoryName': 'ufs', 'slot': 0,
                           'SECTOR_SIZE_IN_BYTES': geometry.sector_bytes,
                           'start_sector': start, 'num_partition_sectors': count})
        self._response(deadline, raw_mode=True)
        length = count*geometry.sector_bytes
        data = bytearray()
        while len(data) < length:
            if not self.buffer:
                self._receive(deadline)
            take = min(length-len(data), len(self.buffer))
            data.extend(self.buffer[:take])
            del self.buffer[:take]
        self._response(deadline, raw_mode=False)
        return bytes(data)

    def read_chunk(self, lun, start, count):
        def action(deadline):
            for number in (lun, start, count):
                integer(number, 0, 2**32-1)
            if self.state != 'configured' or set(self.geometry) != {r.lun for r in self.ranges}:
                raise GuardError('all planned LUN geometries must be confirmed first')
            if not count or not any(r.lun == lun and r.start <= start and start+count <= r.start+r.count for r in self.ranges):
                raise GuardError('read is outside authorized ranges')
            if count*self.geometry[lun].sector_bytes > self.MAX_CHUNK:
                raise GuardError('read chunk exceeds memory limit')
            first = self._read_once(lun, start, count, deadline)
            second = self._read_once(lun, start, count, deadline)
            if hashlib.sha256(first).digest() != hashlib.sha256(second).digest():
                raise GuardError('repeated reads differ')
            return first
        return self._run(action)

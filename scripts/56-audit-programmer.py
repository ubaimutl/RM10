#!/usr/bin/env python3
"""Inspect local Qualcomm images; no USB, device transport or flashing support.

Reports embedded certificate signatures, root-key overlap with reference
images, and limited MBNv7 checks. Embedded certificates alone do not authenticate
an entire image. MBNv7 authority views are checked separately; nonempty segments
with unexpected zero hashes remain unresolved. Requires host cryptography.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa


def sha(data):
    return hashlib.sha256(data).hexdigest()


def certificate_entries(data):
    entries = []
    for match in re.finditer(rb'\x30\x82', data):
        offset = match.start()
        if offset + 4 > len(data):
            continue
        size = 4 + int.from_bytes(data[offset+2:offset+4], 'big')
        if not 300 <= size <= 10000 or offset + size > len(data):
            continue
        der = data[offset:offset+size]
        try:
            cert = x509.load_der_x509_certificate(der)
        except ValueError:
            continue
        entries.append((offset, cert, der))
    return entries


def verify_certificate(cert, parent):
    key = parent.public_key()
    try:
        if isinstance(key, ec.EllipticCurvePublicKey):
            key.verify(cert.signature, cert.tbs_certificate_bytes,
                       ec.ECDSA(cert.signature_hash_algorithm))
        elif isinstance(key, rsa.RSAPublicKey):
            key.verify(cert.signature, cert.tbs_certificate_bytes,
                       getattr(cert, 'signature_algorithm_parameters', padding.PKCS1v15()),
                       cert.signature_hash_algorithm)
        else:
            return False
    except InvalidSignature:
        return False
    return True


def elf_segments(data, base):
    """Parse file offsets only. Never load or execute ELF contents."""
    if len(data)-base < 64 or data[base:base+4] != b'\x7fELF' or data[base+5] != 1:
        raise ValueError('unsupported ELF header')
    bits = data[base+4]
    if bits == 1:
        phoff = struct.unpack_from('<I', data, base+28)[0]
        entsize, count = struct.unpack_from('<HH', data, base+42)
        expected = 32
    elif bits == 2:
        phoff = struct.unpack_from('<Q', data, base+32)[0]
        entsize, count = struct.unpack_from('<HH', data, base+54)
        expected = 56
    else:
        raise ValueError('unsupported ELF class')
    if entsize != expected or not 1 <= count <= 256:
        raise ValueError('unsupported ELF program table')
    if base + phoff + entsize*count > len(data):
        raise ValueError('truncated ELF program table')
    result = []
    for index in range(count):
        offset = base+phoff+index*entsize
        if bits == 1:
            fields = struct.unpack_from('<8I', data, offset)
            relative, size, flags = fields[1], fields[4], fields[6]
        else:
            fields = struct.unpack_from('<II6Q', data, offset)
            relative, size, flags = fields[2], fields[5], fields[1]
        if base + relative + size > len(data):
            raise ValueError('truncated ELF segment')
        result.append((base+relative, size, flags))
    return result


def mbn_checks(data):
    rows = []
    for match in re.finditer(rb'\x7fELF', data):
        base = match.start()
        try:
            segments = elf_segments(data, base)
        except (ValueError, struct.error):
            continue
        for offset, size, flags in segments:
            if (flags >> 24) & 7 != 2:
                continue
            blob = data[offset:offset+size]
            if len(blob) < 64:
                raise ValueError('truncated MBN hash segment')
            h = struct.unpack_from('<10I', blob)
            row = {'elf_offset': base, 'hash_segment_offset': offset,
                   'mbn_version': h[1], 'oem_image_signature_verified': False}
            rows.append(row)
            if h[1] != 7:
                row['unresolved'] = 'only MBNv7 is handled'
                continue
            common, meta_qti, meta_oem, hash_size, sig_qti, cert_qti, sig_oem, cert_oem = h[2:]
            hash_start = 40 + common + meta_qti + meta_oem
            signed_end = hash_start + hash_size
            sig_start = signed_end + sig_qti + cert_qti
            cert_start = sig_start + sig_oem
            if (common != 24 or hash_size != 48*len(segments)
                    or cert_start+cert_oem > len(blob)):
                raise ValueError('unsupported MBNv7 sizes')
            row['software_id'] = struct.unpack_from('<I', blob, 48)[0]
            row['hash_algorithm_id'] = struct.unpack_from('<I', blob, 56)[0]
            if row['hash_algorithm_id'] != 3:
                raise ValueError('only SHA384 hash tables are supported')
            checks = []
            for i, (start, length, seg_flags) in enumerate(segments):
                expected = blob[hash_start+i*48:hash_start+(i+1)*48]
                is_hash = (seg_flags >> 24) & 7 == 2
                zero = expected == bytes(48)
                checks.append({'index': i, 'file_bytes': length, 'is_hash_segment': is_hash,
                               'zero_hash_entry': zero,
                               'sha384_matches': expected == hashlib.sha384(data[start:start+length]).digest()})
            row['segment_hash_checks'] = checks
            row['nonzero_segment_hashes_match'] = all(c['sha384_matches'] for c in checks if not c['zero_hash_entry'])
            row['unverified_zero_nonhash_entries'] = [c['index'] for c in checks if c['zero_hash_entry'] and not c['is_hash_segment'] and c['file_bytes']]

            def authority_signature(authority):
                # Each authority signs a view with the other authority's
                # lengths and metadata zeroed, retaining their byte positions.
                view = bytearray(blob[:signed_end])
                if authority == 'oem':
                    view[24:32] = bytes(8)
                    view[40+common:40+common+meta_qti] = bytes(meta_qti)
                    ss, sn, cs, cn = sig_start, sig_oem, cert_start, cert_oem
                else:
                    view[32:40] = bytes(8)
                    view[40+common+meta_qti:hash_start] = bytes(meta_oem)
                    ss, sn, cs, cn = signed_end, sig_qti, signed_end+sig_qti, cert_qti
                chain = certificate_entries(blob[cs:cs+cn])
                if not chain or chain[0][0] != 0:
                    raise ValueError('missing authority leaf certificate')
                signature = blob[ss:ss+sn]
                if len(signature) < 2 or signature[0] != 0x30 or signature[1] >= 128:
                    raise ValueError('unsupported ECDSA signature encoding')
                signature = signature[:signature[1]+2]
                key = chain[0][1].public_key()
                if not isinstance(key, ec.EllipticCurvePublicKey):
                    raise ValueError('only ECDSA image signatures are supported')
                try:
                    key.verify(signature, bytes(view), ec.ECDSA(hashes.SHA384()))
                    return True
                except InvalidSignature:
                    return False

            row['oem_image_signature_verified'] = authority_signature('oem')
            if sig_qti or cert_qti:
                row['qti_image_signature_verified'] = authority_signature('qti')
                row['dual_authority_view_normalization'] = 'other authority lengths and metadata bytes zeroed'
    return rows


def audit(path):
    data = Path(path).read_bytes()
    entries = certificate_entries(data)
    certificates = []
    for offset, cert, der in entries:
        spki = cert.public_key().public_bytes(serialization.Encoding.DER,
                                              serialization.PublicFormat.SubjectPublicKeyInfo)
        parents = sorted(set(sha(parent_der) for _, parent, parent_der in entries
                             if cert.issuer == parent.subject and verify_certificate(cert, parent)))
        certificates.append({'offset': offset, 'der_sha256': sha(der), 'spki_sha256': sha(spki),
                             'subject': cert.subject.rfc4514_string(),
                             'self_issued': cert.issuer == cert.subject,
                             'verified_parent_der_sha256': parents})
    return {'bytes': len(data), 'sha256': sha(data), 'certificates': certificates,
            'mbnv7': mbn_checks(data),
            'complete_programmer_authentication_established': False,
            'hardware_acceptance_established': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--reference', action='append', type=Path, default=[])
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('refusing to overwrite an existing report')
    image = audit(args.image)
    roots = {r['spki_sha256'] for r in image['certificates'] if r['self_issued'] and r['verified_parent_der_sha256']}
    references = []
    for path in args.reference:
        report = audit(path)
        report['matching_embedded_root_spki_sha256'] = sorted(roots.intersection(
            r['spki_sha256'] for r in report['certificates'] if r['self_issued'] and r['verified_parent_der_sha256']))
        references.append(report)
    # No paths, serials or device captures are included in the report.
    args.output.write_text(json.dumps({'schema': 1, 'image': image, 'references': references,
                                      'hardware_test_authorized': False}, indent=2)+'\n')
    print('Saved host-only image audit; this report does not authorize loader execution.')


if __name__ == '__main__':
    main()

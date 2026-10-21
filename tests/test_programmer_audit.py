"""Synthetic signed-image controls; no firmware or hardware is required."""
import datetime
import hashlib
import importlib.util
from pathlib import Path
import struct
import unittest

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

spec = importlib.util.spec_from_file_location(
    'programmer_audit', Path(__file__).resolve().parents[1]/'scripts/56-audit-programmer.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def fixture(dual=False):
    key = ec.generate_private_key(ec.SECP384R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Synthetic host fixture')])
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(key.public_key()).serial_number(1)
            .not_valid_before(datetime.datetime(2020, 1, 1))
            .not_valid_after(datetime.datetime(2030, 1, 1))
            .sign(key, hashes.SHA384()).public_bytes(serialization.Encoding.DER))
    qti = 3464 if dual else 0
    signed = (struct.pack('<10I', 0, 7, 24, 0, 224, 144,
                          104 if dual else 0, 3360 if dual else 0, 104, 3360)
              + struct.pack('<6I', 0, 0, 37, 0, 3, 0) + bytes(224))
    signed_size = len(signed) + 144
    hash_size = signed_size + qti + 104 + 3360
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    header = ident + struct.pack('<HHIQQQIHHHHHH', 2, 183, 1, 0, 64, 0, 0, 64, 56, 3, 0, 0, 0)
    ph = (struct.pack('<II6Q', 0, 0x07000000, 0, 0, 0, 232, 0, 8)
          + struct.pack('<II6Q', 1, 7, 4096, 0, 0, 128, 128, 4096)
          + struct.pack('<II6Q', 0, 0x02000000, 8192, 0, 0, hash_size, hash_size, 4096))
    code = bytes(range(128))
    signed += hashlib.sha384(header+ph).digest() + hashlib.sha384(code).digest() + bytes(48)
    oem_view = bytearray(signed)
    oem_view[24:32] = bytes(8)
    signature = key.sign(bytes(oem_view), ec.ECDSA(hashes.SHA384())).ljust(104, b'\0')
    qti_data = b''
    if dual:
        qti_view = bytearray(signed)
        qti_view[32:40] = bytes(8)
        qti_view[64:288] = bytes(224)
        qti_data = (key.sign(bytes(qti_view), ec.ECDSA(hashes.SHA384())).ljust(104, b'\0')
                    + cert.ljust(3360, b'\xff'))
    blob = signed + qti_data + signature + cert.ljust(3360, b'\xff')
    data = bytearray(8192+len(blob))
    data[:232] = header+ph
    data[4096:4224] = code
    data[8192:] = blob
    return bytes(data)


class ProgrammerAuditTests(unittest.TestCase):
    def test_signed_table_and_referenced_bytes_verify(self):
        data = fixture()
        row = audit.mbn_checks(data)[0]
        self.assertTrue(row['oem_image_signature_verified'])
        self.assertTrue(row['nonzero_segment_hashes_match'])
        self.assertEqual(row['unverified_zero_nonhash_entries'], [])
        _, cert, _ = audit.certificate_entries(data)[0]
        self.assertTrue(audit.verify_certificate(cert, cert))

    def test_code_corruption_is_detected_despite_intact_signature(self):
        data = bytearray(fixture())
        data[4100] ^= 1
        row = audit.mbn_checks(bytes(data))[0]
        self.assertTrue(row['oem_image_signature_verified'])
        self.assertFalse(row['nonzero_segment_hashes_match'])

    def test_signed_table_corruption_is_detected(self):
        data = bytearray(fixture())
        data[8192+64+224+48] ^= 1
        row = audit.mbn_checks(bytes(data))[0]
        self.assertFalse(row['oem_image_signature_verified'])
        self.assertFalse(row['nonzero_segment_hashes_match'])

    def test_dual_authority_views_verify_independently(self):
        row = audit.mbn_checks(fixture(dual=True))[0]
        self.assertTrue(row['oem_image_signature_verified'])
        self.assertTrue(row['qti_image_signature_verified'])

    def test_corrupt_qti_signature_does_not_falsely_pass(self):
        data = bytearray(fixture(dual=True))
        data[8192+64+224+144+20] ^= 1
        row = audit.mbn_checks(bytes(data))[0]
        self.assertTrue(row['oem_image_signature_verified'])
        self.assertFalse(row['qti_image_signature_verified'])


if __name__ == '__main__':
    unittest.main()

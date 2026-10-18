# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Benjamin Dehli
"""Tests for the Python tools against Moog's official v1.3.0 firmware.

Set MATRIARCH_FIRMWARE to the path of Matriarch_Firmware_v1_3_0.syx. The tests are skipped otherwise.
Run: python3 -m unittest discover -s tests -v
"""

import hashlib
import json
import os
import struct
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))

import patch_holdcc  # noqa: E402
from matriarch_syx import Firmware  # noqa: E402
from patch_mixgate import patch  # noqa: E402

EXPECTED = json.load(open(os.path.join(HERE, 'expected.json')))
SOURCE = os.environ.get('MATRIARCH_FIRMWARE')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(SOURCE, 'set MATRIARCH_FIRMWARE to the official v1.3.0 .syx')
class PatchTests(unittest.TestCase):
    def setUp(self):
        with open(SOURCE, 'rb') as f:
            self.original = f.read()

    def test_source_is_official_v1_3_0(self):
        self.assertEqual(sha256(self.original), EXPECTED['source']['sha256'])
        self.assertEqual(Firmware(SOURCE).version, '1.3.0')

    def test_round_trip_is_byte_identical(self):
        fw = Firmware(SOURCE)
        fw.write(0x88000, fw.read(0x88000))
        self.assertEqual(bytes(fw.raw), self.original)

    def test_mixgate_patch_matches_hardware_tested_builds(self):
        for ms, expected in EXPECTED['mixgate'].items():
            with self.subTest(ms=ms):
                fw = Firmware(SOURCE)
                patch(fw, float(ms))
                self.assertEqual(sha256(bytes(fw.raw)), expected)

    def test_mixgate_patch_changes_only_two_words(self):
        fw = Firmware(SOURCE)
        patch(fw, 5)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'patched.syx')
            fw.save(path)
            patched = Firmware(path)
        self.assertTrue(all(r.checksum_ok() for r in patched.records))
        _, a = Firmware(SOURCE).image()
        _, b = patched.image()
        wa = struct.unpack(f'<{len(a) // 2}H', a)
        wb = struct.unpack(f'<{len(b) // 2}H', b)
        changed = [0x88000 + i for i, (x, y) in enumerate(zip(wa, wb)) if x != y]
        self.assertEqual(changed, [0x8B991, 0x8B992])

    def test_refuses_to_patch_twice(self):
        fw = Firmware(SOURCE)
        patch(fw, 5)
        with self.assertRaises(ValueError):
            patch(fw, 50)
        patch_holdcc.patch(fw)
        with self.assertRaises(ValueError):
            patch_holdcc.patch(fw)

    def test_hold_patch_matches_expected(self):
        fw = Firmware(SOURCE)
        self.assertFalse(patch_holdcc.is_applied(fw))
        patch_holdcc.patch(fw)
        self.assertTrue(patch_holdcc.is_applied(fw))
        self.assertEqual(sha256(bytes(fw.raw)), EXPECTED['hold'])

    def test_hold_patch_changes_only_its_words(self):
        fw = Firmware(SOURCE)
        patch_holdcc.patch(fw)
        _, a = Firmware(SOURCE).image()
        _, b = fw.image()
        wa = struct.unpack(f'<{len(a) // 2}H', a)
        wb = struct.unpack(f'<{len(b) // 2}H', b)
        changed = {0x88000 + i for i, (x, y) in enumerate(zip(wa, wb)) if x != y}
        expected = {0x893AC, 0x893AD, 0x8C5BD, 0x8C5BE}
        expected |= set(range(0xA2000, 0xA200C)) | set(range(0xA2010, 0xA2033))
        self.assertEqual(changed, expected)

    def test_fixes_combine_in_any_order(self):
        for ms, expected in EXPECTED['mixgate_hold'].items():
            with self.subTest(ms=ms):
                first = Firmware(SOURCE)
                patch(first, float(ms))
                patch_holdcc.patch(first)
                second = Firmware(SOURCE)
                patch_holdcc.patch(second)
                patch(second, float(ms))
                self.assertEqual(sha256(bytes(first.raw)), expected)
                self.assertEqual(bytes(first.raw), bytes(second.raw))


if __name__ == '__main__':
    unittest.main()

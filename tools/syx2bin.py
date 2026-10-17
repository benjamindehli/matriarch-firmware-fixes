# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Benjamin Dehli
"""Extract a flat firmware image from a Matriarch .syx file.

Usage: python3 syx2bin.py <firmware.syx> <out.bin>

The image is little-endian 16-bit words, loaded at C28x word address 0x88000.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matriarch_syx import Firmware  # noqa: E402

if __name__ == '__main__':
    fw = Firmware(sys.argv[1])
    print('header:', ' '.join(f'{w:04x}' for w in fw.records[0].words))
    base, image = fw.image()
    open(sys.argv[2], 'wb').write(image)
    words = len(image) // 2
    print(f'range 0x{base:x}-0x{base + words:x} ({words} words)')

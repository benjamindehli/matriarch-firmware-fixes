# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Benjamin Dehli
"""Fix "Paraphonic Mixer Gate Length" in Matriarch firmware v1.3.0.

In 2- and 4-note paraphonic mode, when a key is released while other keys are
still held, the released oscillator's mixer gate is closed only after a fixed
delay. v1.3.0 initialises that delay to 125000 us (125 ms) in the engine init
code, so short or overlapping notes keep sounding for an extra 125 ms.

  0008b98f  8d00 0ef4   MOVL XAR0,#0xef4
  0008b991  8f01 e848   MOVL XAR4,#0x1e848      ; 125000 us
  0008b994  a893        MOVL *+XAR3[AR0],XAR4   ; engine.mixGateReleaseDelay

This rewrites the immediate of the MOVL at 0x8b991.

Usage: python3 patch_mixgate.py <in.syx> <out.syx> [--ms 50]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matriarch_syx import Firmware  # noqa: E402

SITE = 0x8B991
ORIGINAL = [0x8F01, 0xE848]  # MOVL XAR4,#125000


def movl_xar4(value):
    assert 0 <= value < 1 << 22
    return [0x8F00 | (value >> 16), value & 0xFFFF]


def patch(fw, ms):
    """Set the mixer gate release delay in a v1.3.0 Firmware. Returns the delay in us."""
    if fw.read(SITE, 2) != ORIGINAL:
        found = ' '.join(f'{w:04x}' for w in fw.read(SITE, 2))
        raise ValueError(f'unexpected code at 0x{SITE:x}: {found} (only unpatched v1.3.0 is supported)')
    us = int(round(ms * 1000))
    if not 0 <= us < 1 << 22:
        raise ValueError(f'delay out of range: {ms} ms')
    fw.write(SITE, movl_xar4(us))
    return us


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--ms', type=float, default=50.0, help='mixer gate hold in ms (v1.3.0: 125, recommended: 50)')
    args = ap.parse_args()

    fw = Firmware(args.src)
    try:
        us = patch(fw, args.ms)
    except ValueError as e:
        sys.exit(str(e))
    fw.save(args.dst)
    print(f'patched mixer gate release delay: 125000 us -> {us} us')


if __name__ == '__main__':
    main()

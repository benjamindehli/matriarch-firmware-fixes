# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Benjamin Dehli
"""Apply one or more fixes to Moog Matriarch firmware v1.3.0.

Usage: python3 patch.py <in.syx> <out.syx> [--mixgate MS] [--hold]

  --mixgate MS  paraphonic mixer gate hold after key-up, in ms (v1.3.0: 125). See patch_mixgate.py.
  --hold        HOLD sends sustain (CC 64) only while the Arp/Seq isn't running. See patch_holdcc.py.

The fixes change separate parts of the firmware, so they can be combined in any order.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_holdcc  # noqa: E402
import patch_mixgate  # noqa: E402
from matriarch_syx import Firmware  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description='Apply fixes to Moog Matriarch firmware v1.3.0.')
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--mixgate', type=float, metavar='MS', help='paraphonic mixer gate hold in ms (recommended: 5)')
    ap.add_argument('--hold', action='store_true', help='HOLD sends sustain only while the Arp/Seq is stopped')
    args = ap.parse_args()
    if args.mixgate is None and not args.hold:
        ap.error('choose at least one fix: --mixgate MS and/or --hold')

    fw = Firmware(args.src)
    try:
        if args.mixgate is not None:
            us = patch_mixgate.patch(fw, args.mixgate)
            print(f'paraphonic mixer gate: 125000 us -> {us} us')
        if args.hold:
            patch_holdcc.patch(fw)
            print('HOLD: sustain CC 64 only while the Arp/Seq is stopped')
    except ValueError as e:
        sys.exit(str(e))
    fw.save(args.dst)


if __name__ == '__main__':
    main()

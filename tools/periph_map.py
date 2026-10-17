# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Benjamin Dehli
"""Show which functions touch which F2837x peripherals.

Usage: python3 periph_map.py <refs.tsv>

refs.tsv comes from ghidra_scripts/ExportDecomp.java (function, source, target, reference type).
"""

import collections
import sys

# (first word address, end word address, name) of the F2837x peripheral frames
BLOCKS = [
    (0xB00, 0xB80, 'ADCRESULT'),
    (0xC00, 0xC18, 'TIMER'),
    (0xCE0, 0xD00, 'PIECTRL'),
    (0xD00, 0xE00, 'PIEVECT'),
    (0x1000, 0x1200, 'DMA'),
    (0x1400, 0x1580, 'CLA'),
    (0x4000, 0x4C00, 'EPWM'),
    (0x5000, 0x50C0, 'ECAP'),
    (0x5C00, 0x5C80, 'DAC'),
    (0x6000, 0x6100, 'MCBSP'),
    (0x6100, 0x6110, 'SPIA'),
    (0x6110, 0x6120, 'SPIB'),
    (0x6120, 0x6130, 'SPIC'),
    (0x6200, 0x6300, 'UPP'),
    (0x7000, 0x7040, 'WD'),
    (0x7200, 0x7210, 'SCIA'),
    (0x7210, 0x7220, 'SCIB'),
    (0x7220, 0x7230, 'SCIC'),
    (0x7230, 0x7240, 'SCID'),
    (0x7300, 0x7380, 'I2C'),
    (0x7400, 0x7600, 'ADC'),
    (0x7C00, 0x7F00, 'GPIOCTRL'),
    (0x7F00, 0x8000, 'GPIODAT'),
    (0x40000, 0x41000, 'USB'),
    (0x47000, 0x48000, 'EMIF'),
    (0x5F800, 0x5FC00, 'FLASHCTL'),
]


def main():
    per_function = collections.defaultdict(collections.Counter)
    with open(sys.argv[1]) as refs:
        for line in refs:
            function, _source, target, _kind = line.rstrip('\n').split('\t')
            try:
                addr = int(target.split(':')[-1], 16)
            except ValueError:
                continue
            for lo, hi, name in BLOCKS:
                if lo <= addr < hi:
                    per_function[function][name] += 1

    per_peripheral = collections.defaultdict(list)
    for function, names in per_function.items():
        for name in names:
            per_peripheral[name].append(function)
    for name in sorted(per_peripheral):
        functions = sorted(per_peripheral[name])
        print(name, len(functions), ' '.join(functions[:25]))


if __name__ == '__main__':
    main()

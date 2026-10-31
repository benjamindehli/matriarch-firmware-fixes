# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Benjamin Dehli
"""Fix "Paraphonic Mixer Gate Length" in Matriarch firmware v1.3.0.

In 2- and 4-note paraphonic mode, when a key is released while other keys are still held, the released
oscillator's mixer gate is closed only after a hold time. v1.3.0 sets the hold to 125000 us (125 ms):

  0008b98f  8d00 0ef4   MOVL XAR0,#0xef4
  0008b991  8f01 e848   MOVL XAR4,#0x1e848      ; 125000 us
  0008b994  a893        MOVL *+XAR3[AR0],XAR4   ; engine.mixGateReleaseDelay

Note-off (0x88de4) marks every released oscillator pending with a timestamp, and the main loop
(0x8a81d) closes its gate once the hold has passed, but only if other keys are still down. Every
note-off restarts the timer for all pending gates. So the hold does two jobs: it delays the cut-off
(which smears staccato), and it groups releases, so a lifted chord rings out with the envelope release
only if each key comes up within the hold time of the previous one. Shortening the hold (v1.x of this
project) fixed staccato but cut off chord releases with a long release time.

This fix keeps Moog's 125 ms for chords and uses a short hold only for notes that weren't pressed
together with a key that's still held. It records each oscillator's press time in its voice record's
timestamp field (+6, only used while a release is pending) and decides at note-off:

  note-on   0x88ca9  LCR 0x000a2040 (was LCR 0x00088a24, the gate assignment)
            0xa2040  remembers the old gate flags, calls 0x88a24, and stores the current time
                     in the timestamp of every oscillator that became gated
  note-off  0x88e65  LCR 0x000a2080, SB 0x00088e91 (replaces Moog's "mark released gates pending")
            0xa2080  for each oscillator whose gate flag is 0:
                       pending 1 (Moog's window): restart its timer, as Moog does
                       pending 2 (short hold): leave it alone
                       pending 0 (just released): if any held oscillator was pressed within
                         40 ms of it, pending 1 with Moog's window. Otherwise pending 2, with
                         the timestamp back-dated so the 125 ms timer runs out after the short hold,
                         and every oscillator still at pending 1 gets the same: its chord is no
                         longer held, so notes pressed together over a held key stop together

The short hold is the immediate of MOVL XAR5,#us at 0xa20a7. The main loop, the gate closing and the
"keep gates open when the last key comes up" logic are Moog's, unchanged.

With --simple, the fix instead changes Moog's 125 ms value at 0x8b991, as v1.0.0 to v1.2.0 of this
project did. Every note released while other keys are held then stops after the hold, so with a short
hold a chord lifted with a long release keeps only its last note or two.

Usage: python3 patch_mixgate.py <in.syx> <out.syx> [--ms 5] [--simple]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matriarch_syx import Firmware  # noqa: E402

HOLD_SITE = 0x8B991
HOLD_ORIGINAL = [0x8F01, 0xE848]  # MOVL XAR4,#125000, changed only in simple mode

NOTE_ON_SITE = 0x88CA9
NOTE_ON_ORIGINAL = [0x7648, 0x8A24]  # LCR 0x00088a24
NOTE_ON_PATCHED = [0x764A, 0x2040]  # LCR 0x000a2040

NOTE_OFF_SITE = 0x88E65
NOTE_OFF_ORIGINAL = [0x8D00, 0x02A2, 0x9292]  # MOVL XAR0,#0x2a2 ; MOV AL,*+XAR2[AR0]
NOTE_OFF_PATCHED = [0x764A, 0x2080, 0x6F2A]  # LCR 0x000a2080 ; SB 0x00088e91,UNC

NOTE_ON_ADDR = 0xA2040
NOTE_ON = [
    0xB2BD, 0xA2BD, 0xFE04, 0x8BA4, 0x82A9, 0x06A1, 0xFF10, 0x02A2, 0x8AA9, 0x92C4, 0x9641, 0xDC08,
    0x92C4, 0x9642, 0xDC08, 0x92C4, 0x9643, 0xDC08, 0x92C4, 0x9644, 0x06A3, 0x8AA1, 0x7648, 0x8A24,
    0x8F00, 0xC080, 0x7649, 0xB905, 0x82A9, 0x06A1, 0xFF10, 0x02A2, 0x8AA9, 0x92C4, 0x6104, 0x9241,
    0x6002, 0xA2D4, 0xDC08, 0x92C4, 0x6104, 0x9242, 0x6002, 0xA2D4, 0xDC08, 0x92C4, 0x6104, 0x9243,
    0x6002, 0xA2D4, 0xDC08, 0x92C4, 0x6104, 0x9244, 0x6002, 0xA2D4, 0xFE84, 0x82BE, 0x8BBE, 0x0006,
]  # fmt: skip

NOTE_OFF_ADDR = 0xA2080
NOTE_OFF = [
    0xB2BD, 0xFE02, 0x2841, 0x0004, 0x06A2, 0xFF10, 0x02A2, 0x8BA9, 0x92C1, 0x6035, 0x92C9, 0x5201,
    0x6131, 0x5202, 0x6130, 0xC4D1, 0x06A2, 0xFF10, 0x02A2, 0x8AA9, 0xB603, 0x92C4, 0x6108, 0x06D4,
    0x03A6, 0xFF56, 0x8F40, 0x9C40, 0x0FA5, 0x681E, 0xDC08, 0x000F, 0xFFF6, 0x28C9, 0x0002, 0x8D00,
    0x0EF4, 0x06A3, 0x0392, 0x8F40, 0x1388, 0x07A5, 0x1ED1, 0xC4A9, 0x06A2, 0xFF10, 0x02A2, 0x8AA9,
    0xB603, 0x92CC, 0x5201, 0x6004, 0x28CC, 0x0002, 0xC2D4, 0xDC08, 0x000F, 0xFFF9, 0x6F04, 0x28C9,
    0x0001, 0xA2D1, 0xD908, 0x0B41, 0x60C8, 0xFE82, 0x8BBE, 0x0006,
]  # fmt: skip
SHORT_OFFSET = 39  # MOVL XAR5,#short at NOTE_OFF_ADDR + 39

CODE_START = NOTE_ON_ADDR
CODE_END = NOTE_OFF_ADDR + len(NOTE_OFF)


def movl_xar4(value):
    return [0x8F00 | (value >> 16), value & 0xFFFF]


def movl_xar5(value):
    return [0x8F40 | (value >> 16), value & 0xFFFF]


def short_hold_us(fw):
    """The short hold in a patched Firmware, in us, or None if this fix isn't applied."""
    if fw.read(NOTE_ON_SITE, 2) != NOTE_ON_PATCHED or fw.read(NOTE_OFF_SITE, 3) != NOTE_OFF_PATCHED:
        return None
    hi, lo = fw.read(NOTE_OFF_ADDR + SHORT_OFFSET, 2)
    return ((hi & 0x3F) << 16) | lo


def simple_hold_us(fw):
    """The hold in a Firmware patched with --simple (or v1.0.0 to v1.2.0 of this project), in us, or None."""
    hi, lo = fw.read(HOLD_SITE, 2)
    if hi & 0xFFC0 != 0x8F00 or [hi, lo] == HOLD_ORIGINAL:
        return None
    return ((hi & 0x3F) << 16) | lo


def is_unpatched(fw):
    return (
        fw.read(HOLD_SITE, 2) == HOLD_ORIGINAL
        and fw.read(NOTE_ON_SITE, 2) == NOTE_ON_ORIGINAL
        and fw.read(NOTE_OFF_SITE, 3) == NOTE_OFF_ORIGINAL
        and set(fw.read(CODE_START, CODE_END - CODE_START)) == {0xFFFF}
    )


def patch(fw, ms, simple=False):
    """Set the short mixer gate hold in a v1.3.0 Firmware, chord-aware unless simple. Returns the hold in us."""
    if not is_unpatched(fw):
        short = short_hold_us(fw)
        plain = simple_hold_us(fw)
        if short is not None:
            reason = f'it already has the chord-aware mixer gate fix ({short / 1000:g} ms)'
        elif plain is not None:
            reason = f'it already has the simple mixer gate fix ({plain / 1000:g} ms)'
        else:
            reason = 'it is not unpatched Matriarch firmware v1.3.0'
        raise ValueError(f"can't patch this file: {reason}. Start from Moog's original v1.3.0 file.")
    us = int(round(ms * 1000))
    if not 0 <= us <= 125000:
        raise ValueError(f'hold out of range: {ms} ms (0 to 125)')
    if simple:
        fw.write(HOLD_SITE, movl_xar4(us))
        return us
    off = list(NOTE_OFF)
    off[SHORT_OFFSET : SHORT_OFFSET + 2] = movl_xar5(us)
    fw.write(NOTE_ON_ADDR, NOTE_ON)
    fw.write(NOTE_OFF_ADDR, off)
    fw.write(NOTE_ON_SITE, NOTE_ON_PATCHED)
    fw.write(NOTE_OFF_SITE, NOTE_OFF_PATCHED)
    return us


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--ms', type=float, default=5.0, help='mixer gate hold in ms (v1.3.0: 125, recommended: 5)')
    ap.add_argument('--simple', action='store_true', help='the same hold for every note, chords included')
    args = ap.parse_args()

    fw = Firmware(args.src)
    try:
        us = patch(fw, args.ms, args.simple)
    except ValueError as e:
        sys.exit(str(e))
    fw.save(args.dst)
    if args.simple:
        print(f'patched mixer gate: released notes {us} us, chords included')
    else:
        print(f'patched mixer gate: chords keep 125000 us, other released notes {us} us')


if __name__ == '__main__':
    main()

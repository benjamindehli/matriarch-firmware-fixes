# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Benjamin Dehli
"""Fix "ARP sends Sustain CC while Hold is active" in Matriarch firmware v1.3.0.

Since v1.2.x the HOLD button doubles as a sustain pedal when the Arp/Seq isn't running, and sends
MIDI CC 64 then. The HOLD handler (0x8c5a5) sends CC 64 whether or not the Arp/Seq is running, so
latching an arpeggio also sustains notes on connected gear. The handler ends with

  0008c5b8  9224        MOV  AL,@0x24          ; 0xc8a4 = global "MIDI Out Filter - Keys"
  0008c5ba  56b0 01a8   MOVB @AH,#0x1,NEQ      ; AH = send CC 64
  0008c5bc  92a6        MOV  AL,@AR6           ; AL = new HOLD state
  0008c5bd  7648 c56b   LCR  0x0008c56b        ; sustain(on, send): sets KB hold, sends CC 64

The patch redirects that call to a few new instructions in empty flash (sector H, unused after
0xa1c3f) that stop CC 64 "on" while the Arp/Seq is playing, then continue into Moog's code:

  000a2000  5300        CMPB AH,#0x0
  000a2001  6109        SB   0xa200a,EQ        ; not sending anyway
  000a2002  5200        CMPB AL,#0x0
  000a2003  6107        SB   0xa200a,EQ        ; HOLD off: always send CC 64 = 0
  000a2004  8f00 e4ff   MOVL XAR4,#0xe4ff      ; Arp/Seq object 0xe4c0, +0x3f = playing
  000a2006  1bc4 0000   CMP  *+XAR4[0x0],#0x0
  000a2008  56b0 00a8   MOVB @AH,#0x0,NEQ      ; playing: don't send CC 64 = 64
  000a200a  0048 c56b   LB   0x0008c56b        ; tail-jump, returns to the HOLD handler

The Arp/Seq latch itself (0xe4c0 + 0xa5) can't be used: the HOLD parameter's handler runs from an
event queue after this code.

Whether the Arp/Seq is running also changes when it's started or stopped while HOLD is on, so the
PLAY parameter's handler (0x893a3) gets the same treatment. Its call to the Arp/Seq start/stop
routine 0x90b88 (the only caller) goes through a wrapper that resyncs CC 64 when the state changes:

  000a2010  b2bd        MOVL *SP++,XAR1
  000a2011  aabd        MOVL *SP++,XAR2
  000a2012  8d40 e4ff   MOVL XAR1,#0xe4ff      ; Arp/Seq playing flag
  000a2014  5ac1        MOVZ AR2,*+XAR1[0x0]   ; playing before
  000a2015  7649 0b88   LCR  0x00090b88        ; Moog's start/stop
  000a2017  92c1        MOV  AL,*+XAR1[0x0]    ; playing after
  000a2018  54a2        CMP  AL,@AR2
  000a2019  6117        SB   0xa2030,EQ        ; unchanged
  000a201a  8f01 13b9   MOVL XAR4,#0x113b9     ; HOLD parameter
  000a201c  93c4        MOV  AH,*+XAR4[0x0]
  000a201d  6113        SB   0xa2030,EQ        ; HOLD off
  000a201e  8f00 c8a4   MOVL XAR4,#0xc8a4      ; "MIDI Out Filter - Keys"
  000a2020  93c4        MOV  AH,*+XAR4[0x0]
  000a2021  610f        SB   0xa2030,EQ        ; filtered
  000a2022  5200        CMPB AL,#0x0
  000a2023  6107        SB   0xa202a,EQ        ; stopped
  000a2024  8f01 3443   MOVL XAR4,#0x13443     ; sustain pedal state
  000a2026  93c4        MOV  AH,*+XAR4[0x0]
  000a2027  6009        SB   0xa2030,NEQ       ; pedal down: keep sustaining
  000a2028  9b00        MOVB AH,#0x0           ; started: CC 64 = 0
  000a2029  6f02        SB   0xa202b,UNC
  000a202a  9b40        MOVB AH,#0x40          ; stopped: CC 64 = 64
  000a202b  9a40        MOVB AL,#0x40
  000a202c  8f00 cdc0   MOVL XAR4,#0xcdc0      ; MIDI out, honours the output port setting
  000a202e  7649 7037   LCR  0x00097037        ; send CC
  000a2030  86be        MOVL XAR2,*--SP
  000a2031  8bbe        MOVL XAR1,*--SP
  000a2032  0006        LRETR

So connected gear sustains exactly when HOLD is on and the Arp/Seq isn't running. Internal sustain
behaviour is unchanged. Only the MIDI output differs.

Usage: python3 patch_holdcc.py <in.syx> <out.syx>
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matriarch_syx import Firmware  # noqa: E402

CALL_SITE = 0x8C5BD
ORIGINAL_CALL = [0x7648, 0xC56B]  # LCR 0x0008c56b
PATCHED_CALL = [0x764A, 0x2000]  # LCR 0x000a2000

STUB_ADDR = 0xA2000
STUB = [0x5300, 0x6109, 0x5200, 0x6107, 0x8F00, 0xE4FF, 0x1BC4, 0x0000, 0x56B0, 0x00A8, 0x0048, 0xC56B]

PLAY_SITE = 0x893AC
ORIGINAL_PLAY_CALL = [0x7649, 0x0B88]  # LCR 0x00090b88
PATCHED_PLAY_CALL = [0x764A, 0x2010]  # LCR 0x000a2010

WRAPPER_ADDR = 0xA2010
WRAPPER = [
    0xB2BD, 0xAABD, 0x8D40, 0xE4FF, 0x5AC1, 0x7649, 0x0B88, 0x92C1, 0x54A2, 0x6117, 0x8F01, 0x13B9,
    0x93C4, 0x6113, 0x8F00, 0xC8A4, 0x93C4, 0x610F, 0x5200, 0x6107, 0x8F01, 0x3443, 0x93C4, 0x6009,
    0x9B00, 0x6F02, 0x9B40, 0x9A40, 0x8F00, 0xCDC0, 0x7649, 0x7037, 0x86BE, 0x8BBE, 0x0006,
]  # fmt: skip


def is_applied(fw):
    return (
        fw.read(CALL_SITE, 2) == PATCHED_CALL
        and fw.read(STUB_ADDR, len(STUB)) == STUB
        and fw.read(PLAY_SITE, 2) == PATCHED_PLAY_CALL
        and fw.read(WRAPPER_ADDR, len(WRAPPER)) == WRAPPER
    )


def patch(fw):
    """Apply the fix to a v1.3.0 Firmware."""
    free = fw.read(STUB_ADDR, WRAPPER_ADDR + len(WRAPPER) - STUB_ADDR)
    if fw.read(CALL_SITE, 2) != ORIGINAL_CALL or fw.read(PLAY_SITE, 2) != ORIGINAL_PLAY_CALL or set(free) != {0xFFFF}:
        found = ' '.join(f'{w:04x}' for w in fw.read(CALL_SITE, 2))
        raise ValueError(f'unexpected code at 0x{CALL_SITE:x}: {found} (only unpatched v1.3.0 is supported)')
    fw.write(STUB_ADDR, STUB)
    fw.write(WRAPPER_ADDR, WRAPPER)
    fw.write(CALL_SITE, PATCHED_CALL)
    fw.write(PLAY_SITE, PATCHED_PLAY_CALL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    args = ap.parse_args()

    fw = Firmware(args.src)
    try:
        patch(fw)
    except ValueError as e:
        sys.exit(str(e))
    fw.save(args.dst)
    print('patched HOLD: sustain CC 64 only while the Arp/Seq is stopped')


if __name__ == '__main__':
    main()

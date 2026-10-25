// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Benjamin Dehli
//
// The fixes the web patcher can apply. A port of tools/patch_mixgate.py and tools/patch_holdcc.py.

import { FirmwareError } from "./matriarch-syx.js";

/** SHA-256 of Moog's official Matriarch_Firmware_v1_3_0.syx, the only file the fixes are made for. */
export const OFFICIAL_V1_3_0_SHA256 = "2f414599472e928fccfba687b9fa4bb8639fdd8a9573ace1df408ed587ad6f67";

const equal = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);

// Mixer gate fix: see tools/patch_mixgate.py for the description.
const MIXGATE_HOLD_SITE = 0x8b991;
const MIXGATE_HOLD_ORIGINAL = [0x8f01, 0xe848]; // MOVL XAR4,#125000, left unchanged
const NOTE_ON_SITE = 0x88ca9;
const NOTE_ON_ORIGINAL = [0x7648, 0x8a24]; // LCR 0x00088a24
const NOTE_ON_PATCHED = [0x764a, 0x2040]; // LCR 0x000a2040
const NOTE_OFF_SITE = 0x88e65;
const NOTE_OFF_ORIGINAL = [0x8d00, 0x02a2, 0x9292];
const NOTE_OFF_PATCHED = [0x764a, 0x2080, 0x6f2a]; // LCR 0x000a2080 ; SB 0x00088e91,UNC
const NOTE_ON_ADDR = 0xa2040;
// prettier-ignore
const NOTE_ON = [
    0xb2bd, 0xa2bd, 0xfe04, 0x8ba4, 0x82a9, 0x06a1, 0xff10, 0x02a2, 0x8aa9, 0x92c4, 0x9641, 0xdc08,
    0x92c4, 0x9642, 0xdc08, 0x92c4, 0x9643, 0xdc08, 0x92c4, 0x9644, 0x06a3, 0x8aa1, 0x7648, 0x8a24,
    0x8f00, 0xc080, 0x7649, 0xb905, 0x82a9, 0x06a1, 0xff10, 0x02a2, 0x8aa9, 0x92c4, 0x6104, 0x9241,
    0x6002, 0xa2d4, 0xdc08, 0x92c4, 0x6104, 0x9242, 0x6002, 0xa2d4, 0xdc08, 0x92c4, 0x6104, 0x9243,
    0x6002, 0xa2d4, 0xdc08, 0x92c4, 0x6104, 0x9244, 0x6002, 0xa2d4, 0xfe84, 0x82be, 0x8bbe, 0x0006,
];
const NOTE_OFF_ADDR = 0xa2080;
// prettier-ignore
const NOTE_OFF = [
    0xb2bd, 0xfe02, 0x2841, 0x0004, 0x06a2, 0xff10, 0x02a2, 0x8ba9, 0x92c1, 0x6035, 0x92c9, 0x5201,
    0x6131, 0x5202, 0x6130, 0xc4d1, 0x06a2, 0xff10, 0x02a2, 0x8aa9, 0xb603, 0x92c4, 0x6108, 0x06d4,
    0x03a6, 0xff56, 0x8f40, 0x9c40, 0x0fa5, 0x681e, 0xdc08, 0x000f, 0xfff6, 0x28c9, 0x0002, 0x8d00,
    0x0ef4, 0x06a3, 0x0392, 0x8f40, 0x1388, 0x07a5, 0x1ed1, 0xc4a9, 0x06a2, 0xff10, 0x02a2, 0x8aa9,
    0xb603, 0x92cc, 0x5201, 0x6004, 0x28cc, 0x0002, 0xc2d4, 0xdc08, 0x000f, 0xfff9, 0x6f04, 0x28c9,
    0x0001, 0xa2d1, 0xd908, 0x0b41, 0x60c8, 0xfe82, 0x8bbe, 0x0006,
];
const SHORT_OFFSET = 39; // MOVL XAR5,#short at NOTE_OFF_ADDR + 39
const CODE_END = NOTE_OFF_ADDR + NOTE_OFF.length;

/**
 * Describe the mixer gate fix in a firmware file. Recognises both this fix and the older one
 * (v1.x of this project, which changed the 125 ms hold itself).
 * @returns {{state: "unpatched"} | {state: "patched", ms: number} | {state: "unsupported"}}
 */
export function mixGateState(fw) {
    const hold = fw.read(MIXGATE_HOLD_SITE, 2);
    const onSite = fw.read(NOTE_ON_SITE, 2);
    const offSite = fw.read(NOTE_OFF_SITE, 3);
    if (equal(onSite, NOTE_ON_PATCHED) && equal(offSite, NOTE_OFF_PATCHED)) {
        const [hi, lo] = fw.read(NOTE_OFF_ADDR + SHORT_OFFSET, 2);
        return { state: "patched", ms: (((hi & 0x3f) << 16) | lo) / 1000 };
    }
    if (fw.version !== "1.3.0") return { state: "unsupported" };
    if (!equal(hold, MIXGATE_HOLD_ORIGINAL) && (hold[0] & 0xffc0) === 0x8f00) {
        return { state: "patched", ms: (((hold[0] & 0x3f) << 16) | hold[1]) / 1000 };
    }
    const free = fw.read(NOTE_ON_ADDR, CODE_END - NOTE_ON_ADDR);
    if (
        equal(hold, MIXGATE_HOLD_ORIGINAL) &&
        equal(onSite, NOTE_ON_ORIGINAL) &&
        equal(offSite, NOTE_OFF_ORIGINAL) &&
        free.every((w) => w === 0xffff)
    ) {
        return { state: "unpatched" };
    }
    return { state: "unsupported" };
}

/**
 * Shorten the paraphonic mixer gate hold for notes released while other keys are held, unless they
 * were pressed together with one of them. Chords keep Moog's 125 ms. Returns the short hold in us.
 */
export function patchMixGate(fw, ms) {
    if (mixGateState(fw).state !== "unpatched") {
        throw new FirmwareError("Only unpatched Matriarch firmware v1.3.0 can be patched.");
    }
    const us = Math.round(ms * 1000);
    if (!Number.isFinite(us) || us < 0 || us > 125000) {
        throw new FirmwareError(`Hold out of range: ${ms} ms (0 to 125).`);
    }
    const off = NOTE_OFF.slice();
    off.splice(SHORT_OFFSET, 2, 0x8f40 | (us >> 16), us & 0xffff); // MOVL XAR5,#us
    fw.write(NOTE_ON_ADDR, NOTE_ON);
    fw.write(NOTE_OFF_ADDR, off);
    fw.write(NOTE_ON_SITE, NOTE_ON_PATCHED);
    fw.write(NOTE_OFF_SITE, NOTE_OFF_PATCHED);
    return us;
}

// HOLD fix: see tools/patch_holdcc.py for the disassembly.
const HOLD_CALL_SITE = 0x8c5bd;
const HOLD_ORIGINAL_CALL = [0x7648, 0xc56b]; // LCR 0x0008c56b
const HOLD_PATCHED_CALL = [0x764a, 0x2000]; // LCR 0x000a2000
const HOLD_STUB_ADDR = 0xa2000;
const HOLD_STUB = [0x5300, 0x6109, 0x5200, 0x6107, 0x8f00, 0xe4ff, 0x1bc4, 0x0000, 0x56b0, 0x00a8, 0x0048, 0xc56b];
const PLAY_SITE = 0x893ac;
const PLAY_ORIGINAL_CALL = [0x7649, 0x0b88]; // LCR 0x00090b88
const PLAY_PATCHED_CALL = [0x764a, 0x2010]; // LCR 0x000a2010
const PLAY_WRAPPER_ADDR = 0xa2010;
// prettier-ignore
const PLAY_WRAPPER = [
    0xb2bd, 0xaabd, 0x8d40, 0xe4ff, 0x5ac1, 0x7649, 0x0b88, 0x92c1, 0x54a2, 0x6117, 0x8f01, 0x13b9,
    0x93c4, 0x6113, 0x8f00, 0xc8a4, 0x93c4, 0x610f, 0x5200, 0x6107, 0x8f01, 0x3443, 0x93c4, 0x6009,
    0x9b00, 0x6f02, 0x9b40, 0x9a40, 0x8f00, 0xcdc0, 0x7649, 0x7037, 0x86be, 0x8bbe, 0x0006,
];

/**
 * Describe the HOLD fix in a firmware file.
 * @returns {{state: "unpatched"} | {state: "patched"} | {state: "unsupported"}}
 */
export function holdState(fw) {
    const free = fw.read(HOLD_STUB_ADDR, PLAY_WRAPPER_ADDR + PLAY_WRAPPER.length - HOLD_STUB_ADDR);
    if (
        equal(fw.read(HOLD_CALL_SITE, 2), HOLD_ORIGINAL_CALL) &&
        equal(fw.read(PLAY_SITE, 2), PLAY_ORIGINAL_CALL) &&
        free.every((w) => w === 0xffff)
    ) {
        return { state: "unpatched" };
    }
    if (
        equal(fw.read(HOLD_CALL_SITE, 2), HOLD_PATCHED_CALL) &&
        equal(fw.read(PLAY_SITE, 2), PLAY_PATCHED_CALL) &&
        equal(fw.read(HOLD_STUB_ADDR, HOLD_STUB.length), HOLD_STUB) &&
        equal(fw.read(PLAY_WRAPPER_ADDR, PLAY_WRAPPER.length), PLAY_WRAPPER)
    ) {
        return { state: "patched" };
    }
    return { state: "unsupported" };
}

/** Make HOLD send sustain (CC 64) only while the Arp/Seq isn't running. */
export function patchHold(fw) {
    if (holdState(fw).state !== "unpatched") {
        throw new FirmwareError("Only unpatched Matriarch firmware v1.3.0 can be patched.");
    }
    fw.write(HOLD_STUB_ADDR, HOLD_STUB);
    fw.write(PLAY_WRAPPER_ADDR, PLAY_WRAPPER);
    fw.write(HOLD_CALL_SITE, HOLD_PATCHED_CALL);
    fw.write(PLAY_SITE, PLAY_PATCHED_CALL);
}

// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Benjamin Dehli
//
// The fixes the web patcher can apply. A port of tools/patch_mixgate.py and tools/patch_holdcc.py.

import { FirmwareError } from "./matriarch-syx.js";

/** SHA-256 of Moog's official Matriarch_Firmware_v1_3_0.syx, the only file the fixes are made for. */
export const OFFICIAL_V1_3_0_SHA256 = "2f414599472e928fccfba687b9fa4bb8639fdd8a9573ace1df408ed587ad6f67";

const MIXGATE_SITE = 0x8b991;
const MIXGATE_ORIGINAL = [0x8f01, 0xe848]; // MOVL XAR4,#125000

function movlXar4(value) {
    return [0x8f00 | (value >> 16), value & 0xffff];
}

/**
 * Describe what the patcher can do with a firmware file.
 * @returns {{state: "unpatched"} | {state: "patched", ms: number} | {state: "unsupported"}}
 */
export function mixGateState(fw) {
    const [a, b] = fw.read(MIXGATE_SITE, 2);
    if (a === MIXGATE_ORIGINAL[0] && b === MIXGATE_ORIGINAL[1]) return { state: "unpatched" };
    if ((a & 0xffc0) === 0x8f00 && fw.version === "1.3.0") {
        return { state: "patched", ms: (((a & 0x3f) << 16) | b) / 1000 };
    }
    return { state: "unsupported" };
}

/** Set the paraphonic mixer gate release delay. Returns the delay in microseconds. */
export function patchMixGate(fw, ms) {
    if (mixGateState(fw).state !== "unpatched") {
        throw new FirmwareError("Only unpatched Matriarch firmware v1.3.0 can be patched.");
    }
    const us = Math.round(ms * 1000);
    if (!Number.isFinite(us) || us < 0 || us >= 1 << 22) {
        throw new FirmwareError(`Delay out of range: ${ms} ms.`);
    }
    fw.write(MIXGATE_SITE, movlXar4(us));
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

const equal = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);

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

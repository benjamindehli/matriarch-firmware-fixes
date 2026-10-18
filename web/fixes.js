// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Benjamin Dehli
//
// The fixes the web patcher can apply. A port of tools/patch_mixgate.py.

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

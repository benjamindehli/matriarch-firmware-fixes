// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Benjamin Dehli
//
// Tests for the web patcher's JavaScript against Moog's official v1.3.0 firmware.
// Set MATRIARCH_FIRMWARE to the path of Matriarch_Firmware_v1_3_0.syx. The tests are skipped otherwise.
// Run: npm test

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { mixGateState, patchMixGate } from "../web/fixes.js";
import { Firmware, FirmwareError } from "../web/matriarch-syx.js";

const expected = JSON.parse(readFileSync(new URL("./expected.json", import.meta.url)));
const source = process.env.MATRIARCH_FIRMWARE;
const skip = source ? false : "set MATRIARCH_FIRMWARE to the official v1.3.0 .syx";
const sha256 = (data) => createHash("sha256").update(data).digest("hex");

test("source is the official v1.3.0", { skip }, () => {
    const original = readFileSync(source);
    assert.equal(sha256(original), expected.source.sha256);
    assert.equal(new Firmware(original).version, "1.3.0");
});

test("round trip is byte-identical", { skip }, () => {
    const original = readFileSync(source);
    const fw = new Firmware(original);
    fw.write(0x88000, fw.read(0x88000));
    assert.deepEqual(Buffer.from(fw.bytes()), original);
});

test("mixer gate patch matches the hardware-tested builds", { skip }, () => {
    for (const [ms, hash] of Object.entries(expected.mixgate)) {
        const fw = new Firmware(readFileSync(source));
        assert.deepEqual(mixGateState(fw), { state: "unpatched" });
        patchMixGate(fw, Number(ms));
        assert.equal(sha256(fw.bytes()), hash, `${ms} ms`);
        assert.deepEqual(mixGateState(new Firmware(fw.bytes())), {
            state: "patched",
            ms: Number(ms),
        });
    }
});

test("refuses to patch twice", { skip }, () => {
    const fw = new Firmware(readFileSync(source));
    patchMixGate(fw, 5);
    assert.throws(() => patchMixGate(fw, 50), FirmwareError);
});

test("rejects files that aren't Matriarch firmware", () => {
    assert.throws(() => new Firmware(new Uint8Array([1, 2, 3])), FirmwareError);
    assert.throws(() => new Firmware(Uint8Array.from([0xf0, 0x43, 0x10, 0, 0, 0, 0, 0xf7])), FirmwareError);
});

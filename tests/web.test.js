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

import { OFFICIAL_V1_3_0_SHA256, holdState, mixGateState, patchHold, patchMixGate } from "../web/fixes.js";
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

test("mixer gate patch matches the expected builds", { skip }, () => {
    for (const [ms, hash] of Object.entries(expected.mixgate)) {
        const fw = new Firmware(readFileSync(source));
        assert.deepEqual(mixGateState(fw), { state: "unpatched" });
        patchMixGate(fw, Number(ms));
        assert.equal(sha256(fw.bytes()), hash, `${ms} ms`);
        assert.deepEqual(mixGateState(new Firmware(fw.bytes())), {
            state: "patched",
            mode: "chord",
            ms: Number(ms),
        });
    }
});

test("simple mixer gate patch matches the v1.2.0 builds", { skip }, () => {
    for (const [ms, hash] of Object.entries(expected.mixgate_simple)) {
        const fw = new Firmware(readFileSync(source));
        patchMixGate(fw, Number(ms), { simple: true });
        assert.equal(sha256(fw.bytes()), hash, `${ms} ms`);
        assert.deepEqual(mixGateState(new Firmware(fw.bytes())), {
            state: "patched",
            mode: "simple",
            ms: Number(ms),
        });
    }
});

test("refuses to patch twice", { skip }, () => {
    const fw = new Firmware(readFileSync(source));
    patchMixGate(fw, 5);
    assert.throws(() => patchMixGate(fw, 50), FirmwareError);
    assert.throws(() => patchMixGate(fw, 50, { simple: true }), FirmwareError);
});

test("rejects files that aren't Matriarch firmware", () => {
    assert.throws(() => new Firmware(new Uint8Array([1, 2, 3])), FirmwareError);
    assert.throws(() => new Firmware(Uint8Array.from([0xf0, 0x43, 0x10, 0, 0, 0, 0, 0xf7])), FirmwareError);
});

test("web patcher knows the official v1.3.0 checksum", () => {
    assert.equal(OFFICIAL_V1_3_0_SHA256, expected.source.sha256);
});

test("files from v1.0.0 to v1.2.0 of this project count as simple mode", { skip }, () => {
    const fw = new Firmware(readFileSync(source));
    fw.write(0x8b991, [0x8f00, 0x1388]); // 125 ms hold changed to 5 ms
    assert.deepEqual(mixGateState(fw), { state: "patched", mode: "simple", ms: 5 });
    assert.throws(() => patchMixGate(fw, 5), FirmwareError);
});

test("HOLD patch matches the expected build", { skip }, () => {
    const fw = new Firmware(readFileSync(source));
    assert.deepEqual(holdState(fw), { state: "unpatched" });
    patchHold(fw);
    assert.equal(sha256(fw.bytes()), expected.hold);
    assert.deepEqual(holdState(new Firmware(fw.bytes())), { state: "patched" });
    assert.throws(() => patchHold(fw), FirmwareError);
});

test("fixes combine in any order", { skip }, () => {
    for (const [key, simple] of [
        ["mixgate_hold", false],
        ["mixgate_simple_hold", true],
    ]) {
        for (const [ms, hash] of Object.entries(expected[key])) {
            const first = new Firmware(readFileSync(source));
            patchMixGate(first, Number(ms), { simple });
            patchHold(first);
            const second = new Firmware(readFileSync(source));
            patchHold(second);
            patchMixGate(second, Number(ms), { simple });
            assert.equal(sha256(first.bytes()), hash, `${key} ${ms} ms`);
            assert.deepEqual(Buffer.from(first.bytes()), Buffer.from(second.bytes()));
        }
    }
});

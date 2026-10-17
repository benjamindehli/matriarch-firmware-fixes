# matriarch-firmware-fixes

Unofficial bug fixes for the Moog Matriarch firmware v1.3.0, the last release before the Matriarch was discontinued.

> **Unofficial. Use at your own risk.** This project isn't affiliated with or endorsed by Moog Music. Flashing modified firmware may void your warranty, and the authors take no responsibility for any damage. This repository contains no Moog firmware. You patch your own copy of Moog's official v1.3.0 file.

## Fixes

| Fix                          | Script                   | Status                              |
| ---------------------------- | ------------------------ | ----------------------------------- |
| Paraphonic Mixer Gate Length | `tools/patch_mixgate.py` | Tested on hardware (5 ms and 50 ms) |

### Paraphonic Mixer Gate Length

Moog's v1.3.0 known-issues list says: _"Paraphonic Mixer Gate Length - Mixer gate can stay high longer than keys are pressed."_

In 2- and 4-note paraphonic mode, releasing a key while another key is still held keeps that oscillator sounding for another **125 ms**. Staccato notes over a held note, or fast playing where keys overlap, smear together (see the Moog forum thread "Matriarch - staccato playing in paraphonic modes"). The patch shortens the hold:

- `--ms 5`: released notes stop almost immediately (recommended)
- `--ms 50`: the v1.1.0 behaviour

When the _last_ key is released, the VCA envelope's release shapes the tail exactly as before.

## How to patch and flash

You need Python 3 and Moog's official **v1.3.0** firmware (`Matriarch_Firmware_v1_3_0.syx`), which comes with the Moog Firmware Updater or Moog's v1.3.0 download.

1. Create the patched file:
   ```sh
   python3 tools/patch_mixgate.py Matriarch_Firmware_v1_3_0.syx Matriarch_Firmware_v1_3_0_mixgate5ms.syx --ms 5
   ```
   The script refuses to patch anything that isn't v1.3.0.
2. Flash it with a SysEx tool (SysEx Librarian on macOS, Bome SendSX on Windows), following Moog's normal procedure:
   1. Send `Matriarch_FIRMWARE_INVALIDATE.syx`.
   2. Re-select the Matriarch as the MIDI output (it reboots).
   3. Send `Matriarch_FIRMWARE_ERASE.syx`.
   4. Send the patched file.
3. To go back to stock, repeat step 2 with Moog's original `Matriarch_Firmware_v1_3_0.syx`.

Use a direct USB cable (no hub) and don't touch the synth during the transfer. If a transfer fails, power-cycle, reconnect, and start again from INVALIDATE. The updates never touch the bootloader.

## How the fix works

Note-off (`0x88de4`) doesn't close a released voice's mixer gate immediately when other keys are held. It marks the voice as release-pending with a timestamp, and the main loop (`0x8a56b`, at `0x8a81d`) closes the gate once `now - timestamp > engine.mixGateDelay`. The engine init (`0x8b3f0`) sets that delay:

```
0008b98f  8d00 0ef4   MOVL XAR0,#0xef4
0008b991  8f01 e848   MOVL XAR4,#0x1e848      ; 125000 us   <- the patch rewrites this immediate
0008b994  a893        MOVL *+XAR3[AR0],XAR4   ; engine(0x10640).mixGateDelay
```

Only the release loop reads the field, and the setter at `0x88efc` is never called. The patch changes two 16-bit words. All other bytes of the `.syx` stay identical to Moog's, and the affected record's checksum is recomputed.

History, from comparing v1.1.0, v1.2.3 and v1.3.0:

| Version | Mixer gate hold after key-up                       | Multi Trig envelope retrigger window |
| ------- | -------------------------------------------------- | ------------------------------------ |
| v1.1.0  | 50 ms (`deadline = ts + 0xC350` at `0x8a6e3`)      | 2 ms                                 |
| v1.2.3  | 125 ms (moved to `engine+0xEF4`, set at `0x8b901`) | 4 ms                                 |
| v1.3.0  | 125 ms                                             | 5 ms                                 |

The 125 ms change isn't in any release notes. Moog support has said the hold is intentional, "to avoid completely missing quickly played notes". The Multi Trig retrigger window (the stuck-envelope fixes in v1.2.x) is separate code with its own constant and isn't affected by this patch.

## Firmware format and hardware notes

- The firmware is a single SysEx message `F0 04 17 ... F7`. Each 16-bit word is packed into 3 bytes (`0x40|b15..12`, `b11..6`, `b5..0`).
- Data records are `0013 0088 0080 0000 addrLo addrHi cksum <128 words> 0000`, where cksum is the 16-bit sum of the other words. The header record (`0012 ...`) holds the version and its own checksum at word 14. There's no whole-image CRC.
- The CPU is a TI TMS320F2837x (C28x + FPU), which is word-addressed. The application lives at `0x88000` to `0xBFFFF`, and the bootloader sits below it and isn't part of updates.
- Global settings sit at `0xC899 + n` for SysEx global parameter `n` (v1.3.0). For example, paraphony mode is at `0xC8D0`.
- Front-panel LEDs and other digital outputs go through a shift-register shadow at `0x1374A`, flushed over SPI.

## Tools

| File                     | Purpose                                                                           |
| ------------------------ | --------------------------------------------------------------------------------- |
| `tools/matriarch_syx.py` | Parses `.syx` files, verifies checksums and patches words in place                |
| `tools/patch_mixgate.py` | The mixer gate fix                                                                |
| `tools/syx2bin.py`       | Extracts a flat image to load at word address `0x88000`                           |
| `tools/periph_map.py`    | Shows which functions touch which peripherals (from `refs.tsv`)                   |
| `tools/ghidra_scripts/`  | `ExportDecomp.java` (decompiled C + references) and `DumpListing.java` (listings) |
| `tools/listing.sh`       | Dumps a listing from a local Ghidra project in `work/ghidra`                      |

The analysis setup is Ghidra 12.1.2 with the [ghidra-tms320c28x](https://github.com/outlandnish/ghidra-tms320c28x) processor module. Import the image from `syx2bin.py` as raw binary with language `TMS320C28x:LE:32:default` and base address `0x88000`, then run the module's `SetupF28377D.java CPU1` and `SeedFunctions.java` before auto-analysis.

## Development

Python code is linted and formatted with [Ruff](https://docs.astral.sh/ruff/) (config in `pyproject.toml`). Markdown and JSON are formatted with [Prettier](https://prettier.io/) (config in `.prettierrc.json`). Editors that support [EditorConfig](https://editorconfig.org/) pick up the basic settings for all files from `.editorconfig`.

```sh
pip install ruff
ruff check .          # lint
ruff format .         # format Python

npm install
npm run format        # format Markdown and JSON
```

## License

Copyright (C) 2026 Benjamin Dehli

The tools and documentation in this repository are free software, licensed under the [GNU General Public License v3.0 or later](LICENSE). Moog Music's firmware isn't included and isn't covered by this license.

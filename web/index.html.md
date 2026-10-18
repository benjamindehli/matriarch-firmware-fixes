Page: Matriarch Firmware Patcher: fix paraphonic staccato on the Moog Matriarch
URL: https://benjamindehli.github.io/matriarch-firmware-fixes/
Last changed: 2026-10-18

# Matriarch Firmware Patcher

Apply unofficial bug fixes to your own copy of the Moog Matriarch firmware v1.3.0. The first fix makes released notes stop when you let go in paraphonic mode, so staccato playing works again. Everything happens in your browser. Your file is never uploaded.

- [Source on GitHub](https://github.com/benjamindehli/matriarch-firmware-fixes)
- [Star the repo](https://github.com/login?return_to=%2Fbenjamindehli%2Fmatriarch-firmware-fixes)
- [Follow @benjamindehli](https://github.com/login?return_to=%2Fbenjamindehli)

**Unofficial. Use at your own risk.** This project isn't affiliated with or endorsed by Moog Music. You can always go back by flashing Moog's original firmware.

## Using the patcher

The patcher itself is interactive and needs a browser with JavaScript: https://benjamindehli.github.io/matriarch-firmware-fixes/

1. Choose Moog's firmware file, `Matriarch_Firmware_v1_3_0.syx`, from Moog's v1.3.0 download or the Moog Firmware Updater. The page checks that it's Matriarch firmware v1.3.0 and compares it with the SHA-256 of Moog's official file.
2. Choose the paraphonic mixer gate length: 5 ms (recommended), 50 ms (the same behaviour as firmware v1.1.0), or a whole number from 0 to 125.
3. Download the patched file and flash it with a SysEx tool (SysEx Librarian on macOS, Bome SendSX on Windows) using Moog's normal procedure:
   1. Send `Matriarch_FIRMWARE_INVALIDATE.syx`.
   2. Re-select the Matriarch as the MIDI output (it reboots).
   3. Send `Matriarch_FIRMWARE_ERASE.syx`.
   4. Send the patched file.

Use a direct USB cable and don't touch the synth during the transfer. To go back to stock, repeat the steps with Moog's original file.

## What it fixes

### Paraphonic Mixer Gate Length

Each of the Matriarch's four oscillators has a gate in front of the mixer that opens when a key assigns a note to it. In 2- and 4-note paraphonic mode, firmware v1.3.0 doesn't close that gate when you release a key while other keys are still held. It waits another 125 ms first. Staccato notes over a held note, and fast passages where the next key goes down before the last one comes up, smear together.

Moog lists this as a known issue in the v1.3.0 release notes: _"Paraphonic Mixer Gate Length - Mixer gate can stay high longer than keys are pressed."_ The hold was added on purpose, to avoid completely missing quickly played notes, and it has grown since firmware v1.1.0:

| Firmware        | Hold after key-up             |
| --------------- | ----------------------------- |
| v1.1.0          | 50 ms                         |
| v1.2.3          | 125 ms                        |
| v1.3.0          | 125 ms                        |
| v1.3.0, patched | 5 ms, 50 ms or your own value |

The patch changes the one value that sets the hold. When you release the last key, the VCA envelope's release shapes the tail exactly as before, and Multi Trig and its envelope retrigger timing are untouched. The [technical details](https://github.com/benjamindehli/matriarch-firmware-fixes#how-the-fix-works) are in the repository.

### Other known issues in v1.3.0

These are on Moog's list but not fixed here yet:

- Send Program Change seems to have no effect.
- The arpeggiator sends Sustain CC while Hold is active.
- After Load Default Settings, global mode acts as if A#3 is held down until a power cycle.
- Sequence Random Repeat and Sequence Keyed Restart seem to have no effect.
- Keyed Timing Reset doesn't work while Hold is active.
- Delay Sync CV Bend can be stepped when it should be smooth.

If one of these affects you, say so in the [issue tracker](https://github.com/benjamindehli/matriarch-firmware-fixes/issues).

## Questions

### Why can't I play staccato in paraphonic mode on the Moog Matriarch?

In firmware v1.2.3 and v1.3.0, when you release a key in 2- or 4-note paraphonic mode while other keys are still held, the Matriarch keeps that oscillator's mixer gate open for another 125 ms. Short notes and fast overlapping notes smear together. Moog lists it as the known issue "Paraphonic Mixer Gate Length" in the v1.3.0 release notes. This patcher shortens the hold to 5 ms or any value you choose.

### Is my firmware file uploaded anywhere?

No. The patcher runs entirely in your browser. The page loads no external scripts, fonts or trackers, and the file never leaves your computer.

### Why isn't the patched firmware available as a download?

The patched file is still Moog's firmware with a small change, and Moog owns the copyright. Distributing it would mean distributing Moog's firmware. The patcher lets you change your own copy instead.

### Where do I get the Matriarch firmware v1.3.0 file?

From Moog's v1.3.0 firmware download, or through the Moog Firmware Updater. The file you need is `Matriarch_Firmware_v1_3_0.syx`.

### Is it safe to flash patched firmware on the Matriarch?

The patch changes one number in one instruction and leaves the rest of the firmware byte-identical to Moog's file. The update never touches the bootloader, and both the 5 ms and 50 ms builds have been flashed and tested on a Matriarch. It's still unofficial, so you use it at your own risk.

### How do I go back to Moog's original firmware?

Flash Moog's original `Matriarch_Firmware_v1_3_0.syx` with the same procedure: send INVALIDATE, re-select the MIDI port, send ERASE, then send the original file.

### Which delay should I choose?

5 ms makes released notes stop almost immediately, which suits staccato playing. 50 ms is how firmware v1.1.0 behaved, before the hold was raised to 125 ms. Moog's reason for the hold was to avoid completely missing quickly played notes, so if very short taps feel too quiet, try a value in between.

### Does the patch affect Multi Trig or the stuck-envelope fixes?

No. The envelope retrigger timing that fixed stuck envelopes in Multi Trig mode is separate code with its own value, and the patch doesn't change it.

---

By Benjamin Dehli for [Dehli Musikk](https://www.dehlimusikk.no/). Free software under the [GNU General Public License v3.0 or later](https://github.com/benjamindehli/matriarch-firmware-fixes/blob/main/LICENSE). Moog and Matriarch are trademarks of Moog Music Inc. This project isn't affiliated with Moog Music.

Page: Matriarch Firmware Patcher: fix paraphonic staccato on the Moog Matriarch
URL: https://benjamindehli.github.io/matriarch-firmware-fixes/
Last changed: 2026-10-31

# Matriarch Firmware Patcher

Apply unofficial bug fixes to your own copy of the Moog Matriarch firmware v1.3.0: released notes stop when you let go in paraphonic mode, and HOLD no longer sends sustain to connected gear while an arpeggio is latched. Everything happens in your browser. Your file is never uploaded.

- [Source on GitHub](https://github.com/benjamindehli/matriarch-firmware-fixes)
- [Star the repo](https://github.com/login?return_to=%2Fbenjamindehli%2Fmatriarch-firmware-fixes)
- [Follow @benjamindehli](https://github.com/login?return_to=%2Fbenjamindehli)

**Unofficial. Use at your own risk.** This project isn't affiliated with or endorsed by Moog Music. You can always go back by flashing Moog's original firmware.

## Using the patcher

The patcher itself is interactive and needs a browser with JavaScript: https://benjamindehli.github.io/matriarch-firmware-fixes/

1. Choose Moog's firmware file, `Matriarch_Firmware_v1_3_0.syx`, from Moog's v1.3.0 download or the Moog Firmware Updater. The page checks that it's Matriarch firmware v1.3.0 and compares it with the SHA-256 of Moog's official file.
2. Choose the fixes. Both are selected by default, and you can apply either one on its own:
   - Fix the paraphonic mixer gate length: 5 ms (recommended), 50 ms (the same behaviour as firmware v1.1.0), or a whole number from 0 to 125. Keys you press together still ring out together when you lift them.
   - Fix HOLD sending sustain while the Arp/Seq is playing: with the fix, HOLD sends sustain (MIDI CC 64) only while the Arp/Seq is stopped.
3. Download the patched file and flash it with a SysEx tool (SysEx Librarian on macOS, Bome SendSX on Windows) using Moog's normal procedure:
   1. Send `Matriarch_FIRMWARE_INVALIDATE.syx`.
   2. Re-select the Matriarch as the MIDI output (it reboots).
   3. Send `Matriarch_FIRMWARE_ERASE.syx`.
   4. Send the patched file.

Use a direct USB cable and don't touch the synth during the transfer. To go back to stock, repeat the steps with Moog's original file.

## What it fixes

### Paraphonic Mixer Gate Length

Each of the Matriarch's four oscillators has a gate in front of the mixer that opens when a key assigns a note to it. In 2- and 4-note paraphonic mode, firmware v1.3.0 doesn't close that gate when you release a key while other keys are still held. It waits another 125 ms first. Staccato notes over a held note, and fast passages where the next key goes down before the last one comes up, smear together.

[![Waveforms in Logic Pro: the same MIDI part recorded with the original 125 ms hold, 50 ms and 5 ms. With 125 ms each short note keeps sounding well after it ends, with 5 ms it stops right at the end of the note.](https://benjamindehli.github.io/matriarch-firmware-fixes/audio-test-1200.webp)](https://benjamindehli.github.io/matriarch-firmware-fixes/audio-test.webp)

_The same MIDI part recorded on a Matriarch with the original firmware (125 ms), then with each patch (50 ms and 5 ms): a held note with short notes on top. The highlighted note ends at the same point in all three. With 125 ms it keeps sounding well past the end, with 50 ms the tail is shorter, and with 5 ms it stops where the note ends._

Moog lists this as a known issue in the v1.3.0 release notes: _"Paraphonic Mixer Gate Length - Mixer gate can stay high longer than keys are pressed."_ The hold was added on purpose, to avoid completely missing quickly played notes, and it has grown since firmware v1.1.0:

| Firmware                      | Hold after key-up                                    |
| ----------------------------- | ---------------------------------------------------- |
| v1.1.0                        | 50 ms                                                |
| v1.2.3                        | 125 ms                                               |
| v1.3.0                        | 125 ms                                               |
| v1.3.0, patched (chord-aware) | 5 ms, 50 ms or your own value, and 125 ms for chords |
| v1.3.0, patched (simple)      | 5 ms, 50 ms or your own value, chords included       |

The hold also decides whether keys were lifted together: when you lift a chord, its notes ring out with the release only if each key comes up within the hold time of the previous one. So the patch keeps Moog's 125 ms for a note you pressed together with a key that's still held, and uses the short hold only for the others, such as staccato notes over a held chord or the notes of a fast run. When every key of a chord is up but other keys are still held, such as a staccato chord over a held bass note, the whole chord stops after the short hold.

If you prefer one fixed cut-off, the patcher's simple mode gives every released note the short hold, chords included, as versions 1.0.0 to 1.2.0 of this patcher did. With a short hold and a long release, a lifted chord then keeps only its last note or two.

Lifted chords ring out exactly as with Moog's firmware. When you release the last key, the VCA envelope's release shapes the tail as before, and Multi Trig and its envelope retrigger timing are untouched. The [technical details](https://github.com/benjamindehli/matriarch-firmware-fixes#how-the-fixes-work) are in the repository.

### HOLD sends sustain while the Arp/Seq is playing

Since the v1.2 updates, the HOLD button does two jobs. While the Arp/Seq is running it latches the pattern, and while the Arp/Seq is stopped it works as a sustain pedal and sends MIDI CC 64 to connected gear. Firmware v1.3.0 sends the sustain in both cases, so latching an arpeggio also makes connected synths sustain every note. Moog lists this as a known issue: _"ARP sends Sustain CC while Hold is active - HOLD should send sustain CC when Arp/Seq is inactive."_

With the fix, connected gear sustains exactly when HOLD is on and the Arp/Seq isn't running:

| You do this                        | v1.3.0 sends                      | Patched sends                                 |
| ---------------------------------- | --------------------------------- | --------------------------------------------- |
| HOLD on, Arp/Seq stopped           | Sustain on                        | Sustain on                                    |
| HOLD on while the Arp/Seq plays    | Sustain on                        | Nothing, and the pattern latches as before    |
| Start the Arp/Seq while HOLD is on | Nothing, so notes keep sustaining | Sustain off, unless the sustain pedal is down |
| Stop the Arp/Seq while HOLD is on  | Nothing                           | Sustain on                                    |
| HOLD off                           | Sustain off                       | Sustain off                                   |

The Matriarch's own sound, the sustain pedal and incoming MIDI sustain work exactly as before. The fix has been tested on a Matriarch driving a Yamaha DX7 over MIDI. Without the patch, there's a workaround: after latching with HOLD, press and release the sustain pedal. That sends sustain off to connected gear while the pattern stays latched.

### Other known issues in v1.3.0

These are on Moog's list but not fixed here yet:

- Send Program Change seems to have no effect.
- After Load Default Settings, global mode acts as if A#3 is held down until a power cycle.
- Sequence Random Repeat and Sequence Keyed Restart seem to have no effect.
- Keyed Timing Reset doesn't work while Hold is active.
- Delay Sync CV Bend can be stepped when it should be smooth.

If one of these affects you, say so in the [issue tracker](https://github.com/benjamindehli/matriarch-firmware-fixes/issues).

## Questions

### Why can't I play staccato in paraphonic mode on the Moog Matriarch?

In firmware v1.2.3 and v1.3.0, when you release a key in 2- or 4-note paraphonic mode while other keys are still held, the Matriarch keeps that oscillator's mixer gate open for another 125 ms. Short notes and fast overlapping notes smear together. Moog lists it as the known issue "Paraphonic Mixer Gate Length" in the v1.3.0 release notes. This patcher shortens the hold to 5 ms or any value you choose, while chords you lift keep ringing out with the release.

### Why do my other synths sustain when I latch the arpeggiator with HOLD?

Since the v1.2 updates, the HOLD button also works as a sustain pedal when the Arp/Seq isn't running, and sends MIDI CC 64 to connected gear. Firmware v1.3.0 sends it even while the Arp/Seq is running, so latching an arpeggio also sustains notes on connected synths. Moog lists it as a known issue. The HOLD fix sends sustain only while the Arp/Seq is stopped. Without the patch, pressing and releasing a sustain pedal after engaging HOLD clears the sustain on connected gear.

### Is my firmware file uploaded anywhere?

No. The patcher runs entirely in your browser. The page loads no external scripts, fonts or trackers, and the file never leaves your computer.

### Why isn't the patched firmware available as a download?

The patched file is still Moog's firmware with a small change, and Moog owns the copyright. Distributing it would mean distributing Moog's firmware. The patcher lets you change your own copy instead.

### Where do I get the Matriarch firmware v1.3.0 file?

From Moog's v1.3.0 firmware download, or through the Moog Firmware Updater. The file you need is `Matriarch_Firmware_v1_3_0.syx`.

### Is it safe to flash patched firmware on the Matriarch?

Both fixes add a few instructions in unused flash. The rest of the firmware stays byte-identical to Moog's file, and the Matriarch computes its own firmware checksum after an update. The update never touches the bootloader, and every release is flashed and tested on a Matriarch before it's published. It's still unofficial, so you use it at your own risk.

### How do I go back to Moog's original firmware?

Flash Moog's original `Matriarch_Firmware_v1_3_0.syx` with the same procedure: send INVALIDATE, re-select the MIDI port, send ERASE, then send the original file.

### Which delay should I choose?

5 ms is recommended. Released notes stop almost immediately, which suits staccato playing, and in the chord-aware mode chords you lift still ring out with the release, because notes you press together keep Moog's 125 ms. 50 ms gives a softer cut-off. In the simple mode it's how firmware v1.1.0 behaved.

### Should I choose chord-aware or simple?

Chord-aware is recommended. Staccato notes and fast runs stop after the delay, while chords you lift still ring out with the release. Choose simple if you'd rather have the same cut-off for every note, for example if you mostly play with a short release. With simple and a long release, a lifted chord keeps only its last note or two with 5 ms, while 50 ms lets most lifted chords ring out.

### Does the patch affect Multi Trig or the stuck-envelope fixes?

No. The envelope retrigger timing that fixed stuck envelopes in Multi Trig mode is separate code with its own value, and the patch doesn't change it.

---

By Benjamin Dehli for [Dehli Musikk](https://www.dehlimusikk.no/). Free software under the [GNU General Public License v3.0 or later](https://github.com/benjamindehli/matriarch-firmware-fixes/blob/main/LICENSE). Moog and Matriarch are trademarks of Moog Music Inc. This project isn't affiliated with Moog Music.

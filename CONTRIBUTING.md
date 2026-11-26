# Contributing

The most valuable thing you can send is **a profile for a box nobody here owns.**

## Sending a profile

1. Run the read-only probe and diagnosis. They never modify your device.

   ```bash
   python3 tools/box.py --probe
   python3 tools/diag.py
   ```

2. Check what landed in `profiles/<brand>-<model>/`. Only these files are meant
   to be committed:

   | File | What it holds |
   |---|---|
   | `probe.json` | brand, model, SoC, Android version, build, RAM, storage |
   | `packages.txt` | installed packages and their enabled/disabled state |
   | `settings.json` | the settings keys this toolkit may change |
   | `diag.md` | the rendered diagnosis |
   | `mesures.md` | before/after numbers, if you have them |

   Everything under `profiles/<brand>-<model>/raw/` is gitignored on purpose.
   It contains your IP, your Wi-Fi name, your serial number, your MAC address
   and the names of the phones you have paired. **Do not commit it, and do not
   paste it into an issue.**

3. Read the committed files before you open the PR. If you find an IP, an SSID,
   a serial, an Android ID or a MAC address, that is a bug in the anonymiser —
   please report it rather than hand-editing it away.

## Adding packages to the classification

`references/classify.md` is the heart of this project. A package moves into
**SAFE** only with a reason and a device it was verified on. "It looked
useless" is not a reason.

A package moves into **NEVER** on the strength of a single report. Breaking
someone's box costs far more than keeping a useless package enabled.

## Recovery pages

`recovery/<brand>-<model>.md` is written **after** a probe has identified the
SoC, never from a datasheet. An EDL procedure written for the wrong SoC family
is worse than no page at all, because it reads as authoritative.

## Rules

- Disable only. No `pm uninstall`, no root, no flashing, no firmware or loader
  redistributed in this repo.
- English is canonical. If you change `PROMPT.md` or `README.md`, update
  `PROMPT.fr.md` or `README.fr.md` in the same PR.
- Say what you actually tested. This repo would rather cover three boxes
  honestly than claim five hundred.

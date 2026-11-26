# Fixtures

No box in this project is sacrificial, so the classification is developed and
tested **against recorded output, not against hardware.**

A fixture is the raw output of one command on one real device:

```
tests/fixtures/<brand>-<model>/getprop.txt
tests/fixtures/<brand>-<model>/packages.txt
tests/fixtures/<brand>-<model>/dumpsys-accessibility.txt
```

`tools/profile.py` captures exactly these into `profiles/<slug>/raw/` on the
first read-only pass. Moving them here means **anonymising them first**: the raw
dumps contain IP addresses, Wi-Fi names, serial numbers, MAC addresses, paired
phone names and often location. `tools/box.py:redact()` catches the obvious
shapes; read the file yourself before committing it.

## Status

There are no fixtures here yet: no box has been probed. Fixture-based tests
are deferred until there is hardware to capture from.

Three of the five tests below already run, against a live Android rather than
a recording — see `tests/emu/`. That rig is not a substitute for fixtures: it
has no vendor packages and no mirroring stack, so it cannot test the
classification rules that matter most on a real box.

The first tests to write, the ones that cost the most if wrong:

1. A Linux dongle is detected and refused, not probed into a traceback.
   *Needs a fixture — the rig always answers ADB.*
2. A missing diagnostic source drops its line instead of raising.
   **Covered by `tests/emu/cycle.sh`:** pstore and thermal are absent there.
3. A NEVER package is refused, and no flag makes it through.
   **Covered by `tests/emu/cycle.sh`.**
4. An unknown package classifies as RISKY, never SAFE.
   **Covered by `tests/emu/cycle.sh`:** 175 of 239 emulator packages land
   RISKY, every one of them unknown to the SAFE list.
5. A journal written before a mid-batch reboot still restores afterwards.
   *Needs a fixture or a rig step that reboots mid-batch — neither exists.*

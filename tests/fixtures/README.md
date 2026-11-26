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

Tests are deferred until there is hardware to capture from. There is no test
code here yet, and pretending otherwise would be exactly the dishonesty this
repo exists to avoid.

When hardware arrives, the first tests to write are the ones that cost the most
if wrong:

1. A Linux dongle is detected and refused, not probed into a traceback.
2. A missing diagnostic source drops its line instead of raising.
3. A NEVER package is refused, and no flag makes it through.
4. An unknown package classifies as RISKY, never SAFE.
5. A journal written before a mid-batch reboot still restores afterwards.

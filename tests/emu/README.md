# The emulator rig

A throwaway Android in a VM, so the dangerous half of this toolkit can be run
before it is ever pointed at hardware.

The Android emulator is QEMU on the host hypervisor. It gives a real Android
with a real `adbd`, a real `pm`, a real `settings`, real `dumpsys` — and a
snapshot button. That last part is what matters here: **the rig is the
sacrificial device the real box is not.**

It is not a CarPlay AI Box, and nothing here should be read as if it were.

## What it does and does not prove

**Proved on the rig.** `probe`, `diag`, `profile`, `classify`,
`pm disable-user`, the journal, the restore, the drift check, the NEVER
refusal, and — the one that matters — that the survival check reports FAILED
and exits non-zero when the bound accessibility service disappears. All of
that over the `adb` binary, which `Box` prefers whenever it is installed.

**Not proved: the raw TCP client's data path.** `tools/box.py` carries a
hand-rolled ADB wire protocol for machines with no `adb` installed. This
image sets `ro.adb.secure=1`, and the stdlib has no RSA, so the client gets
as far as AUTH and stops. What the rig proves is that it stops *cleanly* —
one sentence telling you to install platform-tools, not a traceback. Its
CNXN/OPEN/WRTE path has never executed against anything. Treat the `adb`
binary as required, not preferred.

**Only provable on the rig.** Running a whole destructive cycle and reverting
it in ten seconds. Disabling packages the real box must never be asked to
disable, to see what actually happens.

**Not provable here, at all.** Whether CarPlay still connects. Whether a tap
reaches the car's screen. Anything about the vendor mirroring stack, which no
emulator image contains. Anything electrical. The rig's `ro.*` properties,
thermal zones, pstore and power_supply are the emulator's, not a box's.

A green cycle here does not license a batch on the real box. It licenses the
*code* that would run the batch.

## Use

```bash
tests/emu/create.sh      # writes the AVD (no JDK needed, no avdmanager)
tests/emu/start.sh       # headless boot, waits for sys.boot_completed
tests/emu/cycle.sh       # the full destructive cycle, snapshot-protected
tests/emu/stop.sh
```

`tests/emu/snapshot.sh save|load|list <name>` is the undo button. Take one
before anything interesting.

Requires the `emulator` binary and an arm64 system image. Override with
`AVD_NAME`, `EMU_PORT`, `SYSTEM_IMAGE`, `API_TARGET` if yours differ.

## Measured on this rig

Image: `system-images/android-35/google_apis_playstore/arm64-v8a`, Android 15
(SDK 35), `ro.build.type=user`, arm64, on macOS 26 / Apple silicon.

- **`emulator -prop` does not take.** Neither `ro.*` nor `persist.*` survived
  to `getprop`; `setprop` from the shell is refused by SELinux on a user
  build. **Boot reasons cannot be simulated here.** `diag.py`'s power-loss
  detection is therefore untestable on the rig, and stays untested until a
  real box produces one.
- **`adb root` is refused** on a `google_apis_playstore` image, so dropbox,
  pstore and thermal readings cannot be seeded. `diag.py` correctly reports
  those sources as unavailable rather than failing.
- **The APEX packages are spelled `com.google.android.*` on a GMS build**, not
  `com.android.*`. Both spellings are now in the NEVER list; see
  `references/classify.md`.
- **The documented APEX bootloop did not reproduce here.** All four were
  accepted by `pm disable-user --user 0`, the device rebooted normally in
  ~20 s with Wi-Fi and ADB intact, and Android had silently re-enabled all
  four by the time it came back. That is one image on one Android version and
  it says nothing about an Android 13 vendor firmware, which is where the
  reports come from. They stay NEVER: being wrong costs the device.
- **An accessibility component that does not resolve is pruned.**
  `settings put secure enabled_accessibility_services <pkg>/<nonexistent>`
  reports success and leaves the value `null`. Any test of the touch guard
  must bind a service that actually exists, which is what `cycle.sh` does.

## Bugs this rig found

Each of these passed every check that existed before the rig did.

1. `usb_adb_available()` answered yes if *any* USB device was attached — a
   phone plugged into the same laptop made the tool promise a cable to the
   box. It now matches `ro.serialno`.
2. `resolve_host()` turned an ADB serial into `<serial>:5555` and could not
   reach a device over USB at all — the connection path the design calls
   path 1.
3. `apply.py check` compared the device against a probe taken a second
   earlier, so the accessibility leg could not fail. The touchscreen could
   disappear and the check printed `n/a` and exited 0. It now reads the
   baseline from `profiles/<slug>/probe.json` and refuses to answer without
   one.
4. An unknown SDK (no probe) downgraded APEX packages from NEVER to RISKY —
   turning the worst outcome in this repo into a question a user can answer
   yes to. Unknown is now treated as 13+.

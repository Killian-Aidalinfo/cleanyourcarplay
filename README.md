# cleanyourcarplay

**Find out why your Android CarPlay box crashes, then strip it down to the one
job you actually use it for.**

These boxes — Carlinkit TBox/Ultra, Ottocast and the many clones — are full
Android devices sold to do one thing: put wireless CarPlay on a car that only
has the wired kind. Most people never open an app on them. Yet they ship with a
Play Store, a browser, media players, a vendor app store and a pile of
telemetry, all competing for 2 GB of RAM behind your navigation.

This toolkit does two things, in this order:

1. **Diagnosis.** It reads why your box last rebooted, what crashed, how hot it
   got and what its power rail looked like. This comes first because a large
   share of these reboots are **electrical** — car USB ports and cigarette-lighter
   adapters often deliver under 1 A, and the voltage collapses when you crank the
   engine. No amount of debloating fixes that, and you deserve to know before you
   start.
2. **Cleanup.** It disables everything that is not needed to boot, bring up
   Wi-Fi and Bluetooth, pair your phone and run the mirroring stack. Nothing is
   uninstalled. Everything is reversible.

Everything runs over ADB from your computer. No root. No flashing. Nothing
written to `/system`.

## Status — read this first

**This toolkit has not yet been run on a real device.** Hardware is expected
2026-11-27. Package names, property names and system paths in this repo come
from documented reports on comparable devices, not from a box this project has
touched. The `profiles/` directory is empty for exactly that reason, and it will
only ever list boxes that were genuinely tested.

Most repos in this space claim broad support on the strength of one device. This
one will tell you precisely what it has seen.

It *has* been run end to end against a real Android — a throwaway emulator in
a VM, see `tests/emu/`. That proves the code works against a live `adbd`, `pm`
and `settings`, and it found five bugs that no amount of reading would have.
It proves nothing about a CarPlay box: an emulator has no mirroring stack, no
vendor firmware and no car.

## How you use it

You do not read this README to use the toolkit, and you do not type its
commands. You paste one URL into Claude Code and answer a few questions:

```
https://raw.githubusercontent.com/Killian-Aidalinfo/cleanyourcarplay/main/PROMPT.md
```

The agent connects to your box, runs the read-only diagnosis, tells you what it
found, asks you four questions, and does the rest. Every step it takes is
recorded so one command puts it all back.

Expect to be asked: do you use **Android Auto** as well as CarPlay, do calls and
audio go through the box or through the car's own Bluetooth, do you want to keep
firmware updates, and do you want to keep the voice assistant.

## What this is not

- **Not a launcher.** You never look at this device's Android UI, so no effort
  goes into making it pretty. If you want a launcher for an AI Box you actually
  use as an Android box, look at
  [Mini-Car-Launcher](https://github.com/jamal2362/Mini-Car-Launcher).
- **Not for Linux CarPlay dongles.** The small adapters — Carlinkit 3.0/4.0,
  CPC200-CCPA, Ottocast U2-X — run embedded Linux. They have no ADB, no packages
  and nothing to disable. This toolkit **detects them and stops**, and points you
  at [catplay](https://github.com/catplay-labs/catplay) instead.
- **Not a rooting or flashing kit.** No firmware, no loaders, no bootloader
  work, and no image is ever written by anything in this repo.
- **Not CarPlay protocol reverse engineering.** See
  [ludwig-v/wireless-carplay-dongle-reverse-engineering](https://github.com/ludwig-v/wireless-carplay-dongle-reverse-engineering).

## The risk, stated plainly

A TV you break is a TV you fix from its own settings menu with its own remote.
**This box has neither.** It has no screen of its own — it displays inside your
car's CarPlay window — no remote, and no reachable settings menu. Your only way
back is ADB over the network.

That means two specific mistakes are much worse here than they sound:

- **Disabling the mirroring stack.** On at least one documented device, the
  package holding the accessibility service that injects your finger taps into
  CarPlay is `com.carsyso.main`. Disable it and the box boots perfectly, the
  picture appears, and the screen stops responding to your finger. Nothing
  "crashes". You simply cannot do anything any more.
- **Disabling APEX packages on Android 13+.** `com.android.adservices.api`,
  `com.android.sdksandbox`, `com.android.federatedcompute.services` and
  `com.android.ondevicepersonalization.services` give you a boot loop, a
  blinking LED, no Wi-Fi and no ADB. The only documented way out is Qualcomm EDL
  mode with a third-party firehose loader.

So this toolkit **refuses** those packages. There is no override flag, and
asking nicely will not produce one. Unknown packages are treated as risky, never
as safe.

One more, cheap to get wrong: after `pm disable-user`, run `adb shell sync` and
wait before rebooting, or your whole batch silently disappears.

## Security

On many of these boxes ADB is open on port 5555 at every boot regardless of what
the settings say, and it runs as root. Anyone on the same Wi-Fi can do anything
to the device. Keep it on a network you trust, and let the toolkit close
debugging when it is done — it verifies the port is actually shut rather than
trusting the toggle.

## Repo layout

| Path | What it is |
|---|---|
| `PROMPT.md` | the real interface: paste it into Claude Code |
| `AGENTS.md` | the rules the agent may not break |
| `tools/` | the agent's hands: probe, diagnose, disable, restore, check |
| `references/` | classification, evidence sources, device families, power test |
| `profiles/<brand>-<model>/` | what a real device reported, anonymised |
| `recovery/<brand>-<model>.md` | how to get that model back, written after a probe |

## Credit

The approach, and the pure-Python ADB client this project adapts, come from
[Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv) (MIT) — the same
idea for Android TVs. The documented bricking cases come from
[teab0www/carlinkit-tbox-ultra2-recovery](https://github.com/teab0www/carlinkit-tbox-ultra2-recovery),
and the ADB-runs-as-root warning from
[hamza39460/headunit-debloat-skill](https://github.com/hamza39460/headunit-debloat-skill).

Français : [README.fr.md](README.fr.md)

MIT.

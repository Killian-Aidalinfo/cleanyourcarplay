# Device families: which box is in front of you

Two kinds of hardware get called "Chinese CarPlay box". They share nothing
technically, and this toolkit handles exactly one of them.

## Android AI Box — in scope

Carlinkit TBox / TBox Ultra / Ultra 2, Ottocast Play2Video, and a long tail of
clones. A full Android device (typically Android 11–15, Qualcomm or Allwinner),
with a package manager, ADB, and a vendor mirroring stack that projects into the
car's CarPlay window.

**Tells:**
- ADB connects and `getprop ro.build.version.release` returns an Android version
- `pm list packages` returns hundreds of packages
- There is a Play Store, or at least a vendor app store
- Storage is measured in tens of gigabytes

Everything in this repo applies.

## Linux dongle — out of scope

Carlinkit 3.0 / 4.0 / 5.0, CPC200-CCPA, CPC200-CCPW, Ottocast U2-X and similar
small adapters. Embedded Linux on a small SoC (Allwinner V851/V853 and
relatives). No Android, no packages, no `pm`, usually no ADB at all.

**Tells:**
- ADB does not connect, on any port
- The device exposes a configuration web page when you join its access point —
  commonly around `192.168.50.x`
- It is physically small, often a USB dongle rather than a box
- There is no app store, because there are no apps

**There is nothing here to debloat.** These devices have no bloat in the Android
sense: they run one firmware image that does one job. Making them better means
tuning or replacing that firmware, which is a different craft and a different
project.

Send people with a Linux dongle to:

- [catplay](https://github.com/catplay-labs/catplay) — open CarPlay firmware,
  Rust, actively developed
- [ludwig-v/wireless-carplay-dongle-reverse-engineering](https://github.com/ludwig-v/wireless-carplay-dongle-reverse-engineering)
  — the reference reverse-engineering work
- [abdulwaheedsyed/carlinkit_cp2a_lag_project](https://github.com/abdulwaheedsyed/carlinkit_cp2a_lag_project)
  — lag and stutter tuning notes for the CPC200-CP2A

## What the toolkit does about it

`tools/box.py --probe` classifies the device before anything else happens. On a
Linux dongle it exits with status 2, says plainly that the device is out of
scope and why, and prints the links above. It does not try to be clever, and it
does not half-support it.

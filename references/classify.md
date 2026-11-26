# Classification: NEVER / RISKY / SAFE

This file is the product. Everything else is plumbing.

The rule that governs it: **an unknown package is RISKY, never SAFE.** If
`dumpsys package <name>` does not make a package's role obvious, it does not get
disabled without asking the user, and it never gets added to SAFE on a hunch.

---

## Why the stakes are different from a TV

A TV has a screen, a remote and a settings menu. Disable the wrong thing and you
walk over and re-enable it.

An Android CarPlay box has **none of those**. It renders into the car's CarPlay
window, it has no remote, and its settings menu is unreachable without a working
mirroring stack. ADB over the network is the only way back, so any change that
stops the device booting — or merely stops Wi-Fi coming up — destroys the channel
that would have undone it.

Two documented cases, both from
[teab0www/carlinkit-tbox-ultra2-recovery](https://github.com/teab0www/carlinkit-tbox-ultra2-recovery)
(Carlinkit TBox Ultra 2, X21-SC162, Snapdragon 690, Android 15):

**1. Touch loss with no visible failure.** `com.carsyso.main` hosts the
accessibility service that injects the car screen's touches into CarPlay.
Disabled, the box boots, the picture appears, and the screen stops responding.
Nothing crashes. The user has no way to act on the device at all.

**2. Boot loop with no software way out.** APEX-bundled packages on Android 13+,
disabled, produce a boot loop, a blinking LED, no Wi-Fi and no ADB. The only
documented exit is Qualcomm EDL mode (9008) with a third-party firehose loader.

---

## NEVER

The tools refuse these. **There is no override flag.** If a user insists, the
agent explains why and does not do it.

### The mirroring stack

This is the box's entire reason to exist. On the reference device these are:

| Package | Role |
|---|---|
| `com.carsyso.main` | **accessibility service that injects touch into CarPlay** |
| `com.carsyso.bluetooth` | phone pairing |
| `com.suding.speedplay` | mirroring |
| `carnetos.usbmedia` | USB transport to the head unit |
| `com.suding.settings` | vendor settings the stack depends on |
| `com.suding.led` | status LED |
| `com.android.launcher3` | the home the stack is launched from |

**Vendor package names differ per manufacturer.** Do not copy this list to
another box. The probe identifies the stack on the device in front of you by
asking which package owns the bound accessibility service, and which packages
hold the display, USB and audio permissions. Anything it finds that way is NEVER
on that device, whatever it is called.

### APEX on Android 13+

- `com.android.adservices.api`
- `com.android.sdksandbox`
- `com.android.federatedcompute.services`
- `com.android.ondevicepersonalization.services`

Boot loop, no Wi-Fi, no ADB, EDL to recover.

### Keeping the device alive and reachable

Wi-Fi, Bluetooth, networking, telephony and radio packages; `com.android.systemui`;
`com.android.shell`; `com.android.settings`; `android`;
`com.android.providers.*` except calendar, contacts, dictionary and blocked
numbers; the permission controller; the package installer; ext services and ext
shared; `com.google.android.overlay.modules*` and module-related
`com.android.*` / `com.google.android.*`.

### Anything wearing the vendor's name whose role is unknown

On these boxes the vendor's own packages *are* the product. A package named
after the manufacturer is NEVER until the probe has established what it does.

---

## RISKY

Disabled **only after an explicit question**, with the consequence stated before
the user answers.

| Package group | Ask | Consequence if disabled |
|---|---|---|
| Android Auto stack | "Do you use Android Auto as well as CarPlay?" | Android phones stop working with the box. **Never assume CarPlay-only — this depends on the phones in the household.** |
| Bluetooth audio / calls through the box | "Do calls and audio go through the box or the car?" | Calls and audio fall back to the car's own Bluetooth, which may be what you want, or may be worse |
| `com.google.android.gms`, `com.google.android.gsf` | "Keep Google Play Services?" | On some Android 13+ firmwares this breaks Bluetooth pairing flows and the text-to-speech used by navigation. Also removes Play Store, Find My Device |
| Firmware update service | "Keep firmware updates?" | No more vendor fixes. Often reasonable on a box you have just stabilised, but it is the user's call |
| Voice assistant | "Keep the voice assistant?" | No wake word, no voice search on the box itself. CarPlay's own Siri is unaffected |

---

## SAFE

Disabled without asking, because an adapter has exactly one job and none of
these serve it.

- Play Store (`com.android.vending`)
- Google apps: Gmail, YouTube, Chrome, Maps, Google app, Photos, Drive
- The vendor's own app store and its updater
- Web browsers
- Media players, galleries, music apps
- File explorers
- Telemetry, analytics, crash and feedback reporters
- Live wallpapers, screensavers, easter eggs, demo and retail-mode apps
- Printing, NFC payment, and other services with no meaning in a car
- Factory and engineering menu apps — **disable them, never launch them.**
  `dumpsys package <name>` tells you what you need. Launching a factory menu on
  these devices can write to partitions.

This list is much longer than the equivalent for a TV, because a TV has to stay
usable as a TV. An adapter does not.

---

## Procedural rules that belong to this file

1. **Small batches.** Never a large sweep. Until it is proven on hardware that
   the mirroring accessibility service binds *outside a car* (it may require a
   USB host to be present), desk verification proves nothing about touch — in
   that case, **one package family per in-car cycle.**
2. **`adb shell sync` and wait before every reboot.** On the reference device an
   entire batch was lost because the reboot came too soon.
3. **Survival check after every batch**, before the next one: the mirroring
   accessibility service is still bound, Wi-Fi is up, ADB answers, a screencap
   is obtained. Four greens or stop.
4. **An injected tap is not proof of touch.** `input tap` goes through a
   different path than a finger on the car's screen. Only a human pressing the
   real screen proves touch still works.
5. **If `pm disable-user` is refused for every package, stop and say so.** Do
   not retry in a loop.

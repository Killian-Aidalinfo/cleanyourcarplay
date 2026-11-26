#!/usr/bin/env python3
"""Sort packages into NEVER / RISKY / SAFE.

The rule that governs everything here: **an unknown package is RISKY, never
SAFE.** Getting this wrong on a TV costs a trip to the settings menu. Getting it
wrong on a CarPlay box costs the touchscreen, or the device.

The human-readable version of these rules, with the reasons, is
references/classify.md. The two must say the same thing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

NEVER = "NEVER"
RISKY = "RISKY"
SAFE = "SAFE"

# --------------------------------------------------------------------------
# NEVER
# --------------------------------------------------------------------------

# APEX-bundled on Android 13+. Disabling these gives a boot loop, a blinking
# LED, no Wi-Fi and no ADB. Only documented exit: Qualcomm EDL.
# AOSP spells these com.android.*; a build with Google Mobile Services —
# which is most AI Boxes, they ship the Play Store — spells the very same
# modules com.google.android.*. Verified on an arm64 Android 15 GMS image:
# only the com.google.* names are present there. Both spellings belong here,
# because the one that is missing costs nothing and the one that is missing
# from the list costs the device.
APEX_13 = {
    "com.android.adservices.api",
    "com.android.sdksandbox",
    "com.android.federatedcompute.services",
    "com.android.ondevicepersonalization.services",
    "com.google.android.adservices.api",
    "com.google.android.sdksandbox",
    "com.google.android.federatedcompute",
    "com.google.android.federatedcompute.services",
    "com.google.android.ondevicepersonalization.services",
    "com.google.mainline.adservices",
}

# The mirroring stack as documented on the Carlinkit TBox Ultra 2. Vendor names
# differ per manufacturer, which is why detect_mirroring_stack() exists: these
# are a floor, not the list.
KNOWN_MIRRORING = {
    "com.carsyso.main",          # accessibility service that injects touch
    "com.carsyso.bluetooth",
    "com.suding.speedplay",
    "carnetos.usbmedia",
    "com.suding.settings",
    "com.suding.led",
    "com.android.launcher3",
}

# Keeping the device alive and, above all, reachable.
SURVIVAL = {
    "android",
    "com.android.systemui",
    "com.android.shell",
    "com.android.settings",
    "com.android.phone",
    "com.android.server.telecom",
    "com.android.bluetooth",
    "com.android.keychain",
    "com.android.permissioncontroller",
    "com.android.packageinstaller",
    "com.google.android.permissioncontroller",
    "com.google.android.packageinstaller",
    "com.android.externalstorage",
    "com.android.providers.settings",
    "com.android.providers.media",
    "com.android.providers.downloads",
    "com.android.providers.telephony",
    "com.android.inputdevices",
    "com.android.location.fused",
    "com.android.wifi.resources",
    "com.android.networkstack",
    "com.android.se",
}

SURVIVAL_PREFIXES = (
    "com.android.providers.",          # minus the few allowed below
    "com.android.networkstack",
    "com.android.wifi",
    "com.android.bluetooth",
    "com.android.hotspot",
    "com.android.telephony",
    "com.google.android.overlay.modules",
    "com.google.android.modulemetadata",
    "com.android.cellbroadcast",
    "com.qualcomm.qti.telephony",
    "com.qualcomm.qti.wifi",
    "org.codeaurora.ims",
)

PROVIDERS_ALLOWED = {
    "com.android.providers.calendar",
    "com.android.providers.contacts",
    "com.android.providers.userdictionary",
    "com.android.providers.blockednumber",
}

# --------------------------------------------------------------------------
# RISKY — only after an explicit question, consequence stated first
# --------------------------------------------------------------------------

RISKY_GROUPS = {
    "android_auto": {
        "question": "Do you use Android Auto as well as CarPlay?",
        "consequence": "Android phones stop working with the box.",
        "packages": {
            "com.google.android.projection.gearhead",
            "com.google.android.gms.car",
            "com.android.car.projection",
        },
    },
    "bluetooth_audio": {
        "question": "Do calls and audio go through the box, or the car's own Bluetooth?",
        "consequence": "Calls and audio fall back to the car's Bluetooth.",
        "packages": {
            "com.android.bluetoothmidiservice",
            "com.qualcomm.qti.bluetooth_audio",
        },
    },
    "play_services": {
        "question": "Keep Google Play Services?",
        "consequence": (
            "On some Android 13+ firmwares this breaks Bluetooth pairing flows "
            "and the text-to-speech used by navigation. Also removes Play "
            "Store and Find My Device."
        ),
        "packages": {"com.google.android.gms", "com.google.android.gsf"},
    },
    "firmware_update": {
        "question": "Keep firmware updates?",
        "consequence": "No more vendor fixes for this box.",
        "packages": {
            "com.google.android.gms.update",
            "com.android.updater",
            "com.mediatek.systemupdate",
            "com.droidlogic.otaupgrade",
        },
    },
    "voice_assistant": {
        "question": "Keep the voice assistant?",
        "consequence": "No wake word on the box. CarPlay's own Siri is unaffected.",
        "packages": {
            "com.google.android.googlequicksearchbox",
            "com.quicinc.voice.activation",
            "com.qualcomm.qti.voiceai.speech",
        },
    },
}

# --------------------------------------------------------------------------
# SAFE — an adapter has one job and none of these serve it
# --------------------------------------------------------------------------

SAFE_EXACT = {
    "com.android.vending",
    "com.google.android.apps.maps",
    "com.google.android.gm",
    "com.google.android.youtube",
    "com.android.chrome",
    "com.google.android.apps.photos",
    "com.google.android.apps.docs",
    "com.google.android.videos",
    "com.google.android.music",
    "com.google.android.apps.tachyon",
    "com.google.android.feedback",
    "com.google.android.partnersetup",
    "com.google.android.printservice.recommendation",
    "com.google.android.apps.turbo",
    "com.android.printspooler",
    "com.android.bips",
    "com.android.egg",
    "com.android.protips",
    "com.android.dreams.basic",
    "com.android.dreams.phototable",
    "com.android.wallpaper.livepicker",
    "com.android.galaxy4",
    "com.android.noisefield",
    "com.android.magicsmoke",
    "com.android.musicvis",
    "com.android.traceur",
    "com.android.browser",
    "com.android.gallery3d",
    "com.android.music",
    "com.estrongs.android.pop",
    "com.apkpure.aegon",
    "com.android.calendar",
    "com.android.email",
}

SAFE_PREFIXES = (
    "com.google.android.apps.",
    "com.google.android.youtube",
    "com.google.android.marvin",
    "com.android.wallpaper",
    "com.android.dreams",
)

# Factory and engineering menus: disable, never launch. Launching one on these
# devices can write to partitions.
FACTORY_HINTS = ("factory", "engineermode", "engineer", "mmitest", "autotest", "ddrtest")

SAFE_HINTS = (
    "livewallpaper", "wallpaper", "screensaver", "daydream",
    "demo", "retaildemo", "analytics", "telemetry", "crashreport",
    "appstore", "marketplace", "browser", "filemanager", "fileexplorer",
    "videoplayer", "musicplayer", "gallery",
)


class Classifier:
    """Classify packages for one specific device.

    ``mirroring`` is the stack detected on the device in front of us. It comes
    from the probe (packages owning a bound accessibility service), not from a
    hardcoded list, because vendor names differ per manufacturer.
    """

    def __init__(self, sdk: int = 0, mirroring=None, vendor_prefixes=None):
        self.sdk = sdk
        self.mirroring = set(mirroring or ())
        self.vendor_prefixes = tuple(vendor_prefixes or ())

    # -- helpers ---------------------------------------------------------

    def _is_survival(self, package: str) -> bool:
        if package in SURVIVAL:
            return True
        if package in PROVIDERS_ALLOWED:
            return False
        for prefix in SURVIVAL_PREFIXES:
            if package.startswith(prefix):
                return True
        return False

    def _risky_group(self, package: str):
        for name, group in RISKY_GROUPS.items():
            if package in group["packages"]:
                return name
        return None

    def _is_safe(self, package: str) -> bool:
        if package in SAFE_EXACT:
            return True
        if package.startswith(SAFE_PREFIXES):
            return True
        lowered = package.lower()
        if any(hint in lowered for hint in FACTORY_HINTS):
            return True
        if any(hint in lowered for hint in SAFE_HINTS):
            return True
        return False

    # -- the decision ----------------------------------------------------

    def classify(self, package: str) -> tuple:
        """Return (verdict, reason). Order matters: NEVER wins over everything."""
        if package in self.mirroring:
            return NEVER, "mirroring stack on this device — disabling it costs the touchscreen"
        if package in KNOWN_MIRRORING:
            return NEVER, "known mirroring stack package"
        if package in APEX_13:
            if self.sdk >= 33:
                return NEVER, "APEX-bundled on Android 13+ — boot loop, no Wi-Fi, no ADB, EDL to recover"
            if self.sdk <= 0:
                # No probe, no SDK. Reading that as "older than 13" would turn
                # the worst outcome in this repo into a question the user can
                # answer yes to. Unknown is treated as 13+.
                return NEVER, "APEX-bundled, and this device's Android version is unknown — treated as 13+ (boot loop, no Wi-Fi, no ADB, EDL to recover)"
            return RISKY, "APEX on newer Android; this device reports SDK %d" % self.sdk
        if self._is_survival(package):
            return NEVER, "keeps the device alive and reachable"
        if self.vendor_prefixes and package.startswith(self.vendor_prefixes):
            if self._risky_group(package) is None and not self._is_safe(package):
                return NEVER, "vendor package with an unestablished role — on these boxes the vendor's packages are the product"

        group = self._risky_group(package)
        if group is not None:
            return RISKY, "ask first: %s" % RISKY_GROUPS[group]["question"]

        if self._is_safe(package):
            return SAFE, "not needed by a wireless CarPlay adapter"

        return RISKY, "unknown package — unknown is never safe"

    def classify_all(self, packages) -> dict:
        result = {NEVER: [], RISKY: [], SAFE: []}
        reasons = {}
        for package in sorted(packages):
            verdict, reason = self.classify(package)
            result[verdict].append(package)
            reasons[package] = reason
        return {"verdicts": result, "reasons": reasons}


def vendor_prefixes_from(probe: dict) -> tuple:
    """Guess the vendor's own package namespace from the device's identity."""
    seeds = []
    for key in ("brand", "manufacturer", "device"):
        value = (probe.get(key) or "").strip().lower()
        value = re.sub(r"[^a-z0-9]", "", value)
        if len(value) >= 3 and value not in ("android", "google", "unknown"):
            seeds.append(value)
    return tuple("com.%s" % seed for seed in dict.fromkeys(seeds))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify a package list into NEVER / RISKY / SAFE."
    )
    parser.add_argument("packages", help="file with one package per line, or '-'")
    parser.add_argument("--probe", help="probe.json for this device")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    stream = sys.stdin if args.packages == "-" else open(args.packages)
    packages = [
        line.strip()
        for line in stream
        if line.strip() and not line.startswith("#")
    ]

    probe = {}
    if args.probe and os.path.exists(args.probe):
        with open(args.probe) as handle:
            probe = json.load(handle)

    classifier = Classifier(
        sdk=int(probe.get("sdk") or 0),
        mirroring=probe.get("accessibility_services"),
        vendor_prefixes=vendor_prefixes_from(probe),
    )
    outcome = classifier.classify_all(packages)

    if args.json:
        print(json.dumps(outcome, indent=2, sort_keys=True))
        return 0

    for verdict in (NEVER, RISKY, SAFE):
        entries = outcome["verdicts"][verdict]
        print("\n%s (%d)" % (verdict, len(entries)))
        for package in entries:
            print("  %-55s %s" % (package, outcome["reasons"][package]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

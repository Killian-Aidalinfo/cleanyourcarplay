#!/usr/bin/env python3
"""Capture a device's state: the backup, the contribution, and the fixtures.

Three jobs in one pass:

1. **Backup** — what this box looked like before anything was touched. It is
   what restore.sh replays.
2. **Contribution** — an anonymised profile another owner of the same model can
   use. See CONTRIBUTING.md.
3. **Fixtures** — raw dumps kept locally so the classification can be developed
   and tested without the hardware, which matters because no box here is
   sacrificial.

Committed files carry derived facts only. Raw dumps go under ``raw/`` and are
gitignored: they contain IP, SSID, serial, MAC, paired phone names, Bluetooth
history and often location.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from box import Box, BoxError, NotAndroid, OUT_OF_SCOPE, redact, resolve_host, slug

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The only settings this toolkit is allowed to change, so the only ones worth
# snapshotting. Each must be restorable. See the spec, §7.9.
SETTINGS_KEYS = [
    ("global", "window_animation_scale"),
    ("global", "transition_animation_scale"),
    ("global", "animator_duration_scale"),
    ("global", "wifi_sleep_policy"),
    ("global", "wifi_scan_always_enabled"),
    ("global", "stay_on_while_plugged_in"),
    ("secure", "enabled_accessibility_services"),
]

# Raw dumps worth keeping as fixtures. Local only.
RAW_DUMPS = [
    ("getprop.txt", "getprop"),
    ("packages.txt", "pm list packages -f"),
    ("packages-disabled.txt", "pm list packages -d"),
    ("dumpsys-accessibility.txt", "dumpsys accessibility"),
    ("dumpsys-dropbox.txt", "dumpsys dropbox --print"),
    ("meminfo.txt", "cat /proc/meminfo"),
    ("ps.txt", "ps -A"),
]


def capture_settings(box: Box) -> dict:
    settings = {}
    for namespace, key in SETTINGS_KEYS:
        try:
            value = box.shell("settings get %s %s" % (namespace, key)).strip()
        except BoxError:
            continue
        settings["%s/%s" % (namespace, key)] = value
    return settings


def write_profile(box: Box, probe: dict, keep_raw: bool = True) -> str:
    root = os.path.join(REPO, "profiles", slug(probe))
    os.makedirs(root, exist_ok=True)

    with open(os.path.join(root, "probe.json"), "w") as handle:
        json.dump(probe, handle, indent=2, sort_keys=True)
        handle.write("\n")

    enabled = set(box.packages("-e"))
    disabled = set(box.packages("-d"))
    lines = [
        "# %s %s — packages as found, before any change." % (probe["brand"], probe["model"]),
        "# 'disabled' means it was already disabled when we arrived; restore.sh",
        "# leaves those alone.",
        "",
    ]
    for package in sorted(enabled | disabled):
        lines.append("%s\t%s" % (package, "disabled" if package in disabled else "enabled"))
    with open(os.path.join(root, "packages.txt"), "w") as handle:
        handle.write(redact("\n".join(lines)) + "\n")

    with open(os.path.join(root, "settings.json"), "w") as handle:
        json.dump(capture_settings(box), handle, indent=2, sort_keys=True)
        handle.write("\n")

    if keep_raw:
        raw_dir = os.path.join(root, "raw")
        os.makedirs(raw_dir, exist_ok=True)
        for filename, command in RAW_DUMPS:
            try:
                output = box.shell(command)
            except BoxError as exc:
                output = "<failed: %s>" % exc
            with open(os.path.join(raw_dir, filename), "w") as handle:
                handle.write(output)
        with open(os.path.join(raw_dir, "README.txt"), "w") as handle:
            handle.write(
                "Raw dumps. NOT anonymised, NOT committed (see .gitignore).\n"
                "They contain IP, SSID, serial, MAC, paired phone names and\n"
                "often location. Use them as fixtures, never paste them into\n"
                "an issue.\n"
            )
    return root


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Capture a device profile. Read-only.")
    parser.add_argument("--host", help="device address, or set BOX_HOST")
    parser.add_argument("--no-raw", action="store_true", help="skip the local raw dumps")
    args = parser.parse_args(argv)

    host, port = resolve_host(args.host)
    box = Box(host, port)
    try:
        box.connect()
        try:
            probe = box.probe()
        except NotAndroid:
            print(OUT_OF_SCOPE, file=sys.stderr)
            return 2
        root = write_profile(box, probe, keep_raw=not args.no_raw)
    except BoxError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    finally:
        box.close()

    print("profile written to %s" % root)
    print("  probe.json, packages.txt, settings.json are safe to commit")
    if not args.no_raw:
        print("  raw/ is gitignored and stays on this machine")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

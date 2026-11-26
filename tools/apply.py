#!/usr/bin/env python3
"""Disable packages, restore them, and refuse to do the one thing that bricks.

Every change is journalled to ``profiles/<slug>/changes.jsonl`` before it is
made, so a device that reboots mid-batch can still be put back.

Three rules live in code here, not in documentation:

* a NEVER package is refused — there is no override flag, and adding one would
  defeat the purpose of the project;
* ``sync`` runs and we wait before suggesting a reboot, because an entire batch
  was lost that way on the reference device;
* if every single package is refused by ``pm``, we stop and say so rather than
  looping.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from box import Box, BoxError, NotAndroid, OUT_OF_SCOPE, resolve_host, slug
from classify import NEVER, Classifier, vendor_prefixes_from

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNC_WAIT_SECONDS = 15


def profile_dir(probe: dict) -> str:
    root = os.path.join(REPO, "profiles", slug(probe))
    os.makedirs(root, exist_ok=True)
    return root


def journal(root: str, entry: dict) -> None:
    entry["at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with open(os.path.join(root, "changes.jsonl"), "a") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def read_journal(root: str) -> list:
    path = os.path.join(root, "changes.jsonl")
    if not os.path.exists(path):
        return []
    entries = []
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def classifier_for(box: Box, probe: dict) -> Classifier:
    return Classifier(
        sdk=int(probe.get("sdk") or 0),
        mirroring=probe.get("accessibility_services"),
        vendor_prefixes=vendor_prefixes_from(probe),
    )


def survival_check(box: Box, probe: dict) -> dict:
    """Four greens or stop: accessibility bound, Wi-Fi up, ADB answering, screencap.

    Note the limit, stated here and in references/classify.md: this does NOT
    prove touch still works. An injected tap is not a finger on the car's
    screen. Only a human in the car proves that.
    """
    checks = {}
    try:
        checks["adb"] = box.shell("echo alive").strip() == "alive"
    except BoxError:
        checks["adb"] = False

    expected = set(probe.get("accessibility_services") or ())
    if expected:
        try:
            checks["accessibility"] = expected.issubset(set(box.accessibility_services()))
        except BoxError:
            checks["accessibility"] = False
    else:
        checks["accessibility"] = None  # nothing was bound to begin with

    try:
        wifi = box.shell("dumpsys wifi | head -40")
        checks["wifi"] = "Wi-Fi is enabled" in wifi or "enabled" in wifi.lower()
    except BoxError:
        checks["wifi"] = False

    try:
        data = box.pull_binary("screencap -p")
        checks["screencap"] = data.startswith(b"\x89PNG")
    except BoxError:
        checks["screencap"] = False

    checks["ok"] = all(v for v in checks.values() if v is not None)
    return checks


def disable(box: Box, probe: dict, packages: list, assume_yes: bool = False) -> int:
    root = profile_dir(probe)
    classifier = classifier_for(box, probe)

    refused, planned = [], []
    for package in packages:
        verdict, reason = classifier.classify(package)
        if verdict == NEVER:
            refused.append((package, reason))
        else:
            planned.append((package, verdict, reason))

    if refused:
        print("Refused — these are NEVER packages on this device:\n")
        for package, reason in refused:
            print("  %-50s %s" % (package, reason))
        print(
            "\nThere is no flag to override this. Disabling one of these costs "
            "the touchscreen or the device, and this box has no screen, no "
            "remote and no reset button to get it back.\n"
        )

    if not planned:
        print("Nothing left to do.")
        return 1 if refused else 0

    print("Will disable %d package(s):" % len(planned))
    for package, verdict, reason in planned:
        print("  [%s] %-45s %s" % (verdict, package, reason))

    if not assume_yes:
        answer = input("\nProceed? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Stopped. Nothing was changed.")
            return 1

    succeeded, failed = [], []
    for package, verdict, _reason in planned:
        journal(root, {"action": "disable", "package": package, "verdict": verdict})
        try:
            output = box.shell("pm disable-user --user 0 %s" % package).strip()
        except BoxError as exc:
            output = "error: %s" % exc
        if "new state: disabled" in output or "disabled-user" in output:
            succeeded.append(package)
            print("  disabled %s" % package)
        else:
            failed.append((package, output))
            print("  FAILED   %s — %s" % (package, output))

    if not succeeded and failed:
        print(
            "\nEvery package was refused by pm. That usually means this shell "
            "lacks the rights, not that the list is wrong. Stopping rather "
            "than retrying."
        )
        return 1

    print("\nSyncing and waiting %ds before any reboot." % SYNC_WAIT_SECONDS)
    print("(An entire batch was lost on the reference device by rebooting too soon.)")
    try:
        box.shell("sync")
    except BoxError:
        pass
    time.sleep(SYNC_WAIT_SECONDS)

    checks = survival_check(box, probe)
    print("\nSurvival check: %s" % ("OK" if checks["ok"] else "PROBLEM"))
    for name in ("adb", "accessibility", "wifi", "screencap"):
        value = checks.get(name)
        label = "n/a" if value is None else ("ok" if value else "FAILED")
        print("  %-14s %s" % (name, label))
    if not checks["ok"]:
        print("\nDo not run another batch. Run tools/restore.sh and investigate.")
        return 1

    print(
        "\nThis does not prove touch still works. An injected tap is not a "
        "finger on the car's screen — test in the car before the next batch."
    )
    return 0


def restore(box: Box, probe: dict) -> int:
    root = profile_dir(probe)
    entries = [e for e in read_journal(root) if e.get("action") == "disable"]
    if not entries:
        print("No recorded changes for this device. Nothing to restore.")
        return 0

    packages = sorted({e["package"] for e in entries})
    print("Re-enabling %d package(s) recorded for this device." % len(packages))
    failures = []
    for package in packages:
        try:
            output = box.shell("pm enable --user 0 %s" % package).strip()
        except BoxError as exc:
            output = "error: %s" % exc
        if "new state: enabled" in output:
            print("  enabled %s" % package)
            journal(root, {"action": "restore", "package": package})
        else:
            failures.append((package, output))
            print("  FAILED  %s — %s" % (package, output))

    settings_path = os.path.join(root, "settings.json")
    if os.path.exists(settings_path):
        with open(settings_path) as handle:
            saved = json.load(handle)
        for key, value in saved.items():
            namespace, _, name = key.partition("/")
            if value and value != "null":
                try:
                    box.shell("settings put %s %s %s" % (namespace, name, value))
                except BoxError:
                    pass
        print("  settings replayed from settings.json")

    try:
        box.shell("sync")
    except BoxError:
        pass
    print("\nSynced. Reboot the box to be sure everything is back.")
    return 1 if failures else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Disable or restore packages.")
    parser.add_argument("action", choices=["disable", "restore", "check"])
    parser.add_argument("packages", nargs="?", help="file with one package per line")
    parser.add_argument("--host", help="device address, or set BOX_HOST")
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation")
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

        if args.action == "check":
            checks = survival_check(box, probe)
            for name in ("adb", "accessibility", "wifi", "screencap"):
                value = checks.get(name)
                print("%-14s %s" % (name, "n/a" if value is None else ("ok" if value else "FAILED")))
            return 0 if checks["ok"] else 1

        if args.action == "restore":
            return restore(box, probe)

        if not args.packages:
            parser.error("disable needs a package list file")
        with open(args.packages) as handle:
            packages = [
                line.split("#")[0].strip()
                for line in handle
                if line.strip() and not line.startswith("#")
            ]
        packages = [p for p in packages if p]
        return disable(box, probe, packages, assume_yes=args.yes)
    except BoxError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    finally:
        box.close()


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Compare the device to its recorded profile and report drift.

A firmware update, a factory reset, or someone poking at the settings can undo
this toolkit's work silently. Run this after any of those, or when the box
starts misbehaving again, before assuming the cleanup is at fault.

Read-only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from box import Box, BoxError, NotAndroid, OUT_OF_SCOPE, resolve_host, slug
from apply import profile_dir, read_journal

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(box: Box, probe: dict) -> int:
    root = profile_dir(probe)

    recorded = os.path.join(root, "probe.json")
    if os.path.exists(recorded):
        with open(recorded) as handle:
            before = json.load(handle)
        for key in ("android_release", "build_id"):
            if before.get(key) and before[key] != probe.get(key):
                print("CHANGED  %s: %s -> %s" % (key, before[key], probe[key]))
                print("         The firmware moved. Expect the package list to have moved too.")

    expected_disabled = {
        entry["package"] for entry in read_journal(root) if entry.get("action") == "disable"
    }
    restored = {
        entry["package"] for entry in read_journal(root) if entry.get("action") == "restore"
    }
    expected_disabled -= restored

    if not expected_disabled:
        print("No packages are recorded as disabled by this toolkit.")
        return 0

    actually_disabled = set(box.packages("-d"))
    drifted = sorted(expected_disabled - actually_disabled)

    print("%d package(s) should be disabled." % len(expected_disabled))
    if drifted:
        print("\n%d came back on their own:" % len(drifted))
        for package in drifted:
            print("  %s" % package)
        print("\nRun tools/disable.sh with these to put them back, after checking")
        print("they are still classified the same way on the current firmware.")
        path = os.path.join(root, "drift.txt")
        with open(path, "w") as handle:
            handle.write("\n".join(drifted) + "\n")
        print("Written to %s" % path)
        return 1

    print("No drift. Everything this toolkit disabled is still disabled.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check a device against its profile.")
    parser.add_argument("--host", help="device address, or set BOX_HOST")
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
        return check(box, probe)
    except BoxError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    finally:
        box.close()


if __name__ == "__main__":
    raise SystemExit(main())

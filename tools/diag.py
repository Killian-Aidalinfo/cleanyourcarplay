#!/usr/bin/env python3
"""Why did this box crash or reboot? Read-only.

Android keeps most of the evidence across a reboot, so a crash that happened on
the motorway can be read at the desk the next day. Nothing has to be left
running on the device, and this module never writes to it.

Each source supports a narrow claim. See references/diag.md for what each one
does and does not prove. A missing source is reported as unavailable and
dropped from the conclusion — never an exception, never evidence.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from box import Box, BoxError, NotAndroid, OUT_OF_SCOPE, redact, resolve_host, slug

UNAVAILABLE = "<unavailable>"

# Boot-reason fragments that point at the power rail rather than the software.
# Deliberately conservative: an unrecognised value stays unknown.
POWER_MARKERS = ("uvlo", "undervoltage", "power_loss", "pwr_loss", "brownout", "pon_")
CRASH_MARKERS = ("kernel_panic", "watchdog", "rpm", "tz", "hw_reset", "oemerr")
CLEAN_MARKERS = ("reboot", "userrequested", "shutdown", "cold_boot", "powerup", "usb")


def _try(box: Box, command: str) -> str:
    """Run a read command, turning any failure into UNAVAILABLE."""
    try:
        output = box.shell(command).strip()
    except BoxError:
        return UNAVAILABLE
    if not output or "No such file" in output or "not found" in output:
        return UNAVAILABLE
    return output


def boot_reason(box: Box) -> dict:
    """The single most useful value here: power loss or software failure?"""
    values = {}
    for prop in ("sys.boot.reason", "ro.boot.bootreason", "sys.boot.reason.last"):
        value = box.getprop(prop)
        if value:
            values[prop] = value

    verdict = "unknown"
    joined = " ".join(values.values()).lower()
    if joined:
        if any(marker in joined for marker in POWER_MARKERS):
            verdict = "power"
        elif any(marker in joined for marker in CRASH_MARKERS):
            verdict = "software"
        elif any(marker in joined for marker in CLEAN_MARKERS):
            verdict = "clean"
    return {"properties": values or UNAVAILABLE, "verdict": verdict}


def dropbox(box: Box, limit: int = 12) -> dict:
    """Crashes, ANRs, panics and reboot records, timestamped."""
    raw = _try(box, "dumpsys dropbox --print")
    if raw == UNAVAILABLE:
        return {"available": False}
    entries = []
    for line in raw.splitlines():
        match = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (\S+) ", line)
        if match:
            entries.append({"at": match.group(1), "tag": match.group(2)})
    tally: dict = {}
    for entry in entries:
        tally[entry["tag"]] = tally.get(entry["tag"], 0) + 1
    return {
        "available": True,
        "recent": entries[-limit:],
        "tally": dict(sorted(tally.items(), key=lambda kv: -kv[1])),
    }


def pstore(box: Box) -> dict:
    """Survives a kernel panic. Often absent — absence is not a finding."""
    listing = _try(box, "ls /sys/fs/pstore/ 2>/dev/null")
    if listing == UNAVAILABLE:
        return {"available": False}
    return {"available": True, "files": listing.split()}


def thermal(box: Box) -> dict:
    """A temperature at a moment. Only a sustained high reading before a
    reboot supports a thermal conclusion."""
    types = _try(box, "cat /sys/class/thermal/thermal_zone*/type 2>/dev/null")
    temps = _try(box, "cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null")
    if types == UNAVAILABLE or temps == UNAVAILABLE:
        return {"available": False}
    zones = []
    for name, value in zip(types.splitlines(), temps.splitlines()):
        try:
            raw = int(value.strip())
        except ValueError:
            continue
        celsius = raw / 1000.0 if raw > 1000 else float(raw)
        zones.append({"zone": name.strip(), "celsius": round(celsius, 1)})
    hottest = max((z["celsius"] for z in zones), default=None)
    return {"available": bool(zones), "zones": zones, "hottest_c": hottest}


def power(box: Box) -> dict:
    """Weakest link in the chain: on a box with no battery these nodes are
    often missing or meaningless. Supports a hypothesis, proves nothing."""
    names = _try(box, "ls /sys/class/power_supply/ 2>/dev/null")
    if names == UNAVAILABLE:
        return {"available": False}
    supplies = []
    for name in names.split():
        reading = {"name": name}
        for field in ("voltage_now", "current_now", "online", "status"):
            value = _try(
                box, "cat /sys/class/power_supply/%s/%s 2>/dev/null" % (name, field)
            )
            if value != UNAVAILABLE:
                reading[field] = value.splitlines()[0]
        supplies.append(reading)
    return {"available": bool(supplies), "supplies": supplies}


def memory(box: Box) -> dict:
    """Before/after of the cleanup, and the OOM case when free memory is low."""
    raw = _try(box, "cat /proc/meminfo")
    if raw == UNAVAILABLE:
        return {"available": False}
    fields = {}
    for key in ("MemTotal", "MemAvailable", "MemFree", "SwapTotal"):
        match = re.search(r"^%s:\s+(\d+) kB" % key, raw, re.M)
        if match:
            fields[key] = int(match.group(1))
    total = fields.get("MemTotal") or 0
    available = fields.get("MemAvailable") or 0
    return {
        "available": True,
        "total_mb": round(total / 1024) if total else None,
        "available_mb": round(available / 1024) if available else None,
        "free_ratio": round(available / total, 3) if total else None,
    }


def uptime(box: Box) -> dict:
    raw = _try(box, "cat /proc/uptime")
    if raw == UNAVAILABLE:
        return {"available": False}
    try:
        seconds = float(raw.split()[0])
    except (ValueError, IndexError):
        return {"available": False}
    return {"available": True, "seconds": round(seconds), "hours": round(seconds / 3600, 1)}


def diagnose(box: Box) -> dict:
    """Collect everything. Never raises on a missing source."""
    return {
        "schema": 1,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "boot_reason": boot_reason(box),
        "dropbox": dropbox(box),
        "pstore": pstore(box),
        "thermal": thermal(box),
        "power": power(box),
        "memory": memory(box),
        "uptime": uptime(box),
    }


def conclude(result: dict) -> list:
    """Conclude, but only to the strength of the evidence.

    'Signs consistent with power loss' is the strongest honest claim this
    toolkit can make without an instrument. See references/power-test.md.
    """
    lines = []
    verdict = result["boot_reason"]["verdict"]
    uptime_hours = result["uptime"].get("hours")

    if verdict == "power":
        lines.append(
            "The last boot shows **signs consistent with power loss**. On a box "
            "fed from a cigarette-lighter or car USB port this is the first "
            "thing to rule out: try a known-good supply before debloating "
            "anything. references/power-test.md explains how to confirm it."
        )
    elif verdict == "software":
        lines.append(
            "The last boot followed a **software or driver failure** (panic or "
            "watchdog), not a power cut. Debloating is likely to help here."
        )
    elif verdict == "clean":
        lines.append("The last boot was clean — nothing crashed into it.")
    else:
        lines.append(
            "The boot reason is **unknown** on this device: the property is "
            "missing or its value is not one this toolkit recognises. That is "
            "not evidence either way."
        )

    drop = result["dropbox"]
    if drop.get("available") and drop.get("tally"):
        top = list(drop["tally"].items())[:3]
        lines.append(
            "Crash mailbox: " + ", ".join("%s x%d" % (tag, n) for tag, n in top) + "."
        )
    elif drop.get("available"):
        lines.append("Crash mailbox is empty — nothing crashed recently.")

    hottest = result["thermal"].get("hottest_c")
    if hottest is not None:
        if hottest >= 80:
            lines.append(
                "Hottest zone %.1f °C — hot enough to be worth a thermal "
                "explanation. Read it again under mirroring load." % hottest
            )
        else:
            lines.append(
                "Hottest zone %.1f °C at this moment: no thermal case from "
                "this reading alone." % hottest
            )

    mem = result["memory"]
    if mem.get("available") and mem.get("free_ratio") is not None:
        if mem["free_ratio"] < 0.15:
            lines.append(
                "Only %d MB of %d MB available (%.0f%%). Memory pressure this "
                "high makes the out-of-memory killer a plausible cause, and it "
                "is exactly what cleanup fixes."
                % (mem["available_mb"], mem["total_mb"], mem["free_ratio"] * 100)
            )
        else:
            lines.append(
                "%d MB of %d MB available (%.0f%%)."
                % (mem["available_mb"], mem["total_mb"], mem["free_ratio"] * 100)
            )

    if uptime_hours is not None:
        lines.append("Up for %.1f h." % uptime_hours)

    missing = [
        name
        for name in ("dropbox", "pstore", "thermal", "power")
        if not result[name].get("available")
    ]
    if missing:
        lines.append(
            "Not available on this device: %s. Their absence is not a finding."
            % ", ".join(missing)
        )
    return lines


def render(probe: dict, result: dict) -> str:
    out = ["# Diagnosis — %s %s" % (probe.get("brand"), probe.get("model")), ""]
    out.append("Captured %s. Read-only: nothing on the device was changed." % result["captured_at"])
    out.append("")
    out.append("## What this says")
    out.append("")
    for line in conclude(result):
        out.append("- " + line)
    out.append("")
    out.append("## Raw readings")
    out.append("")
    out.append("```json")
    import json as _json

    out.append(_json.dumps(result, indent=2, sort_keys=True))
    out.append("```")
    out.append("")
    out.append("See references/diag.md for what each source proves.")
    return redact("\n".join(out)) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read-only diagnosis of a CarPlay AI Box.")
    parser.add_argument("--host", help="device address, or set BOX_HOST")
    parser.add_argument("--write", action="store_true",
                        help="write the report into profiles/<brand>-<model>/diag.md")
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
        result = diagnose(box)
    except BoxError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    finally:
        box.close()

    report = render(probe, result)
    if args.write:
        root = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "profiles",
            slug(probe),
        )
        os.makedirs(root, exist_ok=True)
        path = os.path.join(root, "diag.md")
        with open(path, "w") as handle:
            handle.write(report)
        print("wrote %s" % path)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

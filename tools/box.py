#!/usr/bin/env python3
"""ADB client and read-only probe for Android CarPlay AI boxes.

Prefers the `adb` binary when it is on PATH. Falls back to a small pure-Python
ADB client over TCP so the Android SDK is not a hard requirement, which is the
common case on these boxes: many of them leave ADB open on port 5555 at every
boot with no authentication.

Adapted from the approach of Gathin23/cleanyourtv (MIT).

Nothing in this module writes to the device.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import time

DEFAULT_PORT = 5555
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 30.0
MAX_PAYLOAD = 256 * 1024

# ADB wire protocol
_A_CNXN = 0x4E584E43
_A_AUTH = 0x48545541
_A_OPEN = 0x4E45504F
_A_OKAY = 0x59414B4F
_A_CLSE = 0x45534C43
_A_WRTE = 0x45545257
_A_VERSION = 0x01000000


class BoxError(Exception):
    """Anything that stops us talking to the device."""


class NotAndroid(BoxError):
    """The device is reachable but is not an Android AI Box."""


# --------------------------------------------------------------------------
# Redaction
# --------------------------------------------------------------------------

_IPV4 = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")

_REDACT = [
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "<ip>"),
    (re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b"), "<mac>"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<email>"),
    (re.compile(r'(?i)\b(ssid|wifi[_-]?name)\b\s*[:=]\s*"?[^"\n,]+'), r"\1=<ssid>"),
    (re.compile(r"(?i)\b(serial(?:no)?|ro\.serialno|android_id)\b\s*[:=]\s*\S+"), r"\1=<redacted>"),
]


def redact(text: str) -> str:
    """Strip the identifiers that must never reach a public profile.

    Applied to everything written to a committed file or printed to the agent.
    Raw dumps keep their secrets and stay gitignored.
    """
    for pattern, replacement in _REDACT:
        text = pattern.sub(replacement, text)
    return text


# --------------------------------------------------------------------------
# Pure-Python ADB over TCP
# --------------------------------------------------------------------------


def _pack(command: int, arg0: int, arg1: int, payload: bytes) -> bytes:
    checksum = sum(payload) & 0xFFFFFFFF
    header = struct.pack(
        "<6I", command, arg0, arg1, len(payload), checksum, command ^ 0xFFFFFFFF
    )
    return header + payload


class _TcpAdb:
    """Minimal ADB client: enough to open a shell stream and read it back.

    Does not implement the RSA auth handshake. A device that demands AUTH gets
    a clear error telling the user to install platform-tools, rather than a
    silent failure.
    """

    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self._sock: socket.socket | None = None
        self._local_id = 1

    def _connect(self) -> socket.socket:
        if self._sock is not None:
            return self._sock
        try:
            sock = socket.create_connection((self.host, self.port), CONNECT_TIMEOUT)
        except OSError as exc:
            raise BoxError("cannot reach %s:%d (%s)" % (self.host, self.port, exc))
        sock.settimeout(READ_TIMEOUT)
        banner = b"host::features=shell_v2,cmd\x00"
        sock.sendall(_pack(_A_CNXN, _A_VERSION, MAX_PAYLOAD, banner))
        command, _, _, payload = self._read_message(sock)
        if command == _A_AUTH:
            sock.close()
            raise BoxError(
                "this device requires ADB authentication.\n"
                "Install Android platform-tools and run:\n"
                "    adb connect %s:%d\n"
                "then accept the prompt. This toolkit will use the adb binary "
                "once it is on PATH." % (self.host, self.port)
            )
        if command != _A_CNXN:
            sock.close()
            raise BoxError("unexpected ADB handshake response 0x%08x" % command)
        self._banner = payload.decode("utf-8", "replace")
        self._sock = sock
        return sock

    @staticmethod
    def _read_exactly(sock: socket.socket, count: int) -> bytes:
        chunks = []
        remaining = count
        while remaining:
            chunk = sock.recv(remaining)
            if not chunk:
                raise BoxError("device closed the connection")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _read_message(self, sock: socket.socket):
        header = self._read_exactly(sock, 24)
        command, arg0, arg1, length, _checksum, magic = struct.unpack("<6I", header)
        if magic != (command ^ 0xFFFFFFFF):
            raise BoxError("corrupt ADB header")
        payload = self._read_exactly(sock, length) if length else b""
        return command, arg0, arg1, payload

    def stream(self, destination: str) -> bytes:
        """Open an ADB service (``shell:...``, ``exec:...``) and read it out."""
        sock = self._connect()
        self._local_id += 1
        local_id = self._local_id
        sock.sendall(_pack(_A_OPEN, local_id, 0, destination.encode() + b"\x00"))

        remote_id = 0
        output = []
        while True:
            command, arg0, arg1, payload = self._read_message(sock)
            if command == _A_OKAY and arg1 == local_id:
                remote_id = arg0
            elif command == _A_WRTE and arg1 == local_id:
                output.append(payload)
                sock.sendall(_pack(_A_OKAY, local_id, arg0, b""))
            elif command == _A_CLSE and arg1 == local_id:
                if remote_id:
                    sock.sendall(_pack(_A_CLSE, local_id, remote_id, b""))
                break
        return b"".join(output)

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None


# --------------------------------------------------------------------------
# Box
# --------------------------------------------------------------------------


class Box:
    """A device we talk to. Read operations only in this module."""

    def __init__(self, host: str, port: int = DEFAULT_PORT, use_adb: bool | None = None):
        self.host = host
        self.port = port
        self.serial = host if port is None else "%s:%d" % (host, port)
        if use_adb is None:
            use_adb = shutil.which("adb") is not None
        if port is None and not use_adb:
            raise BoxError(
                "%s is an ADB serial, not an address, and it can only be "
                "reached through the adb binary. Install adb, or give the "
                "device's IP instead." % host
            )
        self.use_adb = use_adb
        self._tcp = None if use_adb else _TcpAdb(host, port)
        self._props: dict = {}

    # -- transport ---------------------------------------------------------

    def _adb(self, args, binary: bool = False):
        completed = subprocess.run(
            ["adb", "-s", self.serial] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode != 0:
            message = completed.stderr.decode("utf-8", "replace").strip()
            raise BoxError(message or "adb exited %d" % completed.returncode)
        return completed.stdout if binary else completed.stdout.decode("utf-8", "replace")

    def connect(self) -> None:
        """Make the transport usable. Raises BoxError if the device is unreachable."""
        if self.use_adb:
            subprocess.run(
                ["adb", "connect", self.serial],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._adb(["shell", "true"])
        else:
            self._tcp.stream("shell:true")

    def shell(self, command: str) -> str:
        """Run one shell command and return its stdout.

        One command per call, deliberately: it keeps what happened on the
        device legible in the transcript.
        """
        if self.use_adb:
            return self._adb(["shell", command])
        return self._tcp.stream("shell:" + command).decode("utf-8", "replace")

    def pull_binary(self, command: str) -> bytes:
        """Run a command whose output is binary (``screencap -p``)."""
        if self.use_adb:
            return self._adb(["exec-out", command], binary=True)
        return self._tcp.stream("exec:" + command)

    def close(self) -> None:
        if self._tcp is not None:
            self._tcp.close()

    # -- reads -------------------------------------------------------------

    def getprop(self, name: str) -> str:
        if not self._props:
            raw = self.shell("getprop")
            for match in re.finditer(r"^\[([^\]]+)\]: \[(.*)\]$", raw, re.M):
                self._props[match.group(1)] = match.group(2)
        return self._props.get(name, "")

    def packages(self, state: str = "") -> list:
        """Installed packages. ``state`` may be '-e' (enabled) or '-d' (disabled)."""
        raw = self.shell(("pm list packages %s" % state).strip())
        return sorted(
            line[len("package:"):].strip()
            for line in raw.splitlines()
            if line.startswith("package:")
        )

    def accessibility_services(self) -> list:
        """Packages owning a bound accessibility service.

        This is how the mirroring stack is identified on an unknown box: the
        service that injects the car screen's touches into CarPlay is an
        accessibility service, and whatever package owns it is NEVER-disable.
        """
        raw = self.shell("settings get secure enabled_accessibility_services")
        raw = raw.strip()
        if not raw or raw == "null":
            return []
        return sorted({entry.split("/")[0] for entry in raw.split(":") if "/" in entry})

    def screencap(self, path: str) -> str:
        """Save a PNG of what the device is displaying. Our only eyes."""
        data = self.pull_binary("screencap -p")
        if not data.startswith(b"\x89PNG"):
            raise BoxError("screencap did not return a PNG (%d bytes)" % len(data))
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def usb_adb_available(self) -> bool:
        """Is this device also reachable over USB?

        A cable survives a Wi-Fi that no longer comes up, which is this
        project's worst failure mode. Worth knowing before touching anything.
        """
        if shutil.which("adb") is None:
            return False
        if ":" not in self.serial:
            return True          # we are already talking over the cable
        mine = (self.getprop("ro.serialno")
                or self.getprop("ro.boot.serialno")).strip()
        if not mine:
            # Without an identity we cannot tell this device's cable from
            # someone else's phone, and guessing yes would promise a way back
            # that may not exist.
            return False
        listing = subprocess.run(
            ["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        ).stdout.decode("utf-8", "replace")
        for line in listing.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 2 or parts[1] != "device" or ":" in parts[0]:
                continue
            probe = subprocess.run(
                ["adb", "-s", parts[0], "shell", "getprop", "ro.serialno"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            ).stdout.decode("utf-8", "replace").strip()
            if probe and probe == mine:
                return True
        return False

    # -- family ------------------------------------------------------------

    def family(self) -> str:
        """'android', 'linux-dongle' or 'unknown'. See references/families.md."""
        try:
            release = self.getprop("ro.build.version.release")
        except BoxError:
            return "linux-dongle"
        if not release:
            return "unknown"
        return "android" if self.packages() else "unknown"

    def probe(self) -> dict:
        """Everything we can learn without changing anything."""
        family = self.family()
        if family != "android":
            raise NotAndroid(family)

        packages = self.packages()
        disabled = set(self.packages("-d"))
        meminfo = self.shell("cat /proc/meminfo")
        total_kb = 0
        match = re.search(r"MemTotal:\s+(\d+) kB", meminfo)
        if match:
            total_kb = int(match.group(1))

        return {
            "schema": 1,
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "brand": self.getprop("ro.product.brand"),
            "manufacturer": self.getprop("ro.product.manufacturer"),
            "model": self.getprop("ro.product.model"),
            "device": self.getprop("ro.product.device"),
            "android_release": self.getprop("ro.build.version.release"),
            "sdk": self.getprop("ro.build.version.sdk"),
            "build_id": self.getprop("ro.build.display.id"),
            "soc": self.getprop("ro.board.platform")
            or self.getprop("ro.hardware"),
            "ram_mb": round(total_kb / 1024) if total_kb else None,
            "package_count": len(packages),
            "disabled_count": len(disabled),
            "accessibility_services": self.accessibility_services(),
            "usb_adb_available": self.usb_adb_available(),
            "transport": "adb" if self.use_adb else "tcp",
        }


def slug(probe: dict) -> str:
    """Directory name for a device's profile: ``brand-model``."""
    parts = [probe.get("brand") or "unknown", probe.get("model") or "unknown"]
    text = "-".join(parts).lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "unknown-device"


OUT_OF_SCOPE = """\
This device is not an Android AI Box, so there is nothing here to debloat.

It looks like a Linux CarPlay dongle (Carlinkit 3.0/4.0, CPC200-CCPA,
Ottocast U2-X and similar). Those run a single embedded Linux firmware: no
package manager, no packages, nothing to disable. Making them better means
tuning or replacing that firmware, which is a different project.

Try instead:
  https://github.com/catplay-labs/catplay
  https://github.com/ludwig-v/wireless-carplay-dongle-reverse-engineering
  https://github.com/abdulwaheedsyed/carlinkit_cp2a_lag_project

See references/families.md.
"""


def resolve_host(argument: str | None) -> tuple:
    host = argument or os.environ.get("BOX_HOST", "")
    if not host:
        raise SystemExit(
            "No device given. Pass --host <ip> or set BOX_HOST.\n"
            "See docs/CONNECT.md if you do not know the address."
        )
    if ":" in host:
        address, _, port = host.partition(":")
        return address, int(port)
    if _IPV4.match(host) or "." in host or host in ("localhost",):
        return host, DEFAULT_PORT
    # Anything else is an ADB serial: a USB cable, or an emulator transport
    # such as "emulator-5560". Port None means "this is a serial, not a host".
    return host, None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only probe for an Android CarPlay AI Box."
    )
    parser.add_argument("--host", help="device address, or set BOX_HOST")
    parser.add_argument("--probe", action="store_true", help="identify the device")
    parser.add_argument("--shell", metavar="CMD", help="run one shell command")
    parser.add_argument("--screenshot", metavar="PATH", help="save a PNG")
    parser.add_argument("--json", action="store_true", help="machine-readable probe")
    args = parser.parse_args(argv)

    host, port = resolve_host(args.host)
    box = Box(host, port)
    try:
        box.connect()
    except BoxError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    try:
        if args.shell:
            print(redact(box.shell(args.shell)))
            return 0
        if args.screenshot:
            print("saved %s" % box.screencap(args.screenshot))
            return 0

        try:
            probe = box.probe()
        except NotAndroid:
            print(OUT_OF_SCOPE, file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(probe, indent=2, sort_keys=True))
            return 0

        print("%s %s" % (probe["brand"], probe["model"]))
        print("  Android %s (SDK %s), build %s" % (
            probe["android_release"], probe["sdk"], probe["build_id"]))
        print("  SoC %s, RAM %s MB" % (probe["soc"], probe["ram_mb"]))
        print("  %d packages, %d already disabled" % (
            probe["package_count"], probe["disabled_count"]))
        print("  transport: %s%s" % (
            probe["transport"],
            ", USB ADB available" if probe["usb_adb_available"] else ""))
        services = probe["accessibility_services"]
        if services:
            print("  mirroring candidates (NEVER disable): %s" % ", ".join(services))
        else:
            print("  no bound accessibility service seen — see references/classify.md;")
            print("  the mirroring stack may only bind with a USB host present.")
        print("\n  profile slug: %s" % slug(probe))
        return 0
    except BoxError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    finally:
        box.close()


if __name__ == "__main__":
    raise SystemExit(main())

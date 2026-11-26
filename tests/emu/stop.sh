#!/usr/bin/env bash
# Shut the rig down. The AVD and its snapshots survive.
source "$(dirname "$0")/lib.sh"
adb -s "$SERIAL" emu kill >/dev/null 2>&1 || true
echo "$SERIAL stopped."

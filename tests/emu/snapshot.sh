#!/usr/bin/env bash
# Save / load / list snapshots — the reason this rig can be broken on purpose.
#
#   tests/emu/snapshot.sh save clean
#   tests/emu/snapshot.sh load clean
#   tests/emu/snapshot.sh list
source "$(dirname "$0")/lib.sh"
require_running

action="${1:-list}"
name="${2:-clean}"
case "$action" in
    save) adb_box emu avd snapshot save "$name" && echo "saved: $name" ;;
    load) adb_box emu avd snapshot load "$name" && echo "loaded: $name" ;;
    list) adb_box emu avd snapshot list ;;
    *) echo "usage: snapshot.sh {save|load|list} [name]" >&2; exit 2 ;;
esac

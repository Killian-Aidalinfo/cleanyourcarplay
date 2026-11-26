#!/usr/bin/env bash
# Boot the rig headless and wait until Android is up.
source "$(dirname "$0")/lib.sh"

[ -d "$AVD_DIR" ] || { echo "No $AVD_NAME. Run tests/emu/create.sh first." >&2; exit 1; }

if adb -s "$SERIAL" get-state >/dev/null 2>&1; then
    echo "$SERIAL is already running."
    exit 0
fi

LOG="${TMPDIR:-/tmp}/$AVD_NAME-emulator.log"
echo "Booting $AVD_NAME on port $EMU_PORT (headless). Log: $LOG"
nohup "$EMULATOR" -avd "$AVD_NAME" \
    -no-window -no-audio -no-boot-anim -no-snapshot-load \
    -port "$EMU_PORT" > "$LOG" 2>&1 &

for _ in $(seq 1 120); do
    [ "$(adb -s "$SERIAL" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ] && {
        echo "Up. Point the toolkit at it with:  export BOX_HOST=$SERIAL"
        exit 0
    }
    sleep 5
done
echo "Did not boot within 10 minutes. See $LOG." >&2
exit 1

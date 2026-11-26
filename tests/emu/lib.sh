#!/usr/bin/env bash
# Shared settings for the emulator rig. Sourced, never run.

set -euo pipefail

AVD_NAME="${AVD_NAME:-cyc-a15}"
EMU_PORT="${EMU_PORT:-5560}"
SERIAL="emulator-${EMU_PORT}"
SYSTEM_IMAGE="${SYSTEM_IMAGE:-system-images/android-35/google_apis_playstore/arm64-v8a/}"
API_TARGET="${API_TARGET:-android-35}"

find_sdk() {
    for candidate in "${ANDROID_SDK_ROOT:-}" "${ANDROID_HOME:-}" \
        "$HOME/Library/Android/sdk" \
        /opt/homebrew/share/android-commandlinetools \
        /usr/local/share/android-commandlinetools \
        "$HOME/Android/Sdk"; do
        [ -n "$candidate" ] && [ -x "$candidate/emulator/emulator" ] && { echo "$candidate"; return 0; }
    done
    echo "No Android SDK with an emulator binary found." >&2
    echo "Set ANDROID_SDK_ROOT to the SDK that holds emulator/emulator." >&2
    return 1
}

SDK="$(find_sdk)"
EMULATOR="$SDK/emulator/emulator"
AVD_HOME="${ANDROID_AVD_HOME:-$HOME/.android/avd}"
AVD_DIR="$AVD_HOME/$AVD_NAME.avd"

adb_box() { adb -s "$SERIAL" "$@"; }

require_running() {
    adb -s "$SERIAL" get-state >/dev/null 2>&1 || {
        echo "$SERIAL is not running. Start it with tests/emu/start.sh." >&2
        exit 1
    }
}

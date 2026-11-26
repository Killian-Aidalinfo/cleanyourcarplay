#!/usr/bin/env bash
# The whole toolkit against the rig, in the order a real session uses it.
#
# Destructive by design: it disables packages. That is the point — this is the
# sacrificial device the real box is not. It snapshots first and restores last.
source "$(dirname "$0")/lib.sh"
require_running

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
export BOX_HOST="$SERIAL"

step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

step "snapshot: cycle-start"
adb_box emu avd snapshot save cycle-start >/dev/null

step "a real accessibility service, so the touch guard has something to guard"
# The mirroring stack of a real box is a vendor accessibility service. The rig
# has none, so we bind a stock one: the component must actually resolve, or
# AccessibilityManagerService prunes it and the setting silently stays null.
ACC=com.android.systemui.accessibility.accessibilitymenu
adb_box shell settings put secure enabled_accessibility_services \
    "$ACC/$ACC.AccessibilityMenuService" >/dev/null
adb_box shell settings put secure accessibility_enabled 1 >/dev/null
[ -n "$(adb_box shell settings get secure enabled_accessibility_services | tr -d '\r' | grep -v '^null$')" ] \
    || { echo "could not bind an accessibility service; the touch tests below would be meaningless" >&2; exit 1; }

step "probe"
python3 "$REPO/tools/box.py" --probe

step "the raw TCP client, with no adb binary on PATH"
# Box() prefers the adb binary whenever it is installed, so nothing else in
# this cycle touches the hand-rolled wire protocol. Hide adb and make it run.
TCP_PORT=$((EMU_PORT + 1))
if env PATH=/usr/bin:/bin:/usr/sbin:/sbin python3 "$REPO/tools/box.py" \
        --host "127.0.0.1:$TCP_PORT" --probe 2>&1 | head -4; then
    :
fi
echo "  (ro.adb.secure=$(adb_box shell getprop ro.adb.secure | tr -d '\r'): on a secure"
echo "   build this must refuse with instructions, never a traceback)"

step "diag (read-only)"
python3 "$REPO/tools/diag.py" | sed -n '1,12p'

step "profile — this writes the baseline the survival check compares against"
python3 "$REPO/tools/profile.py" | tail -3

step "classify"
adb_box shell pm list packages | tr -d '\r' | sed 's/^package://' | sort > "$WORK/packages.txt"
python3 "$REPO/tools/classify.py" "$WORK/packages.txt" --json > "$WORK/verdicts.json"
python3 - "$WORK/verdicts.json" <<'PY'
import json, sys
v = json.load(open(sys.argv[1]))["verdicts"]
print("  " + "  ".join("%s=%d" % (k, len(v[k])) for k in ("NEVER", "RISKY", "SAFE")))
open(sys.argv[1] + ".safe", "w").write("\n".join(v["SAFE"][:5]) + "\n")
PY

step "the guard refuses a NEVER package"
printf '%s\n%s\n' "$ACC" "com.google.android.adservices.api" > "$WORK/never.txt"
if python3 "$REPO/tools/apply.py" disable "$WORK/never.txt" --yes; then
    echo "  !! a NEVER batch exited 0 — a caller would read that as success" >&2
    FAILED=1
else
    echo "  correct: refused, non-zero exit"
fi

step "disable a SAFE batch"
python3 "$REPO/tools/apply.py" disable "$WORK/verdicts.json.safe" --yes | tail -12

step "the survival check must FAIL when the touch service disappears"
adb_box shell settings delete secure enabled_accessibility_services >/dev/null
if python3 "$REPO/tools/apply.py" check; then
    echo "  !! check passed while the accessibility service was gone — that is the bug this test exists for" >&2
    FAILED=1
else
    echo "  correct: non-zero exit, accessibility FAILED"
fi
adb_box shell settings put secure enabled_accessibility_services \
    "$ACC/$ACC.AccessibilityMenuService" >/dev/null

step "drift"
python3 "$REPO/tools/check.py" | tail -3

step "restore"
python3 "$REPO/tools/apply.py" restore | tail -8

step "back to the snapshot"
adb_box emu avd snapshot load cycle-start >/dev/null
echo "  restored."

exit "${FAILED:-0}"

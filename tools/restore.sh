#!/usr/bin/env bash
# Put everything back: re-enable every package this toolkit disabled on this
# device, and replay the saved settings.
#
#   tools/restore.sh
#
# A package you disabled by hand stays disabled — we only undo our own work.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${here}/apply.py" restore "$@"

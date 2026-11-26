#!/usr/bin/env bash
# Disable the packages in a list file. Refuses NEVER packages, no exceptions.
#
#   tools/disable.sh profiles/carlinkit-tbox-ultra-2/batch-1.txt
#
# BOX_HOST must be set, or pass --host <ip>.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${here}/apply.py" disable "$@"

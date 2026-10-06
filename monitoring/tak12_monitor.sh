#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec uv run --with google-auth --with requests --with playwright python "$SCRIPT_DIR/tak12_monitor.py"

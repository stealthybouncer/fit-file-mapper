#!/bin/bash
#
# Convenience wrapper for job monitoring
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$SCRIPT_DIR/monitor_jobs.py" "$@"

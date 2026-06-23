#!/usr/bin/env bash
# mqtt: install once, then run — auto-discovered, no registry path.
set -euo pipefail
urirun install urirun-connector-mqtt            # local dev: pip install -e .
urirun run 'device://device-01/led/command/set' --payload '{"state": "on"}' --execute --allow 'device://*'

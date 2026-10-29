#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -n "${PIPELINE_PYTHON:-}" ]; then exec "$PIPELINE_PYTHON" pipeline/ingest.py sources-check "$@"; fi
if [ -x var/venv-pipeline/bin/python ]; then exec var/venv-pipeline/bin/python pipeline/ingest.py sources-check "$@"; fi
exec python3 pipeline/ingest.py sources-check "$@"

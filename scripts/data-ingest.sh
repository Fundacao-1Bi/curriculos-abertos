#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -n "${PIPELINE_PYTHON:-}" ]; then exec "$PIPELINE_PYTHON" pipeline/ingest.py ingest "$@"; fi
if [ -x var/venv-pipeline/bin/python ]; then exec var/venv-pipeline/bin/python pipeline/ingest.py ingest "$@"; fi
exec python3 pipeline/ingest.py ingest "$@"

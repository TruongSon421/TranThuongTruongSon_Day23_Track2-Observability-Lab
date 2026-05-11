#!/bin/bash
set -euo pipefail
echo "[pyroscope-agent] Starting day23-app with Pyroscope profiling"
echo "  server:   ${PYROSCOPE_SERVER:-http://pyroscope:4040}"
echo "  app:      ${PYROSCOPE_APP_NAME:-day23-app}"
exec uvicorn main:app --host 0.0.0.0 --port 8000 --log-level warning

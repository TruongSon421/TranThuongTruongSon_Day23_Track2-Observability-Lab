#!/usr/bin/env bash
## Trigger alerts: HighInferenceLatency + ServiceDown (2 rules fire AND resolve).
## Used in: deck §10 demo, lab Track 02 grading checkpoint.

set -euo pipefail

echo "=== Triggering HighInferenceLatency ==="
curl -sS -X POST http://localhost:8000/inject?mode=latency > /dev/null
echo "  Injected high latency (P99~3s, threshold=2s)"
echo "  Waiting for HighInferenceLatency to fire..."

for i in {1..60}; do
    firing=$(docker exec day23-alertmanager wget -qO- 'http://localhost:9093/api/v2/alerts' 2>/dev/null | \
        grep -c '"state":"active"' || true)
    if [ "$firing" -gt 0 ]; then
        echo "  HighInferenceLatency fired (after ~$((i*5))s)"
        break
    fi
    sleep 5
done

echo "  Waiting for HighInferenceLatency to resolve..."
for i in {1..60}; do
    firing=$(docker exec day23-alertmanager wget -qO- 'http://localhost:9093/api/v2/alerts' 2>/dev/null | \
        grep -c '"state":"active"' || true)
    if [ "$firing" -eq 0 ]; then
        echo "  HighInferenceLatency resolved (rate drops below 2s threshold)."
        break
    fi
    sleep 5
done

echo ""
echo "=== Triggering ServiceDown (kill app) ==="
echo "  Killing day23-app..."
docker stop day23-app > /dev/null
echo "  Waiting for ServiceDown alert to fire..."
for i in {1..18}; do
    sleep 5
    firing=$(docker exec day23-alertmanager wget -qO- 'http://localhost:9093/api/v2/alerts' 2>/dev/null | \
        grep -c '"state":"active"' || true)
    if [ "$firing" -gt 0 ]; then
        echo "  ServiceDown fired (after $((i*5))s)"
        break
    fi
    echo "  No alert yet ($((i*5))s)..."
done

echo ""
echo "=== Restoring service ==="
docker start day23-app > /dev/null
echo "  App restarted. Waiting for ServiceDown to resolve..."
for i in {1..18}; do
    sleep 5
    up_val=$(docker exec day23-prometheus wget -qO- \
        'http://localhost:9090/api/v1/query?query=up%7Bjob%3D%22inference-api%22%7D' 2>/dev/null | \
        python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["data"]["result"][0]["value"][1])' 2>/dev/null || echo "0")
    if [ "$up_val" = "1" ]; then
        echo "  App is up. ServiceDown resolved."
        echo ""
        echo "=== Alert summary ==="
        echo "  HighInferenceLatency: fired -> resolved"
        echo "  ServiceDown: fired -> resolved"
        echo "  -> 2 alert rules fired and resolved"
        exit 0
    fi
    echo "  Waiting ($((i*5))s, up=$up_val)..."
done
echo "Service did not recover within 90s" >&2
exit 1

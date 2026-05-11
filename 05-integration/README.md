# 05 — Integration with Days 16-22

Day 23 is the **integrative day** for Phase 2 Track 2. This track wires the observability stack to artifacts from prior days.

## What gets monitored from where

| Source day | What | How |
|---|---|---|
| 16 cloud infra | EC2/EKS hosts | `node_exporter` scrape (configure target in `prometheus.yml`) |
| 17 data pipeline | Airflow DAG | `airflow_dag_run_duration` via `statsd_exporter` |
| 18 lakehouse | Spark / Delta | Spark UI metrics → Prometheus |
| 19 vector store | Qdrant | scrape `host.docker.internal:6333/metrics` |
| 20 model serving | llama.cpp | scrape `host.docker.internal:8080/metrics` |
| 21 (skipped) | — | not yet authored as of 2026-05 |
| 22 alignment | DPO model | push `dpo_eval_pass_rate` gauge via `monitor-day22-alignment.py` |

## Run

### Prerequisites

Ensure both stacks are running **before** starting Day 23:

```bash
# Day 19 — Qdrant vector store (port 6333)
cd /path/to/TranThuongTruongSon_Day19_Track2
docker compose up -d

# Day 20 — llama.cpp server (port 8080, must expose /metrics)
# Option A: llama-cpp-python server
python -m llama_cpp.server --model "$(jq -r .primary_model models/active.json)" \
    --host 0.0.0.0 --port 8080 --metrics

# Option B: native llama.cpp build
./llama.cpp/build/bin/llama-server -m models/... \
    --host 0.0.0.0 --port 8080 --metrics
```

### Start Day 23 stack

```bash
cd /path/to/TranThuongTruongSon_Day23_Track2-Observability-Lab
make up
make smoke
```

Prometheus (`prometheus.yml`) is pre-configured to scrape:
- Day 19 Qdrant at `host.docker.internal:6333/metrics` (job: `day19-qdrant`)
- Day 20 llama.cpp at `host.docker.internal:8080/metrics` (job: `day20-llamacpp`)

### Import dashboard

#### Option A: Provisioned (auto-imported — no manual steps)

`05-integration-dashboard.json` is provisioned via `dashboards.yml` in folder **05-integration**.
After `docker compose up`, it appears automatically in Grafana:

1. Open **http://localhost:3000** (admin / admin)
2. Dashboards → **05-integration** → **"05 — Integration: Qdrant & llama.cpp"**

#### Option B: Manual import (full-stack overview)

1. Open **http://localhost:3000** (admin / admin)
2. Dashboards → Import → paste `full-stack-dashboard.json`
3. Select Prometheus datasource → Import

Dashboard shows 6 panels. Days 19 and 20 display **real data**. Days 16, 17, 18, 22 show **No Data** (expected — those stacks are not running).

### Reload if config changes

```bash
curl -X POST http://localhost:9090/-/reload
# or: make restart
```

## Dashboards

### 05 — Integration: Qdrant & llama.cpp (recommended)

Full dashboard in folder **05-integration** with 3 sections:
- **Day 19 — Qdrant**: Collections, Vectors, Memory (resident/allocated/active), Uptime, Version
- **Day 20 — llama.cpp**: GPU Utilization, Busy Slots, Requests In-Flight, Token Throughput, Latency
- **Day 23 — FastAPI**: Request rate OK/Error, Error Rate, Latency P50/P95/P99, Token Throughput

Auto-provisioned via `dashboards.yml` — no manual import needed.

### full-stack-dashboard.json (legacy cross-day overview)

Shows one panel per source day. Designed to fail-soft — panels with no data show "No Data" rather than breaking.

## Submission checkpoint (15 pts)

- 5 pts: at least 1 prior-day source actually scraped (or stub script running)
- 5 pts: cross-day dashboard renders with all 6 panels (data or "No Data")
- 5 pts: REFLECTION.md describes which prior-day metric was hardest to expose

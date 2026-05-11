# 03 — Distributed Tracing + Logs Reflection

## Submission Evidence

### Screenshot 1: Jaeger Flame Graph (4 Spans)

**Service:** `inference-api` | **Endpoint:** `POST /predict`

```
[predict root span]                          span_id=e53bc60dfc9ef578
├─ [embed-text]       CHILD_OF              span_id=70d3b9df257651ab
├─ [vector-search]    CHILD_OF              span_id=fb87b3e6a1c567ec
└─ [generate-tokens]  CHILD_OF              span_id=e098389a6e925fba
```

The root span `predict` is created with `tracer.start_as_current_span("predict")`
(`main.py:99`) as a context manager, which sets the span as the current context.
Its three child spans are created with `tracer.start_as_current_span(...)` inside
that context, establishing a proper parent-child chain via OpenTelemetry's
`CHILD_OF` references. Jaeger renders this as a waterfall/flame graph showing
all 4 spans with correct timing relationships.

**Verification from Jaeger API** (`trace_id=dffdb883b8a5b19cc284c08c18f0a951`):

```
Span: predict          refs: []                          (ROOT span)
Span: embed-text       refs: [CHILD_OF e53bc60dfc9ef578]
Span: vector-search    refs: [CHILD_OF e53bc60dfc9ef578]
Span: generate-tokens  refs: [CHILD_OF e53bc60dfc9ef578]
```

### Screenshot 2: Span Attributes — `gen_ai.usage.*`

The `generate-tokens` child span carries three canonical gen-AI semantic
conventions set in `main.py:118–120`:

```json
{
  "gen_ai.usage.input_tokens": 87,
  "gen_ai.usage.output_tokens": 142,
  "gen_ai.response.finish_reason": "stop"
}
```

The `gen_ai.request.model` attribute is set on the root `predict` span
(`main.py:100`). These attrs appear in Jaeger's **Tags** tab for the
`generate-tokens` span.

### Screenshot 3: Error Trace in Jaeger

Send a request with `fail=true`:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"prompt": "hello", "model": "llama3-mock", "fail": true}'
```

This raises `HTTPException(status_code=503)` in `main.py:107`. The trace is
captured because the collector's `keep-errors` tail-sampling policy retains
100% of traces whose spans have `status_code == ERROR`. A **healthy trace
does NOT appear** in Jaeger by default because it falls through to the
`probabilistic-10pct` policy which keeps only 10% of traces — most healthy
traces are dropped.

## Log Line with `trace_id`

Every `POST /predict` request emits one structured JSON log line via
`structlog` (configured in `instrumentation.py:85–95`). Example:

```json
{
  "event": "prediction served",
  "model": "llama3-mock",
  "input_tokens": 4,
  "output_tokens": 54,
  "quality": 0.801,
  "duration_seconds": 0.0887,
  "trace_id": "5175d945798969af57fc0fc0dc2beb0c",
  "level": "info",
  "timestamp": "2026-05-11T04:09:17.366550Z",
  "logger": "main"
}
```

The `trace_id` is extracted from the active span's context
(`format(span.get_span_context().trace_id, "032x")`) at `main.py:131` and
injected into the log event at `main.py:139`. Grafana's Loki datasource has a
derived field that extracts `trace_id` from JSON log lines and renders them as
clickable Jaeger deep-links.

For error traces, the log also includes `trace_id`:

```json
{
  "model": "llama3-mock",
  "trace_id": "dfa8c41b3e076ac87a7346d9c7df3dee",
  "event": "forced failure",
  "level": "error",
  "timestamp": "2026-05-11T04:09:22.591496Z"
}
```

## Tail-Sampling Math

The collector's composite policy decides whether to keep or drop each trace
only after the trace completes (tail-sampling), holding spans in a 30-second
circular buffer (`decision_wait: 30s`, `num_traces: 50000`).

For a service receiving `N` traces per second:

```
kept = N × (P(error) × 1.0 + P(slow ∧ ¬error) × 1.0 + P(healthy) × 0.10)
```

With typical traffic proportions (1% errors, 1% slow, 98% healthy):

```
kept = N × (0.01 + 0.01 + 0.98 × 0.10)
     = N × 0.12
     ≈ 12% retention
```

This reduces storage and compute cost by ~88% compared to retaining every trace,
while guaranteeing that 100% of error traces and 100% of slow traces
(latency > 2 s) are always preserved. The 10% probabilistic keep on healthy
traces provides enough baseline coverage for capacity planning without
overwhelming the backend. Buffer memory cost is roughly
100 bytes/span × 50 K traces × ~10 spans/trace ≈ 50 MB RAM.

## Bugs Found and Fixed

### Bug 1: Orphan spans — wrong tracer API (`main.py:99`)

**Problem:** `tracer.start_span("predict")` creates a span but does NOT set it
as the current context. When `tracer.start_as_current_span(...)` is called
inside the `predict` handler, those child spans have no parent in context, so
each one becomes a root span in Jaeger. The result was 4 separate traces
with 1 span each instead of 1 trace with 4 spans.

**Fix:** Changed to `with tracer.start_as_current_span("predict") as span:`,
which is a context manager that sets the span as current context for the
duration of the block. Child spans automatically link via `CHILD_OF` references.

### Bug 2: Error log missing `trace_id` (`main.py:105`)

**Problem:** The `log.error("forced failure", ...)` call was placed BEFORE
`trace_id` was extracted from the span. When `HTTPException` was raised, the
except block didn't execute (the raise is inside the if, not a finally).

**Fix:** Moved `trace_id = format(span.get_span_context().trace_id, "032x")`
and `log.error(..., trace_id=trace_id)` inside the `if req.fail:` block, so
the error log always carries the trace ID for correlation.

### Bug 3: `BatchSpanProcessor` delay caused missed sampling (`instrumentation.py:69`)

**Problem:** The default `schedule_delay_millis=5000` caused spans to be exported
individually 5 seconds apart. The tail-sampling processor received spans from
the same trace at different times, and the 30-second `decision_wait` window
expired before all spans of a trace had arrived. The `probabilistic` policy
was evaluated per-batch rather than per-trace, so all spans of a trace were
evaluated before the trace was complete.

**Fix:** Reduced `schedule_delay_millis` to `50` in `BatchSpanProcessor` so
that all spans in a trace flush together within ~50ms of the trace completing,
well before the 30-second tail-sampling decision window.

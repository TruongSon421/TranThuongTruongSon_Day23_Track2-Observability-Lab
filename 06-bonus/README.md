# Bonus — 20 pts additive

This folder contains two optional bonus tasks that go beyond the core observability stack.

## B1 — eBPF profiling (10 pts)

Profile the `day23-app` Python process with Pyroscope using eBPF (or `process` fallback on non-Linux).

- **Pyroscope server** runs at `http://localhost:4040`
- The app is auto-instrumented via the `pyroscope` Python package
- Flame graphs appear automatically as traffic hits the app

**How to verify:** open `http://localhost:4040`, run `make load`, and observe a flame graph for `day23-app`.

## B2 — LLM-native observability (10 pts)

Self-host Langfuse to capture a real LangChain LLM trace, demonstrating the 4th pillar of GenAI observability.

- **Langfuse web UI** at `http://localhost:3001`
- Default credentials: `flask@langfuse.com` / `langfuse@123`
- `langfuse_chain.py` wraps the existing mock inference in a LangChain `LLMChain` with `@observe` decorator
- `run_traces.py` emits traces directly via the Langfuse ingestion API

**Setup:**
1. Run: `make langfuse-up`
2. Wait ~20s for Langfuse to initialize
3. Run: `make langfuse-trace`

**How to verify:** open `http://localhost:3001`, login with `flask@langfuse.com` / `langfuse@123`, navigate to Dataset > langfuse-trace-demo and see traces appear.

---

| Bonus | Tool | URL | Run |
|-------|------|-----|-----|
| B1 | Pyroscope | http://localhost:4040 | `make pyroscope-up` |
| B2 | Langfuse | http://localhost:3001 | `make langfuse-up` then `make langfuse-trace` |

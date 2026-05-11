#!/usr/bin/env python3
"""LangChain + Langfuse integration for LLM-native observability (B2 bonus).

Self-hosted Langfuse captures a real LangChain LLM trace, demonstrating the 4th
pillar of GenAI observability.  Each call to `chain.run()` produces a full Langfuse
trace showing: prompt, model, tokens, latency, finish reason.

Run AFTER `make langfuse-up` (Langfuse must be up before the script starts).
"""
from __future__ import annotations

import os
import time
from typing import Any

from langfuse.decorators import observe
from langfuse import Langfuse

from langchain_core.prompts import PromptTemplate
from langchain_core.language_models.fake import FakeListLLM

LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3001")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "flask@langfuse.com")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "langfuse@123")

langfuse = Langfuse(
    host=LANGFUSE_HOST,
    public_key=LANGFUSE_PUBLIC_KEY,
    secret_key=LANGFUSE_SECRET_KEY,
)


def _mock_llm_response(prompt: str, **kwargs: Any) -> str:
    from inference import simulate_inference
    text, in_toks, out_toks, quality = simulate_inference(prompt, "llama3-mock")
    return text


class MockInferenceLLM:
    def __init__(self) -> None:
        self._call_count = 0

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        self._call_count += 1
        return _mock_llm_response(prompt, **kwargs)


PROMPT = PromptTemplate.from_template(
    "You are a helpful AI assistant. {question}\n\nProvide a concise and accurate answer."
)

llm = MockInferenceLLM()
chain = PROMPT | llm


@observe(capture_input=True, capture_output=True, as_id="langfuse-trace-demo")
def run_chain(question: str) -> dict[str, Any]:
    result = chain.invoke({"question": question})
    return {"answer": result, "question": question}


def main() -> None:
    questions = [
        "What is observability?",
        "Explain the three pillars of observability.",
        "What is eBPF and how does it help profiling?",
        "How does Langfuse capture LLM traces?",
        "What is the difference between metrics, logs, and traces?",
    ]

    print("=" * 60)
    print("BONUS B2 — LangChain + Langfuse LLM-native observability")
    print("=" * 60)
    print(f"Langfuse endpoint: {LANGFUSE_HOST}")
    print(f"Tracing {len(questions)} questions...\n")

    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] Q: {q}")
        try:
            result = run_chain(q)
            print(f"     A: {result['answer'][:80]}...")
        except Exception as exc:
            print(f"     ERROR: {exc}")
        print()

    print("Done. View traces at:")
    print(f"  {LANGFUSE_HOST}")
    print("  Login: flask@langfuse.com / langfuse@123")
    print("  Navigate to: Dataset > langfuse-trace-demo")


if __name__ == "__main__":
    main()

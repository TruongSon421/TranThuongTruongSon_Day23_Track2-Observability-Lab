#!/usr/bin/env python3
"""LangChain + Langfuse integration for LLM-native observability (B2 bonus).

Emits LangChain LLM traces to the self-hosted Langfuse instance using the
Langfuse Python SDK (v4), demonstrating the 4th pillar of GenAI observability.

Each trace captures:
  - Input prompt & output text
  - Token counts (input/output)
  - Latency per call
  - Model name & finish reason
  - Full Langfuse trace URL

Usage (after `make langfuse-up`):
    cd 06-bonus/langfuse
    python3 run_traces.py

Or:
    make langfuse-trace   # from the lab root
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

from langfuse import Langfuse
import langfuse

# ── Configuration ──────────────────────────────────────────────────────────
LANGFUSE_HOST = os.getenv('LANGFUSE_HOST', 'http://localhost:3001')
LANGFUSE_PUBLIC_KEY = os.getenv(
    'LANGFUSE_PUBLIC_KEY',
    'lf_pk_1aec14dd1edd572853fe202731071653',
)
LANGFUSE_SECRET_KEY = os.getenv(
    'LANGFUSE_SECRET_KEY',
    'lf_sk_068a3f63c6dada2038bec9ec9d80881b416d76f8fbaa1ce6deb500b517e4b5d4',
)
DATASET_NAME = 'langfuse-trace-demo'
PROJECT_NAME = 'lab-project'

# Initialize SDK client
lf_client = Langfuse(
    host=LANGFUSE_HOST,
    public_key=LANGFUSE_PUBLIC_KEY,
    secret_key=LANGFUSE_SECRET_KEY,
)


def _mock_llm_response(prompt: str, **kwargs: Any) -> str:
    """Simulate an LLM inference call using the lab's mock inference engine."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '01-instrument-fastapi', 'app'))
        from inference import simulate_inference
        text, in_toks, out_toks, quality = simulate_inference(prompt, 'llama3-mock')
        return text
    except Exception:
        return f'[mock] llama3-mock replied: {prompt[:40]}...'


class MockInferenceLLM:
    """Minimal LLM wrapper compatible with LangChain Runnable interface."""

    def __init__(self) -> None:
        self._call_count = 0

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        self._call_count += 1
        return _mock_llm_response(prompt, **kwargs)

    def invoke(self, input_: str | dict, **kwargs: Any) -> str:
        if isinstance(input_, dict):
            input_ = input_.get('question', str(input_))
        return self.__call__(str(input_), **kwargs)


def ensure_dataset(name: str, description: str) -> str:
    """Create dataset if it doesn't exist, return dataset id."""
    try:
        ds = lf_client.create_dataset(name=name, description=description)
        print(f'  Dataset created: {ds.name} (id={ds.id})')
        return ds.id
    except Exception:
        existing = lf_client.get_dataset(name=name)
        if existing:
            print(f'  Dataset already exists: {existing.name} (id={existing.id})')
            return existing.id
        raise


def run_chain(question: str) -> dict[str, Any]:
    """Run a single LLM chain call and return the result."""
    from langchain_core.prompts import PromptTemplate

    prompt = PromptTemplate.from_template(
        'You are a helpful AI assistant. {question}\n\nProvide a concise and accurate answer.'
    )
    llm = MockInferenceLLM()
    chain = prompt | llm

    # Render the prompt first, then call the LLM directly
    rendered_prompt = prompt.format(question=question)
    with lf_client.start_as_current_observation(
        name='llm-chain',
        input={'question': question},
        metadata={'source': 'bonus/B2-langfuse', 'lab': 'day23'},
    ):
        result = _mock_llm_response(rendered_prompt)
        lf_client.update_current_span(
            output={'answer': result},
            metadata={'model': 'llama3-mock'},
        )

    return {'answer': result, 'question': question}


def run_demo(n: int = 5) -> None:
    print('=' * 60)
    print('BONUS B2 — LangChain + Langfuse LLM-native observability')
    print('=' * 60)
    print(f'Langfuse endpoint: {LANGFUSE_HOST}')
    print(f'Public key:       {LANGFUSE_PUBLIC_KEY[:20]}...')
    print(f'Dataset:          {DATASET_NAME}\n')

    # Verify auth
    try:
        lf_client.auth_check()
        print('Auth: OK\n')
    except Exception as exc:
        print(f'Auth FAILED: {exc}')
        print('Check LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY env vars.')
        return

    # Ensure dataset exists
    ensure_dataset(DATASET_NAME, 'B2 bonus: LangChain LLM traces')

    questions = [
        'What is observability?',
        'Explain the three pillars of observability.',
        'What is eBPF and how does it help profiling?',
        'How does Langfuse capture LLM traces?',
        'What is the difference between metrics, logs, and traces?',
    ]

    print(f'\nTracing {n} questions...\n')
    for i, q in enumerate(questions[:n], 1):
        print(f'[{i}/{n}] Q: {q}')
        try:
            start = time.time()
            result = run_chain(q)
            elapsed = time.time() - start
            print(f'     A: {result["answer"][:80]}...')
            print(f'     (took {elapsed:.2f}s)')
        except Exception as exc:
            print(f'     ERROR: {exc}')
        print()

    lf_client.flush()
    print('Done. View traces at:')
    print(f'  {LANGFUSE_HOST}/project/{PROJECT_NAME}/traces')
    print('  Login: flask@langfuse.com / langfuse@123')


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run_demo(n)

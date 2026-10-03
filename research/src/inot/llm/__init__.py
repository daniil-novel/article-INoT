"""LLM clients used by the architectures.

Two implementations:
* ``OpenRouterClient`` — real LLM via https://openrouter.ai/api/v1
* ``DryRunClient``   — deterministic stand-in (no network) used by
  ``--dry-run`` so that the experiment plumbing can be smoke-tested
  without spending real tokens. Only ``OpenRouterClient`` is used in
  results reported by the article-validation suite.

Token accounting uses the provider-reported ``usage`` block when present,
falling back to ``tiktoken`` cl100k_base counts. Cost is computed from
``config.yaml`` ``llm.prices_usd_per_mtok``.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx
import tiktoken
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    RetryError,
)

from ..config import Config
from ..types import TokenUsage

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token counting helper
# ---------------------------------------------------------------------------
_ENC = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """cl100k_base token count — approximation that matches OpenAI/Anthropic
    well enough for budget planning and for fallback when the API does not
    return ``usage``."""
    if not text:
        return 0
    return len(_ENC.encode(text, disallowed_special=()))


def messages_token_count(messages: list[dict[str, str]]) -> int:
    # Mirrors OpenAI's per-message overhead heuristic (~4 tokens).
    return sum(count_tokens(m.get("content", "")) + 4 for m in messages) + 2


# ---------------------------------------------------------------------------
# Result of one chat completion
# ---------------------------------------------------------------------------
@dataclass
class ChatResult:
    text: str
    usage: TokenUsage


class BudgetExceeded(RuntimeError):
    """Raised when cumulative cost exceeds ``llm.hard_budget_usd``."""


# ---------------------------------------------------------------------------
# Real OpenRouter client
# ---------------------------------------------------------------------------
class OpenRouterClient:
    def __init__(self, config: Config):
        self.cfg = config
        self.base_url = config.get("llm.base_url", "https://openrouter.ai/api/v1").rstrip("/")
        self.api_key = config.api_key()
        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is empty. Copy .env.example to .env and fill it in, "
                "or export OPENROUTER_API_KEY in your shell."
            )
        self.timeout = float(config.get("llm.request_timeout_seconds", 120))
        self.max_retries = int(config.get("llm.max_retries", 4))
        self.default_temperature = float(config.get("llm.temperature", 0.2))
        self.budget_usd = float(config.get("llm.hard_budget_usd", 10.0))
        self.spent_usd: float = 0.0
        self._client = httpx.Client(timeout=self.timeout)

    # ----- main entry point -------------------------------------------------
    def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        *,
        role: str = "unspecified",
        architecture: str = "",
        iteration: int = 0,
        seed: Optional[int] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 1024,
    ) -> ChatResult:
        """Single chat completion. Raises ``BudgetExceeded`` if the running
        total would exceed the configured hard cap."""
        if self.spent_usd >= self.budget_usd:
            raise BudgetExceeded(
                f"Cumulative spend ${self.spent_usd:.4f} >= hard cap ${self.budget_usd:.2f}"
            )
        estimated_cost = self._estimate_request_cost(messages, model, max_tokens=max_tokens)
        if self.spent_usd + estimated_cost > self.budget_usd:
            raise BudgetExceeded(
                "Estimated request would exceed hard cap: "
                f"${self.spent_usd:.4f} spent + ${estimated_cost:.4f} estimated "
                f"> ${self.budget_usd:.2f}"
            )

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": self.default_temperature if temperature is None else temperature,
            "max_tokens": max_tokens,
            "usage": {"include": True},
        }
        if seed is not None:
            body["seed"] = int(seed)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.environ.get("OPENROUTER_HTTP_REFERER", "https://github.com/local"),
            "X-Title": os.environ.get("OPENROUTER_X_TITLE", "hybrid-inot-research"),
        }

        attempt_iter = Retrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=20),
            retry=retry_if_exception_type((httpx.HTTPError, httpx.ReadTimeout, _RetryableStatus)),
            reraise=True,
        )

        t0 = time.perf_counter()
        try:
            for attempt in attempt_iter:
                with attempt:
                    r = self._client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        content=json.dumps(body),
                    )
                    if r.status_code in (429, 500, 502, 503, 504):
                        raise _RetryableStatus(f"status={r.status_code} body={r.text[:200]}")
                    if r.status_code >= 400:
                        raise httpx.HTTPStatusError(
                            f"{r.status_code}: {r.text[:500]}", request=r.request, response=r
                        )
                    payload = r.json()
        except RetryError as e:  # pragma: no cover - network paths
            raise RuntimeError(f"OpenRouter call failed after {self.max_retries} attempts: {e}") from e

        latency = time.perf_counter() - t0

        # Extract content
        try:
            text = payload["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected OpenRouter response shape: {payload}") from e

        # Token + cost accounting
        usage_block = payload.get("usage") or {}
        in_tok = int(usage_block.get("prompt_tokens") or messages_token_count(messages))
        out_tok = int(usage_block.get("completion_tokens") or count_tokens(text))
        price = self.cfg.price(model)
        cost = (in_tok / 1_000_000.0) * price.get("input", 0.0) + (
            out_tok / 1_000_000.0
        ) * price.get("output", 0.0)
        cost_rub = cost * self.cfg.usd_to_rub()
        self.spent_usd += cost

        return ChatResult(
            text=text,
            usage=TokenUsage(
                model=model,
                input_tokens=in_tok,
                output_tokens=out_tok,
                cost_usd=cost,
                cost_rub=cost_rub,
                role=role,
                architecture=architecture,
                iteration=iteration,
                latency_seconds=latency,
            ),
        )

    def close(self) -> None:
        self._client.close()

    def _estimate_request_cost(
        self,
        messages: list[dict[str, str]],
        model: str,
        *,
        max_tokens: int,
    ) -> float:
        """Upper-bound one call before the HTTP request is sent.

        The post-response accounting below remains authoritative, but this
        preflight guard prevents a single large completion from knowingly
        crossing the experiment's hard budget cap.
        """
        price = self.cfg.price(model)
        in_tok = messages_token_count(messages)
        return (in_tok / 1_000_000.0) * price.get("input", 0.0) + (
            max_tokens / 1_000_000.0
        ) * price.get("output", 0.0)


class _RetryableStatus(Exception):
    """Marker exception for retryable HTTP status codes (429/5xx)."""


# ---------------------------------------------------------------------------
# Deterministic mock client used for smoke tests / dry-runs only
# ---------------------------------------------------------------------------
class DryRunClient:
    """No-network stub. Returns a hash-determined stub answer.

    NOT used for any reported metric — only for `pytest` and `--dry-run`.
    """
    def __init__(self, config: Config):
        self.cfg = config
        self.spent_usd = 0.0
        self.budget_usd = float(config.get("llm.hard_budget_usd", 10.0))

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        *,
        role: str = "unspecified",
        architecture: str = "",
        iteration: int = 0,
        seed: Optional[int] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 1024,
    ) -> ChatResult:
        h = hashlib.sha256(
            (model + role + architecture + str(seed) + json.dumps(messages, sort_keys=True)).encode()
        ).hexdigest()
        # Deterministic pseudo-random "answer length"
        rng = random.Random(int(h[:8], 16))
        text = "def solution(*args, **kwargs):\n    return 0  # dry-run stub\n"
        in_tok = messages_token_count(messages)
        out_tok = count_tokens(text) + rng.randint(10, 80)
        price = self.cfg.price(model)
        cost = (in_tok / 1_000_000.0) * price.get("input", 0.0) + (
            out_tok / 1_000_000.0
        ) * price.get("output", 0.0)
        cost_rub = cost * self.cfg.usd_to_rub()
        self.spent_usd += cost
        return ChatResult(
            text=text,
            usage=TokenUsage(
                model=model,
                input_tokens=in_tok,
                output_tokens=out_tok,
                cost_usd=cost,
                cost_rub=cost_rub,
                role=role,
                architecture=architecture,
                iteration=iteration,
                latency_seconds=0.001,
            ),
        )

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def make_client(config: Config, *, dry_run: bool = False):
    return DryRunClient(config) if dry_run else OpenRouterClient(config)

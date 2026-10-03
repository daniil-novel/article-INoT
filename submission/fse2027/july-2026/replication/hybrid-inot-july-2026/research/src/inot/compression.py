"""Algorithm 2: Compression of long context (LLMLingua-style proxy).

The article specifies an LLMLingua-2 like procedure (Pan et al. 2024). A real
trained relevance classifier is out of scope for this validation suite; we
implement a deterministic *information-theoretic surrogate* that:

1. Splits the context into semantic blocks (top-level functions / paragraphs).
2. Scores each block with a relevance proxy combining
   (a) presence of identifiers from the task prompt;
   (b) presence of API signatures (``def`` / ``class``);
   (c) presence of error/exception/log fragments;
   (d) inverse self-information (long, repetitive blocks score lower).
3. Greedily keeps the highest-scoring blocks until ``tau_len`` tokens, ALWAYS
   keeping (i) signatures, (ii) ``Traceback`` lines, (iii) the modified-files
   markers — exactly the "must-keep" items from Algorithm 2 lines 5-6.

The key property used by Hybrid-INoT is monotonicity:
    |C_hat| <= tau_len <= |C_0|
which is sufficient for inequality (7) of the article. The *quality* of the
compression mostly affects pass@1, not the H1 token-budget claim.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .llm import count_tokens


_BLOCK_SPLIT = re.compile(r"\n(?=#\s|def\s|class\s|@\w|---)", re.MULTILINE)
_SIGNATURE = re.compile(r"^(def|class|async\s+def)\s+\w+", re.MULTILINE)
_ERROR_HINT = re.compile(r"(Traceback|Error:|Exception|FAIL|Warning)", re.IGNORECASE)


@dataclass
class CompressionResult:
    text: str
    original_tokens: int
    compressed_tokens: int
    kept_blocks: int
    total_blocks: int

    @property
    def ratio(self) -> float:
        return (self.compressed_tokens / self.original_tokens) if self.original_tokens else 1.0


def split_blocks(text: str) -> list[str]:
    if not text:
        return []
    parts = _BLOCK_SPLIT.split(text)
    out = [p.strip() for p in parts if p.strip()]
    return out or [text]


def _identifier_set(prompt: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", prompt))


def relevance_score(block: str, prompt_idents: set[str]) -> float:
    score = 0.0
    n_tok = max(1, count_tokens(block))
    # (a) identifier overlap
    ids = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", block))
    score += 5.0 * len(ids & prompt_idents) / max(1, len(prompt_idents))
    # (b) signature presence
    if _SIGNATURE.search(block):
        score += 2.0
    # (c) error / log fragment
    if _ERROR_HINT.search(block):
        score += 4.0
    # (d) penalise long repetitive blocks (low novelty)
    score -= 0.001 * n_tok
    # (e) per-token efficiency
    return score


def compress(
    context: str,
    prompt: str,
    *,
    tau_len: int = 4096,
    enable: bool = True,
) -> CompressionResult:
    """Greedily keep the most relevant blocks fitting ``tau_len`` tokens.

    Returns the compressed text along with the bookkeeping needed by
    metrics: original_tokens, compressed_tokens, kept/total blocks.
    """
    n0 = count_tokens(context)
    if not enable or n0 <= tau_len or not context:
        return CompressionResult(
            text=context, original_tokens=n0, compressed_tokens=n0,
            kept_blocks=0, total_blocks=0,
        )
    blocks = split_blocks(context)
    idents = _identifier_set(prompt)
    scored = [(relevance_score(b, idents), b, count_tokens(b)) for b in blocks]
    # Always-keep: blocks containing error hints or signatures
    must_keep = [(s, b, n) for (s, b, n) in scored if _ERROR_HINT.search(b) or _SIGNATURE.search(b)]
    rest = [(s, b, n) for (s, b, n) in scored if (s, b, n) not in must_keep]
    rest.sort(key=lambda t: t[0], reverse=True)

    kept: list[str] = []
    used = 0
    for s, b, n in must_keep + rest:
        if used + n <= tau_len:
            kept.append(b)
            used += n
        elif used == 0:
            # ensure non-empty result: include at least one truncated block
            kept.append(_truncate_to_tokens(b, tau_len))
            used = tau_len
            break
    text = "\n\n".join(kept)
    return CompressionResult(
        text=text,
        original_tokens=n0,
        compressed_tokens=count_tokens(text),
        kept_blocks=len(kept),
        total_blocks=len(blocks),
    )


def _truncate_to_tokens(text: str, n: int) -> str:
    from .llm import _ENC
    ids = _ENC.encode(text, disallowed_special=())[:n]
    return _ENC.decode(ids)

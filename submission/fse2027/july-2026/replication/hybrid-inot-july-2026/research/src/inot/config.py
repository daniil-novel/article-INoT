"""YAML config loader with dotted-path overrides.

Reads ``config.yaml`` and exposes a single ``Config`` object used everywhere.
``.env`` is loaded if present so that ``OPENROUTER_API_KEY`` becomes available
without exporting it manually.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def _load_dotenv(path: Path, *, override: bool = True) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and (override or k not in os.environ):
            os.environ[k] = v


@dataclass
class Config:
    raw: dict[str, Any]

    # ---- convenience accessors ------------------------------------------------
    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self.raw
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    @property
    def large_model(self) -> str:
        return self.get("llm.large_model")

    @property
    def small_model(self) -> str:
        return self.get("llm.small_model")

    def price(self, model: str) -> dict[str, float]:
        prices = self.get("llm.prices_usd_per_mtok", {}) or {}
        return prices.get(model, {"input": 0.0, "output": 0.0})

    def usd_to_rub(self) -> float:
        return float(self.get("accounting.usd_to_rub", 100.0))

    def api_key(self) -> str:
        env_var = self.get("llm.api_key_env", "OPENROUTER_API_KEY")
        return os.environ.get(env_var, "")


_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path | None = None) -> Config:
    """Load ``config.yaml`` (or override path), apply ``.env``, return Config."""
    # Для воспроизводимых локальных экспериментов файл проекта `.env` должен
    # иметь приоритет над случайно выставленной системной переменной.
    _load_dotenv(_PROJECT_ROOT / ".env", override=True)
    cfg_path = Path(path) if path else (_PROJECT_ROOT / "config.yaml")
    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return Config(raw=data)


def project_root() -> Path:
    return _PROJECT_ROOT

"""Configuration models for httpdiff."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiffConfig:
    """Top-level configuration parsed from CLI args or config file."""

    # HTTP request settings
    base_url: str
    target_url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    timeout: float = 30.0

    # Diff settings
    ignore: list[str] = field(default_factory=list)

    # Output settings
    format: str = "terminal"  # "terminal" | "html" | "json"
    output: str | None = None


def parse_config_file(path: str) -> dict:
    """Load a JSON config file and return a dict compatible with ``DiffConfig``."""
    import json

    with open(path) as f:
        return json.load(f)

"""Recursive JSON diff engine."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiffEntry:
    """A single difference between two JSON values."""

    path: str
    kind: str  # "added" | "removed" | "changed" | "type_changed"
    old_value: Any = None
    new_value: Any = None


def _canonical_path(segments: list[str | int]) -> str:
    """Build a readable path like ``users[0].name``."""
    parts: list[str] = []
    for s in segments:
        if isinstance(s, int):
            parts.append(f"[{s}]")
        else:
            if parts:
                parts.append(".")
            parts.append(s)
    return "".join(parts)


def _matches_ignore(path: str, patterns: list[str]) -> bool:
    """Check whether *path* matches any ignore pattern.

    Patterns use simple matching:
    - ``timestamp``          → match any field named ``timestamp`` (any level)
    - ``meta.version``       → match exact dotted path (relative to root)
    - ``*.updated_at``       → match ``updated_at`` at any nesting level
    - ``items.*.id``         → match ``id`` nested inside any array element of ``items``
    """
    # Strip the virtual "root." prefix for pattern matching
    if path.startswith("root."):
        path = path.removeprefix("root.")
    elif path == "root":
        path = ""

    array_wildcard_path = re.sub(r"\[\d+\]", ".*", path)

    for pat in patterns:
        # Handle *. prefix pattern (matches field at any nesting level)
        if pat.startswith("*."):
            field = pat[2:]  # e.g. "*.updated_at" → "updated_at"
            if path == field or path.endswith("." + field):
                return True
        elif "." in pat:
            if fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(array_wildcard_path, pat):
                return True
        else:
            # Single field name — check the last path component
            last = path.rpartition(".")[-1].split("[")[0] if path else ""
            if fnmatch.fnmatch(last, pat):
                return True
    return False


def _diff(
    old: Any,
    new: Any,
    segments: list[str | int],
    results: list[DiffEntry],
    ignore: list[str],
) -> None:
    path = _canonical_path(segments)

    # Type mismatch → record and stop descending
    # (None vs non-None is treated as value change, not type change)
    if type(old) is not type(new) and not (
        isinstance(old, dict) and isinstance(new, dict)
    ):
        if old is None or new is None:
            # Treat as value change instead of type change
            results.append(DiffEntry(path, "changed", old, new))
        else:
            results.append(
                DiffEntry(path, "type_changed", type(old).__name__, type(new).__name__)
            )
        return

    # Both dicts
    if isinstance(old, dict) and isinstance(new, dict):
        all_keys = set(old) | set(new)
        for key in sorted(all_keys, key=str):
            if key in old and key not in new:
                p = _canonical_path(segments + [str(key)])
                if not _matches_ignore(p, ignore):
                    results.append(DiffEntry(p, "removed", old[key], None))
            elif key not in old and key in new:
                p = _canonical_path(segments + [str(key)])
                if not _matches_ignore(p, ignore):
                    results.append(DiffEntry(p, "added", None, new[key]))
            else:
                _diff(old[key], new[key], segments + [str(key)], results, ignore)
        return

    # Both lists
    if isinstance(old, list) and isinstance(new, list):
        max_len = max(len(old), len(new))
        for i in range(max_len):
            p = _canonical_path(segments + [i])
            if _matches_ignore(p, ignore):
                continue
            if i >= len(old):
                results.append(DiffEntry(p, "added", None, new[i]))
            elif i >= len(new):
                results.append(DiffEntry(p, "removed", old[i], None))
            else:
                _diff(old[i], new[i], segments + [i], results, ignore)
        return

    # Both scalars
    if old != new:
        if not _matches_ignore(path, ignore):
            results.append(DiffEntry(path, "changed", old, new))


def diff(
    old: Any,
    new: Any,
    ignore: list[str] | None = None,
) -> list[DiffEntry]:
    """Compare two JSON-decoded values and return a list of differences."""
    results: list[DiffEntry] = []
    _diff(old, new, ["root"], results, ignore or [])
    return results


def apply_filter(
    entries: list[DiffEntry],
    kind: str | None = None,
    path_include: list[str] | None = None,
) -> list[DiffEntry]:
    """Filter diff entries by kind (added/removed/changed/type_changed)
    or by path patterns."""
    result = entries
    if kind:
        result = [e for e in result if e.kind == kind]
    if path_include:
        result = [e for e in result if any(fnmatch.fnmatch(e.path, p) for p in path_include)]
    return result

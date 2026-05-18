"""Output formatting for httpdiff."""

from __future__ import annotations

import json
import pprint
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table
from rich import box

from httpdiff.differ import DiffEntry


class Reporter:
    """Formats diff results for terminal, HTML, or JSON output."""

    def __init__(
        self,
        base_url: str,
        target_url: str,
        base_status: int,
        target_status: int,
        entries: list[DiffEntry],
    ):
        self.base_url = base_url
        self.target_url = target_url
        self.base_status = base_status
        self.target_status = target_status
        self.entries = entries

    def render(self, fmt: str = "terminal") -> str:
        if fmt == "terminal":
            return self._terminal()
        elif fmt == "html":
            return self._html()
        elif fmt == "json":
            return self._json()
        else:
            raise ValueError(f"Unknown format: {fmt}")

    def _counts(self) -> dict[str, int]:
        counts: dict[str, int] = {"added": 0, "removed": 0, "changed": 0, "type_changed": 0}
        for e in self.entries:
            counts[e.kind] += 1
        return counts

    # ------------------------------------------------------------------
    # Terminal (rich)
    # ------------------------------------------------------------------
    def _terminal(self) -> str:
        console = Console(width=100, force_terminal=True, color_system="truecolor")
        lines: list[str] = []

        # Capture output from a fresh console each time
        import io
        buf = io.StringIO()
        c = Console(file=buf, width=100, force_terminal=True, color_system="truecolor")

        c.print(f"[bold]httpdiff[/bold]  {self.base_url}  vs  {self.target_url}")
        c.print()

        counts = self._counts()
        total = sum(counts.values())
        if total == 0:
            c.print("[green]✓[/green] No differences found")
            c.print()
            return buf.getvalue()

        c.print(f"Found [bold]{total}[/bold] difference(s):")
        c.print()

        table = Table(box=box.SIMPLE, header_style="bold")
        table.add_column("Type", width=14)
        table.add_column("Path")
        table.add_column("Difference")

        for e in self.entries:
            type_str = {
                "added": "[green]added[/green]",
                "removed": "[red]removed[/red]",
                "changed": "[yellow]changed[/yellow]",
                "type_changed": "[magenta]type[/magenta]",
            }.get(e.kind, e.kind)

            if e.kind == "added":
                diff_str = f"[green]{_fmt_value(e.new_value)}[/green]"
            elif e.kind == "removed":
                diff_str = f"[red]{_fmt_value(e.old_value)}[/red]"
            elif e.kind == "changed":
                diff_str = (
                    f"[red]{_fmt_value(e.old_value)}[/red]  →  "
                    f"[green]{_fmt_value(e.new_value)}[/green]"
                )
            else:
                diff_str = f"{e.old_value}  →  {e.new_value}"

            table.add_row(type_str, e.path, diff_str)

        c.print(table)
        c.print()

        return buf.getvalue()

    # ------------------------------------------------------------------
    # HTML (Jinja2)
    # ------------------------------------------------------------------
    def _html(self) -> str:
        from jinja2 import Environment, FileSystemLoader

        template_dir = Path(__file__).parent / "templates"
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        env.filters["pprint"] = _pprint
        template = env.get_template("report.html")

        return template.render(
            base_url=self.base_url,
            target_url=self.target_url,
            base_status=self.base_status,
            target_status=self.target_status,
            entries=self.entries,
            counts=self._counts(),
        )

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------
    def _json(self) -> str:
        data = {
            "summary": {
                "base_url": self.base_url,
                "target_url": self.target_url,
                "base_status": self.base_status,
                "target_status": self.target_status,
                "total": len(self.entries),
                "counts": self._counts(),
            },
            "diffs": [
                {
                    "path": e.path,
                    "kind": e.kind,
                    "old_value": _json_safe(e.old_value),
                    "new_value": _json_safe(e.new_value),
                }
                for e in self.entries
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _fmt_value(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (int, float)):
        return str(v)
    s = pprint.pformat(v, width=50)
    if len(s) > 60:
        s = s[:57] + "..."
    return s


def _json_safe(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)):
        return v
    if v is None:
        return None
    try:
        json.dumps(v)
        return v
    except (TypeError, ValueError):
        return str(v)


def _pprint(v: Any) -> str:
    return pprint.pformat(v, width=60)

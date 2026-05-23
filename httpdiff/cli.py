"""CLI entry point for httpdiff."""

from __future__ import annotations

import argparse
import json
import sys

from httpdiff.config import DiffConfig, parse_config_file
from httpdiff.differ import diff
from httpdiff.reporter import Reporter
from httpdiff.runner import RequestConfig, RequestError, execute


def _split_ignore_patterns(patterns: list[str]) -> list[str]:
    """Split repeated/comma-separated ignore patterns from CLI args."""
    result: list[str] = []
    for pattern in patterns:
        result.extend(part.strip() for part in pattern.split(",") if part.strip())
    return result


def _parse_args(argv: list[str] | None = None) -> DiffConfig:
    parser = argparse.ArgumentParser(
        prog="httpdiff",
        description="Compare HTTP API responses between two environments.",
    )

    # Config file (if provided, all other args are ignored)
    parser.add_argument("--config", "-c", help="Path to JSON config file")

    # URL arguments
    parser.add_argument("--base", "-b", required=False, help="Baseline URL")
    parser.add_argument("--target", "-t", required=False, help="Target URL")
    parser.add_argument("--method", "-m", default="GET", help="HTTP method (default: GET)")
    parser.add_argument(
        "--header", "-H", action="append", default=[], help="Custom header (can be repeated)"
    )
    parser.add_argument("--body", "-d", help="Request body as JSON string")

    # Diff options
    parser.add_argument(
        "--ignore", "-i", action="append", default=[], help="Field(s) to ignore (can be repeated)"
    )

    # Output options
    parser.add_argument(
        "--format", "-f", choices=["terminal", "html", "json"], default="terminal"
    )
    parser.add_argument("--output", "-o", help="Output file path (for html/json format)")

    parsed = parser.parse_args(argv)

    # Config file mode
    if parsed.config:
        raw = parse_config_file(parsed.config)
        return DiffConfig(**raw)

    # Validate required args
    if not parsed.base:
        parser.error("--base is required (or use --config)")
    if not parsed.target:
        parser.error("--target is required (or use --config)")

    # Parse headers
    headers: dict[str, str] = {}
    for h in parsed.header:
        if ":" not in h:
            parser.error(f"Header must be in 'Key: Value' format, got: {h}")
        key, value = h.split(":", 1)
        headers[key.strip()] = value.strip()

    # Parse body
    body = None
    if parsed.body:
        try:
            body = json.loads(parsed.body)
        except json.JSONDecodeError:
            parser.error(f"Body must be valid JSON, got: {parsed.body}")

    return DiffConfig(
        base_url=parsed.base,
        target_url=parsed.target,
        method=parsed.method.upper(),
        headers=headers,
        body=body,
        ignore=_split_ignore_patterns(parsed.ignore),
        format=parsed.format,
        output=parsed.output,
    )


def main(argv: list[str] | None = None) -> int:
    config = _parse_args(argv)

    # Step 1: fetch both responses
    try:
        base_resp = execute(
            RequestConfig(
                url=config.base_url,
                method=config.method,
                headers=config.headers,
                body=config.body,
                timeout=config.timeout,
            )
        )
        target_resp = execute(
            RequestConfig(
                url=config.target_url,
                method=config.method,
                headers=config.headers,
                body=config.body,
                timeout=config.timeout,
            )
        )
    except RequestError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Step 2: diff
    entries = diff(base_resp.data, target_resp.data, ignore=config.ignore)

    # Step 3: report
    reporter = Reporter(
        base_url=config.base_url,
        target_url=config.target_url,
        base_status=base_resp.status_code,
        target_status=target_resp.status_code,
        entries=entries,
    )

    output = reporter.render(config.format)

    if config.output:
        with open(config.output, "w") as f:
            f.write(output)
    else:
        print(output)

    return 0 if not entries else 1


if __name__ == "__main__":
    sys.exit(main())

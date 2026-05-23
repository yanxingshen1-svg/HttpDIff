"""Tests for the CLI argument parser."""

from httpdiff.cli import _parse_args


def test_comma_separated_ignore_patterns():
    config = _parse_args(
        [
            "-b",
            "https://api.example.com/base",
            "-t",
            "https://api.example.com/target",
            "-i",
            "timestamp,request_id",
            "-i",
            "*.updated_at",
        ]
    )

    assert config.ignore == ["timestamp", "request_id", "*.updated_at"]

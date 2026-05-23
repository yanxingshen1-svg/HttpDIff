"""Tests for the diff engine."""

import json

from httpdiff.differ import diff, DiffEntry, _matches_ignore


def _dump(entries: list[DiffEntry]) -> list[dict]:
    return [
        {"path": e.path, "kind": e.kind, "old": e.old_value, "new": e.new_value}
        for e in entries
    ]


class TestDiff:
    def test_identical(self):
        data = {"name": "Alice", "age": 25}
        assert diff(data, data.copy()) == []

    def test_added_field(self):
        old = {"a": 1}
        new = {"a": 1, "b": 2}
        entries = diff(old, new)
        assert len(entries) == 1
        assert entries[0].kind == "added"
        assert entries[0].path == "root.b"

    def test_removed_field(self):
        old = {"a": 1, "b": 2}
        new = {"a": 1}
        entries = diff(old, new)
        assert len(entries) == 1
        assert entries[0].kind == "removed"
        assert entries[0].path == "root.b"

    def test_changed_value(self):
        old = {"a": 1}
        new = {"a": 2}
        entries = diff(old, new)
        assert len(entries) == 1
        assert entries[0].kind == "changed"
        assert entries[0].old_value == 1
        assert entries[0].new_value == 2

    def test_type_changed(self):
        old = {"a": "hello"}
        new = {"a": 42}
        entries = diff(old, new)
        assert len(entries) == 1
        assert entries[0].kind == "type_changed"

    def test_nested_dict(self):
        old = {"meta": {"version": 1, "status": "ok"}}
        new = {"meta": {"version": 2, "extra": "new"}}
        entries = diff(old, new)

        kinds = {e.path: e.kind for e in entries}
        assert kinds["root.meta.version"] == "changed"
        assert kinds["root.meta.status"] == "removed"
        assert kinds["root.meta.extra"] == "added"

    def test_list_changes(self):
        old = {"items": ["a", "b", "c"]}
        new = {"items": ["a", "x", "c", "d"]}
        entries = diff(old, new)

        kinds = {e.path: e.kind for e in entries}
        assert kinds["root.items[1]"] == "changed"
        assert kinds["root.items[3]"] == "added"

    def test_list_of_objects(self):
        old = {"users": [{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}]}
        new = {"users": [{"name": "Alice", "age": 26}, {"name": "Bob", "age": 30}]}
        entries = diff(old, new)
        assert len(entries) == 1
        assert entries[0].path == "root.users[0].age"
        assert entries[0].kind == "changed"

    def test_ignore_field(self):
        old = {"id": 1, "name": "Alice", "timestamp": "2024-01-01"}
        new = {"id": 1, "name": "Alice", "timestamp": "2025-01-01"}
        entries = diff(old, new, ignore=["timestamp"])
        assert len(entries) == 0

    def test_ignore_nested(self):
        old = {"meta": {"version": 1, "updated_at": "2024-01-01"}}
        new = {"meta": {"version": 1, "updated_at": "2025-01-01"}}
        entries = diff(old, new, ignore=["updated_at"])
        assert len(entries) == 0

    def test_ignore_path(self):
        old = {"id": 1, "name": "Alice"}
        new = {"id": 2, "name": "Alice"}
        entries = diff(old, new, ignore=["id"])
        assert len(entries) == 0

    def test_empty_objects(self):
        assert diff({}, {}) == []

    def test_none_values(self):
        old = {"a": None}
        new = {"a": "something"}
        entries = diff(old, new)
        assert len(entries) == 1
        assert entries[0].kind == "changed"

    def test_deeply_nested(self):
        old = {"level1": {"level2": {"level3": {"value": 1}}}}
        new = {"level1": {"level2": {"level3": {"value": 2}}}}
        entries = diff(old, new)
        assert len(entries) == 1
        assert entries[0].path == "root.level1.level2.level3.value"


class TestMatchesIgnore:
    def test_simple_field(self):
        assert _matches_ignore("root.timestamp", ["timestamp"])
        assert _matches_ignore("root.data.timestamp", ["timestamp"])
        assert not _matches_ignore("root.timestamp_value", ["timestamp"])

    def test_dotted_path(self):
        assert _matches_ignore("root.meta.version", ["meta.version"])
        assert not _matches_ignore("root.version", ["meta.version"])

    def test_wildcard(self):
        assert _matches_ignore("root.data.updated_at", ["*.updated_at"])
        assert _matches_ignore("root.updated_at", ["*.updated_at"])

    def test_array(self):
        # Match field inside array items by last field name
        assert _matches_ignore("root.items[0].id", ["id"])
        assert _matches_ignore("root.items[1].name", ["name"])

    def test_array_path_wildcard(self):
        assert _matches_ignore("root.items[0].id", ["items.*.id"])
        assert _matches_ignore("root.items[12].metadata.updated_at", ["items.*.metadata.updated_at"])

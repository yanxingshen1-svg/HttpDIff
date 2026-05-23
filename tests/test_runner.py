"""Tests for the HTTP request runner."""

import datetime
from unittest.mock import patch

import httpx
import pytest

from httpdiff.runner import RequestConfig, RequestError, execute


def _mock_response(*args, **kwargs) -> httpx.Response:
    """Create a mock ``httpx.Response`` with ``elapsed`` set."""
    resp = httpx.Response(*args, **kwargs)
    resp._elapsed = datetime.timedelta(seconds=0.1)
    return resp


class TestExecute:
    def test_get_success(self):
        config = RequestConfig(
            url="https://api.example.com/users/1",
            method="GET",
        )
        mock = _mock_response(
            200,
            json={"id": 1, "name": "Alice"},
            headers={"content-type": "application/json"},
        )

        with patch("httpx.Client.request", return_value=mock):
            resp = execute(config)

        assert resp.status_code == 200
        assert resp.data == {"id": 1, "name": "Alice"}

    def test_post_with_body(self):
        config = RequestConfig(
            url="https://api.example.com/users",
            method="POST",
            body={"name": "Bob"},
        )
        mock = _mock_response(
            201,
            json={"id": 2, "name": "Bob"},
            headers={"content-type": "application/json"},
        )

        with patch("httpx.Client.request", return_value=mock):
            resp = execute(config)

        assert resp.status_code == 201
        assert resp.data == {"id": 2, "name": "Bob"}

    def test_lowercase_post_with_body(self):
        config = RequestConfig(
            url="https://api.example.com/users",
            method="post",
            body={"name": "Bob"},
        )
        mock = _mock_response(
            201,
            json={"id": 2, "name": "Bob"},
            headers={"content-type": "application/json"},
        )

        with patch("httpx.Client.request", return_value=mock) as request:
            execute(config)

        assert request.call_args.kwargs["method"] == "POST"
        assert request.call_args.kwargs["json"] == {"name": "Bob"}

    def test_network_error(self):
        config = RequestConfig(url="https://api.example.com/error")

        with patch("httpx.Client.request", side_effect=httpx.RequestError("connection refused")):
            with pytest.raises(RequestError, match="connection refused"):
                execute(config)

    def test_timeout(self):
        config = RequestConfig(url="https://api.example.com/timeout")

        with patch("httpx.Client.request", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(RequestError, match="timed out"):
                execute(config)

    def test_non_json_response(self):
        config = RequestConfig(url="https://api.example.com/text")
        mock = _mock_response(
            200,
            text="<html>not json</html>",
            headers={"content-type": "text/html"},
        )

        with patch("httpx.Client.request", return_value=mock):
            with pytest.raises(RequestError, match="not valid JSON"):
                execute(config)

    def test_non_200_status(self):
        """Non-2xx should still succeed — we just get the data back."""
        config = RequestConfig(url="https://api.example.com/not-found")
        mock = _mock_response(
            404,
            json={"error": "not found"},
            headers={"content-type": "application/json"},
        )

        with patch("httpx.Client.request", return_value=mock):
            resp = execute(config)

        assert resp.status_code == 404
        assert resp.data == {"error": "not found"}

"""Tests for HTTP client display formatting."""

# pylint: disable=protected-access

import pytest

from reme.components.client.http_client import HttpClient
from reme.constants import REME_DEFAULT_HOST, REME_DEFAULT_PORT, REME_SERVICE_INFO


def test_default_client_uses_loopback_address():
    """Clients connect to loopback when no service address is configured."""
    client = HttpClient()

    assert client.base_url == f"http://{REME_DEFAULT_HOST}:{REME_DEFAULT_PORT}"


def test_client_converts_wildcard_bind_address_to_loopback():
    """A service's wildcard bind address is not advertised as a destination."""
    client = HttpClient(host="0.0.0.0", port=8123)

    assert client.base_url == "http://127.0.0.1:8123"


@pytest.mark.parametrize(
    ("host", "port", "service_info", "expected"),
    [
        ("192.0.2.10", None, None, "http://192.0.2.10:2333"),
        (None, 8123, None, "http://127.0.0.1:8123"),
        ("192.0.2.10", 8123, '{"host":"192.0.2.20","port":9000}', "http://192.0.2.10:8123"),
        ("192.0.2.10", None, '{"host":"192.0.2.20","port":9000}', "http://192.0.2.10:9000"),
        (None, 8123, '{"host":"192.0.2.20","port":9000}', "http://192.0.2.20:8123"),
        (None, None, '{"host":"192.0.2.20","port":9000}', "http://192.0.2.20:9000"),
        ("192.0.2.10", None, "invalid", "http://192.0.2.10:2333"),
    ],
)
def test_client_preserves_explicit_address_fields(monkeypatch, host, port, service_info, expected):
    """Explicit address fields take precedence and only missing fields are discovered."""
    if service_info is None:
        monkeypatch.delenv(REME_SERVICE_INFO, raising=False)
    else:
        monkeypatch.setenv(REME_SERVICE_INFO, service_info)

    assert HttpClient(host=host, port=port).base_url == expected


def test_format_for_display_hides_metadata_by_default():
    """Response metadata is available structurally but not shown in normal CLI output."""
    client = HttpClient()
    text = '{"answer":"0.4.0.7","success":true,"metadata":{"version":"0.4.0.7"}}'

    assert client._format_for_display(text) == "0.4.0.7\n✅"


def test_format_for_display_shows_metadata_when_requested():
    """show_metadata=true opts into metadata display."""
    client = HttpClient(show_metadata=True)
    text = '{"answer":"0.4.0.7","success":true,"metadata":{"version":"0.4.0.7"}}'

    assert client._format_for_display(text) == '0.4.0.7\n✅ {"version": "0.4.0.7"}'

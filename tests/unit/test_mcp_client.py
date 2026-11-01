"""MCP client addresses and SDK tool descriptors."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

from mcp.types import Tool, ToolAnnotations
import pytest

from reme.components.client.mcp_client import MCPClient
from reme.constants import REME_DEFAULT_HOST, REME_DEFAULT_PORT, REME_SERVICE_INFO


def test_default_mcp_client_uses_loopback_address():
    """The network MCP client uses a connectable loopback destination."""
    client = MCPClient()

    assert client.host == REME_DEFAULT_HOST
    assert client.port == REME_DEFAULT_PORT


def test_mcp_client_converts_wildcard_bind_address_to_loopback():
    """A wildcard service address is normalized before transport construction."""
    client = MCPClient(host="0.0.0.0", port=8123)

    assert client.host == "127.0.0.1"
    assert client.port == 8123


@pytest.mark.parametrize(
    ("host", "port", "service_info", "expected_host", "expected_port"),
    [
        ("192.0.2.10", None, None, "192.0.2.10", REME_DEFAULT_PORT),
        (None, 8123, None, REME_DEFAULT_HOST, 8123),
        ("192.0.2.10", None, '{"host":"192.0.2.20","port":9000}', "192.0.2.10", 9000),
        (None, 8123, '{"host":"192.0.2.20","port":9000}', "192.0.2.20", 8123),
    ],
)
def test_mcp_client_preserves_explicit_address_fields(
    monkeypatch,
    host,
    port,
    service_info,
    expected_host,
    expected_port,
):
    """Only missing fields fall back to discovery or defaults."""
    if service_info is None:
        monkeypatch.delenv(REME_SERVICE_INFO, raising=False)
    else:
        monkeypatch.setenv(REME_SERVICE_INFO, service_info)

    client = MCPClient(host=host, port=port)

    assert (client.host, client.port) == (expected_host, expected_port)


@pytest.mark.asyncio
async def test_mcp_catalog_uses_sdk_field_names():
    """Tool catalogs expose SDK 2 fields while preserving schemas and user metadata."""
    parameters = {
        "type": "object",
        "$defs": {"Query": {"type": "string"}},
        "properties": {"query": {"$ref": "#/$defs/Query"}},
        "required": ["query"],
    }
    output = {"type": "object", "properties": {"answer": {"type": "string"}}}
    metadata = {"input_schema": "user-owned metadata", "_meta": {"keep": True}}
    tool = Tool(
        name="search",
        input_schema=parameters,
        output_schema=output,
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
        meta=metadata,
    )
    client = MCPClient()
    client.client = SimpleNamespace(list_tools=AsyncMock(return_value=[tool]))

    [action] = await client.list_actions()

    assert action["name"] == "search"
    assert action["input_schema"] == parameters
    assert action["output_schema"] == output
    assert action["annotations"]["read_only_hint"] is True
    assert action["annotations"]["open_world_hint"] is False
    assert action["meta"] == metadata
    assert {"inputSchema", "outputSchema", "_meta"}.isdisjoint(action)

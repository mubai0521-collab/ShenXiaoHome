import asyncio
import json
from unittest.mock import AsyncMock

import pytest
import mcp_client


def test_fresh_install_has_no_external_servers(tmp_path, monkeypatch):
    config_path = tmp_path / "mcp_servers.json"
    monkeypatch.setattr(mcp_client, "MCP_SERVERS_PATH", config_path)
    assert mcp_client.MCPManager().list_servers() == []
    assert json.loads(config_path.read_text(encoding="utf-8")) == {"servers": []}


def test_disabled_saved_server_cannot_connect(tmp_path, monkeypatch):
    config_path = tmp_path / "mcp_servers.json"
    config_path.write_text(json.dumps({"servers": [{
        "name": "optional", "type": "http", "url": "https://example.invalid/mcp",
        "enabled": False,
    }]}), encoding="utf-8")
    monkeypatch.setattr(mcp_client, "MCP_SERVERS_PATH", config_path)
    manager = mcp_client.MCPManager()
    connect = AsyncMock()
    monkeypatch.setattr(manager, "_connect_http", connect)
    with pytest.raises(ValueError, match="已停用"):
        asyncio.run(manager.connect("optional"))
    connect.assert_not_awaited()


def test_explicit_saved_server_is_preserved(tmp_path, monkeypatch):
    config_path = tmp_path / "mcp_servers.json"
    saved = {"servers": [{"name": "chosen", "type": "http", "enabled": True,
                           "url": "https://example.invalid/mcp"}]}
    config_path.write_text(json.dumps(saved), encoding="utf-8")
    monkeypatch.setattr(mcp_client, "MCP_SERVERS_PATH", config_path)
    assert mcp_client._load_config() == saved
    assert json.loads(config_path.read_text(encoding="utf-8")) == saved


def test_sse_client_keeps_certificate_verification(monkeypatch):
    captured = {}

    class StopBeforeNetwork(Exception):
        pass

    def client(**kwargs):
        captured.update(kwargs)
        return object()

    def transport(**kwargs):
        kwargs["httpx_client_factory"](headers={"X-Test": "preserved"})
        raise StopBeforeNetwork()

    monkeypatch.setattr(mcp_client.httpx, "AsyncClient", client)
    monkeypatch.setattr(mcp_client, "sse_client", transport)
    with pytest.raises(StopBeforeNetwork):
        asyncio.run(mcp_client.MCPManager()._connect_sse("chosen", {
            "url": "https://example.invalid/sse"}))
    assert captured["verify"] is True
    assert captured["headers"] == {"X-Test": "preserved"}

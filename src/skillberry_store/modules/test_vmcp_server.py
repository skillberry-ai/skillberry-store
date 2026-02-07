import asyncio
import os
import pytest
from skillberry_store.modules.vmcp_server import VirtualMcpServer
from skillberry_store.tests.utils import (
    clean_test_tmp_dir,
    wait_until_server_ready,
    add_tool_manifest,
)

import socket


def test_init_with_port():
    server = VirtualMcpServer(
        name="test_server", description="Test Server", port=8080, tools=[], snippets=[]
    )
    assert server.port == 8080


def test_init_without_port():
    server = VirtualMcpServer(
        name="test_server", description="Test Server", port=None, tools=[], snippets=[]
    )
    assert server.port is not None


def test_init_with_unavailable_port():
    # Create a socket to occupy a port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("localhost", 8081))
    with pytest.raises(ValueError):
        VirtualMcpServer(
            name="test_server", description="Test Server", port=8081, tools=[], snippets=[]
        )
    sock.close()


def test_to_dict():
    server = VirtualMcpServer(
        name="test_server", description="Test Server", port=8080, tools=[], snippets=["snippet1"]
    )
    server_dict = server.to_dict()
    assert server_dict["name"] == "test_server"
    assert server_dict["description"] == "Test Server"
    assert server_dict["port"] == 8080
    assert server_dict["tools"] == []
    assert server_dict["snippets"] == ["snippet1"]

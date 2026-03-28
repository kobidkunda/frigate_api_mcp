from __future__ import annotations

import socket
import subprocess


def _listen(port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port))
    sock.listen(1)
    return sock


def test_debug_refuses_to_start_when_ports_are_in_use():
    api_sock = _listen(8090)
    mcp_sock = _listen(8099)
    try:
        result = subprocess.run(
            ["./factory-analytics.sh", "debug"],
            cwd="/Users/biolasti/application/project/frigate",
            capture_output=True,
            text=True,
            timeout=10,
        )
    finally:
        api_sock.close()
        mcp_sock.close()

    assert result.returncode == 1
    assert "already in use" in (result.stdout + result.stderr).lower()

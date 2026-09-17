import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.services.auth import create_session_token


@pytest.mark.asyncio
async def test_tunnel_info_endpoint_unauthenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/tunnel-info")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_tunnel_info_endpoint_offline():
    token = create_session_token("admin")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", cookies={"vt_session": token}) as client:
        # Without ngrok running on mock port, it returns offline status gracefully
        res = await client.get("/api/tunnel-info")
        assert res.status_code == 200
        data = res.json()
        assert data["active"] is False
        assert data["public_url"] is None
        assert data["status"] == "offline"


@pytest.mark.asyncio
async def test_tunnel_info_endpoint_online_simulated():
    token = create_session_token("admin")
    transport = ASGITransport(app=app)

    simulated_ngrok_response = {
        "tunnels": [
            {
                "name": "command_line (http)",
                "uri": "/api/tunnels/command_line%20%28http%29",
                "public_url": "http://test1234.ngrok-free.app",
                "proto": "http",
            },
            {
                "name": "command_line",
                "uri": "/api/tunnels/command_line",
                "public_url": "https://test1234.ngrok-free.app",
                "proto": "https",
            }
        ]
    }

    with patch("app.api.tunnel.fetch_ngrok_tunnels", return_value=simulated_ngrok_response):
        async with AsyncClient(transport=transport, base_url="http://test", cookies={"vt_session": token}) as client:
            res = await client.get("/api/tunnel-info")
            assert res.status_code == 200
            data = res.json()
            assert data["active"] is True
            assert data["public_url"] == "https://test1234.ngrok-free.app"
            assert data["proto"] == "https"
            assert data["status"] == "connected"
            assert data["provider"] == "ngrok"

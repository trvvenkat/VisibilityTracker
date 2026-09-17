import logging
import httpx
from fastapi import APIRouter, Depends
from app.config import settings
from app.services.auth import require_authenticated_user

logger = logging.getLogger("visibility_tracker.api.tunnel")

router = APIRouter(prefix="/api", tags=["tunnel"])


async def fetch_ngrok_tunnels(api_url: str) -> dict | None:
    """Queries the ngrok API endpoint for active tunnels."""
    endpoint = f"{api_url.rstrip('/')}/api/tunnels"
    async with httpx.AsyncClient(timeout=1.5) as client:
        resp = await client.get(endpoint)
        if resp.status_code == 200:
            return resp.json()
    return None


@router.get(
    "/tunnel-info",
    summary="Get active ngrok / remote access tunnel information",
)
async def get_tunnel_info(user: str = Depends(require_authenticated_user)):
    """
    Checks if a local or containerized ngrok tunnel is active by querying
    the ngrok internal inspection API, returning the public HTTPS URL.
    """
    try:
        data = await fetch_ngrok_tunnels(settings.NGROK_API_URL)
        if data:
            tunnels = data.get("tunnels", [])
            if tunnels:
                # Prefer https tunnel if present
                https_tunnel = next((t for t in tunnels if t.get("proto") == "https"), tunnels[0])
                public_url = https_tunnel.get("public_url")
                proto = https_tunnel.get("proto", "https")
                return {
                    "active": True,
                    "public_url": public_url,
                    "proto": proto,
                    "status": "connected",
                    "provider": "ngrok",
                    "message": f"Public remote tunnel active at {public_url}",
                }
    except Exception as e:
        logger.debug(f"Ngrok API check returned: {e}")

    return {
        "active": False,
        "public_url": None,
        "proto": None,
        "status": "offline",
        "provider": None,
        "message": "No active public tunnel detected",
    }

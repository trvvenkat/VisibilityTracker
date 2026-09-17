import io
import pytest
from httpx import ASGITransport, AsyncClient
from app.config import settings
from app.main import app
from app.services.auth import create_session_token


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_upload_and_job_execution_flow():
    token = create_session_token("admin")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(settings.SESSION_COOKIE_NAME, token)
        # 1. Upload CSV file
        csv_content = b"keyword\niphone 17\nsamsung s26\nmacbook air\n"
        files = {"file": ("test_keywords.csv", io.BytesIO(csv_content), "text/csv")}
        
        upload_resp = await client.post("/api/upload", files=files)
        assert upload_resp.status_code == 201
        upload_data = upload_resp.json()
        assert "file_id" in upload_data
        assert upload_data["keyword_count"] == 3
        file_id = upload_data["file_id"]

        # 2. Start Job with mock platform
        job_req = {
            "file_id": file_id,
            "platform": "mock",
            "top_n": 3,
        }
        job_resp = await client.post("/api/jobs", json=job_req)
        assert job_resp.status_code == 202
        job_data = job_resp.json()
        assert "job_id" in job_data
        job_id = job_data["job_id"]

        # 3. Get Status
        status_resp = await client.get(f"/api/jobs/{job_id}/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["job_id"] == job_id
        assert status_data["total_keywords"] == 3

        # 4. Download CSV (available even before completion)
        dl_resp = await client.get(f"/api/jobs/{job_id}/download")
        assert dl_resp.status_code == 200
        assert "text/csv" in dl_resp.headers.get("content-type", "")

        # 5. Cancel Job
        cancel_resp = await client.post(f"/api/jobs/{job_id}/cancel")
        assert cancel_resp.status_code == 200

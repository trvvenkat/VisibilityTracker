from datetime import datetime
from pathlib import Path
import tempfile
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from app.services.auth import create_session_token
from app.services.job_manager import job_manager


@pytest.fixture
def auth_client():
    token = create_session_token("admin")
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)
    return client


@pytest.mark.asyncio
async def test_list_jobs_and_history(auth_client):
    async with auth_client as client:
        # Create a test uploaded file and job
        tmp = Path(tempfile.mktemp(suffix=".csv"))
        tmp.write_text("Keyword\nrunning shoes\n")
        file_id = "test-history-file-1"
        job_manager.register_uploaded_file(file_id, "shoes_keywords.xlsx", tmp, ["running shoes"])

        job = job_manager.create_job(file_id, "mock", 3)
        job.status = "completed"
        job.completed_count = 1
        job.started_at = datetime.now()
        job.completed_at = datetime.now()
        job_manager.save_meta(job.job_id)

        res = await client.get("/api/jobs")
        assert res.status_code == 200
        jobs = res.json()
        assert len(jobs) >= 1

        # Check job in list
        matched = [j for j in jobs if j["job_id"] == job.job_id]
        assert len(matched) == 1
        item = matched[0]
        assert item["uploaded_filename"] == "shoes_keywords.xlsx"
        assert item["platform"] == "mock"
        assert item["status"] == "completed"
        assert item["has_results_file"] is True


@pytest.mark.asyncio
async def test_download_timestamped_and_custom_filename(auth_client):
    async with auth_client as client:
        tmp = Path(tempfile.mktemp(suffix=".csv"))
        tmp.write_text("Keyword\nsmart watch\n")
        file_id = "test-dl-file-1"
        job_manager.register_uploaded_file(file_id, "watches.csv", tmp, ["smart watch"])

        job = job_manager.create_job(file_id, "amazon", 2)
        # Write dummy content to results.csv
        job.output_file.write_text("KW,SP1,SP2,Sponsored Display\nsmart watch,Watch 1,Watch 2,N/A\n")
        job.status = "completed"
        job_manager.save_meta(job.job_id)

        # 1. Default download without custom name (timestamped)
        res_default = await client.get(f"/api/jobs/{job.job_id}/download")
        assert res_default.status_code == 200
        cd_header = res_default.headers.get("content-disposition", "")
        assert "visibility_amazon_" in cd_header
        assert ".csv" in cd_header

        # 2. Custom name download
        res_custom = await client.get(f"/api/jobs/{job.job_id}/download?custom_name=my_audit_report")
        assert res_custom.status_code == 200
        cd_custom = res_custom.headers.get("content-disposition", "")
        assert "my_audit_report_" in cd_custom
        assert ".csv" in cd_custom


@pytest.mark.asyncio
async def test_clear_history_endpoint(auth_client):
    async with auth_client as client:
        # Create completed job
        tmp = Path(tempfile.mktemp(suffix=".csv"))
        tmp.write_text("Keyword\ntest kw\n")
        file_id = "test-clear-file"
        job_manager.register_uploaded_file(file_id, "clear_me.csv", tmp, ["test kw"])
        job = job_manager.create_job(file_id, "mock", 1)
        job.status = "completed"
        job_manager.save_meta(job.job_id)

        # Verify job is listed
        list_res = await client.get("/api/jobs")
        assert any(j["job_id"] == job.job_id for j in list_res.json())

        # Call clear endpoint
        clear_res = await client.post("/api/jobs/clear")
        assert clear_res.status_code == 200
        data = clear_res.json()
        assert data["success"] is True
        assert data["cleared_count"] >= 1

        # Verify job is no longer listed
        list_after = await client.get("/api/jobs")
        assert not any(j["job_id"] == job.job_id for j in list_after.json())

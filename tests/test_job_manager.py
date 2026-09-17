import pytest
from pathlib import Path
from app.services.job_manager import JobManager


def test_job_lifecycle(tmp_path):
    jm = JobManager()
    
    # 1. Register uploaded file
    file_id = "test-file-123"
    jm.register_uploaded_file(
        file_id=file_id,
        filename="test.csv",
        path=tmp_path / "test.csv",
        keywords=["laptop", "mouse", "keyboard"],
    )

    upload = jm.get_uploaded_file(file_id)
    assert upload is not None
    assert upload["count"] == 3

    # 2. Create job
    job = jm.create_job(file_id=file_id, platform="amazon", top_n=3)
    assert job.status == "queued"
    assert job.total_keywords == 3
    assert job.platform == "amazon"
    assert job.output_file.exists()

    # 3. Status response conversion
    status_resp = job.to_status_response()
    assert status_resp.job_id == job.job_id
    assert status_resp.headers == ["KW", "SP1", "SP2", "SP3", "Sponsored Display"]

    # 4. Cancellation
    success = jm.cancel_job(job.job_id)
    assert success is True
    assert job.cancel_requested is True

    # 5. Non-existent job
    assert jm.get_job("non-existent") is None
    assert jm.cancel_job("non-existent") is False

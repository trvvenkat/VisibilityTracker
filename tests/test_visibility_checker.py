import asyncio
import csv
import pytest
from app.services.job_manager import job_manager
from app.services.visibility_checker import run_visibility_check_job


@pytest.mark.asyncio
async def test_sequential_execution_and_live_csv(tmp_path):
    jm = job_manager
    
    # Register upload with 4 keywords
    file_id = "test-stream-upload"
    keywords = ["wireless mouse", "bluetooth keyboard", "usb c hub", "laptop stand"]
    jm.register_uploaded_file(
        file_id=file_id,
        filename="devices.csv",
        path=tmp_path / "devices.csv",
        keywords=keywords,
    )

    # Create job with mock scraper
    job = jm.create_job(file_id=file_id, platform="mock", top_n=2)
    assert job.output_file.exists()

    # Before job runs, only header exists in CSV
    with open(job.output_file, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        assert len(rows) == 1
        assert rows[0] == ["KW", "SP1", "SP2", "Sponsored Display"]

    # Run the job
    await run_visibility_check_job(job.job_id)

    # Verify job completion state
    assert job.status == "completed"
    assert job.completed_count == 4
    assert job.failed_count == 0
    assert job.processed_keywords == 4
    assert len(job.results) == 4

    # Verify CSV rows on disk
    with open(job.output_file, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        assert len(rows) == 5  # 1 header + 4 data rows
        assert rows[1][0] == "wireless mouse"
        assert rows[2][0] == "bluetooth keyboard"
        assert rows[3][0] == "usb c hub"
        assert rows[4][0] == "laptop stand"


@pytest.mark.asyncio
async def test_job_cancellation_preserves_completed_rows(tmp_path):
    jm = job_manager
    file_id = "test-cancel-upload"
    keywords = ["kw1", "kw2", "kw3", "kw4", "kw5"]
    jm.register_uploaded_file(file_id=file_id, filename="cancel.csv", path=tmp_path / "cancel.csv", keywords=keywords)

    job = jm.create_job(file_id=file_id, platform="mock", top_n=3)

    # Start job task and cancel after first keyword
    async def cancel_later():
        await asyncio.sleep(0.05)
        job.cancel_requested = True

    await asyncio.gather(
        run_visibility_check_job(job.job_id),
        cancel_later(),
    )

    assert job.status == "cancelled"
    # Should have processed at least 1 keyword before cancellation stopped it
    assert job.processed_keywords < 5

    # Check that rows written up to cancellation point are intact on disk
    with open(job.output_file, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        assert len(rows) == job.processed_keywords + 1

import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import re
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse

from app.schemas.job import (
    JobCreateRequest,
    JobCreateResponse,
    JobHistoryItem,
    JobResultsResponse,
    JobStatusResponse,
)
from app.services.auth import require_authenticated_user
from app.services.job_manager import job_manager
from app.services.visibility_checker import run_visibility_check_job

logger = logging.getLogger("visibility_tracker.api.jobs")

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get(
    "",
    summary="List all historical and active visibility check jobs",
)
async def list_jobs(user: str = Depends(require_authenticated_user)):
    """Returns list of past and current runs for the dashboard history table."""
    return job_manager.list_jobs()


@router.post(
    "/clear",
    summary="Clear all past pre-runs and uploaded files",
)
async def clear_jobs(user: str = Depends(require_authenticated_user)):
    """Deletes all past completed, failed, or cancelled jobs while preserving running jobs."""
    cleared_count = job_manager.clear_history()
    return {
        "success": True,
        "cleared_count": cleared_count,
        "message": f"Successfully deleted {cleared_count} previous run(s) and cleared pre-run data.",
    }


@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create and trigger a new visibility check job",
)
async def create_job(
    req: JobCreateRequest,
    user: str = Depends(require_authenticated_user),
):
    try:
        job = job_manager.create_job(
            file_id=req.file_id,
            platform=req.platform,
            top_n=req.top_n,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Launch sequential visibility check asynchronously
    asyncio.create_task(run_visibility_check_job(job.job_id))

    return JobCreateResponse(job_id=job.job_id)


@router.get(
    "/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Get current status and progress of a job",
)
async def get_job_status(
    job_id: str,
    user: str = Depends(require_authenticated_user),
):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found.")
    return job.to_status_response()


@router.get(
    "/{job_id}/results",
    response_model=JobResultsResponse,
    summary="Get all processed result rows for a job",
)
async def get_job_results(
    job_id: str,
    user: str = Depends(require_authenticated_user),
):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found.")

    headers = job.csv_writer.headers if job.csv_writer else []
    rows = [r.row for r in job.results]

    return JobResultsResponse(
        job_id=job.job_id,
        headers=headers,
        rows=rows,
        results=job.results,
    )


@router.get(
    "/{job_id}/download",
    summary="Download the live or completed CSV output file with optional custom filename",
)
async def download_job_csv(
    job_id: str,
    custom_name: str | None = Query(default=None, description="Optional custom filename without timestamp"),
    user: str = Depends(require_authenticated_user),
):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found.")

    if not job.output_file or not Path(job.output_file).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Output CSV file has not been generated yet.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if custom_name and custom_name.strip():
        # Sanitize custom filename
        clean_base = re.sub(r'[\\/*?:"<>|]', "", custom_name.strip()).strip()
        if clean_base.lower().endswith(".csv"):
            clean_base = clean_base[:-4].strip()
        if not clean_base:
            clean_base = f"visibility_{job.platform}"
        download_filename = f"{clean_base}_{timestamp}.csv"
    else:
        download_filename = f"visibility_{job.platform}_{timestamp}.csv"

    return FileResponse(
        path=str(job.output_file),
        media_type="text/csv",
        filename=download_filename,
    )


@router.post(
    "/{job_id}/cancel",
    summary="Cancel a running visibility check job",
)
async def cancel_job(
    job_id: str,
    user: str = Depends(require_authenticated_user),
):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found.")

    success = job_manager.cancel_job(job_id)
    if not success:
        return {"success": False, "message": f"Job is already in '{job.status}' state."}

    return {"success": True, "message": "Cancellation request submitted."}


@router.get(
    "/{job_id}/events",
    summary="Server-Sent Events (SSE) live updates for job progress, rows, and logs",
)
async def stream_job_events(
    job_id: str,
    user: str = Depends(require_authenticated_user),
):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found.")

    queue = job_manager.subscribe(job_id)

    async def event_generator():
        try:
            # First send initial status snapshot
            initial_status = job.to_status_response().model_dump()
            yield f"event: status\ndata: {json.dumps(initial_status)}\n\n"

            # Send any already-existing results
            for result_row in job.results:
                yield f"event: result\ndata: {json.dumps(result_row.model_dump())}\n\n"

            # Send recent logs
            for log_msg in job.logs[-20:]:
                yield f"event: log\ndata: {json.dumps({'message': log_msg})}\n\n"

            # Stream incoming events
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    evt_name = payload.get("event", "message")
                    data_json = json.dumps(payload.get("data", {}))
                    yield f"event: {evt_name}\ndata: {data_json}\n\n"

                    # Check if terminal
                    if evt_name == "status" and payload.get("data", {}).get("status") in ("completed", "failed", "cancelled"):
                        break
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat ping
                    yield ": ping\n\n"

        except asyncio.CancelledError:
            logger.debug(f"SSE client disconnected from job {job_id}")
        finally:
            job_manager.unsubscribe(job_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

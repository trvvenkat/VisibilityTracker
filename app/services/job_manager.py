import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import shutil
from typing import Literal
import uuid

from app.config import settings
from app.schemas.job import JobResultRow, JobStatusResponse
from app.services.csv_writer import LiveCSVWriter

logger = logging.getLogger("visibility_tracker.services.job_manager")


@dataclass
class JobState:
    job_id: str
    platform: str
    top_n: int
    keywords: list[str]
    uploaded_filename: str = ""
    status: Literal["queued", "running", "completed", "failed", "cancelled"] = "queued"
    total_keywords: int = 0
    processed_keywords: int = 0
    completed_count: int = 0
    failed_count: int = 0
    current_keyword: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output_file: Path | None = None
    error: str | None = None
    cancel_requested: bool = False
    csv_writer: LiveCSVWriter | None = None
    results: list[JobResultRow] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    subscribers: list[asyncio.Queue] = field(default_factory=list)

    def to_status_response(self) -> JobStatusResponse:
        headers = []
        if self.csv_writer:
            headers = self.csv_writer.headers
        else:
            headers = ["KW"] + [f"SP{i}" for i in range(1, self.top_n + 1)] + ["Sponsored Display"]

        return JobStatusResponse(
            job_id=self.job_id,
            status=self.status,
            platform=self.platform,
            top_n=self.top_n,
            total_keywords=self.total_keywords,
            processed_keywords=self.processed_keywords,
            completed_count=self.completed_count,
            failed_count=self.failed_count,
            uploaded_filename=self.uploaded_filename,
            current_keyword=self.current_keyword,
            started_at=self.started_at.isoformat() if self.started_at else None,
            completed_at=self.completed_at.isoformat() if self.completed_at else None,
            output_file=str(self.output_file) if self.output_file else None,
            error=self.error,
            headers=headers,
        )


class JobManager:
    """
    Lightweight, thread-safe in-memory and disk-backed job manager.
    Tracks active/past jobs, maintains event queues for SSE, saves metadata on disk,
    and oversees listing and clearing of run history.
    """

    def __init__(self):
        self._jobs: dict[str, JobState] = {}
        self._uploaded_files: dict[str, dict] = {}

    def register_uploaded_file(self, file_id: str, filename: str, path: Path, keywords: list[str]) -> None:
        self._uploaded_files[file_id] = {
            "file_id": file_id,
            "filename": filename,
            "path": path,
            "keywords": keywords,
            "count": len(keywords),
        }
        logger.info(f"Registered uploaded file {file_id}: {filename} ({len(keywords)} keywords)")

    def get_uploaded_file(self, file_id: str) -> dict | None:
        return self._uploaded_files.get(file_id)

    def create_job(self, file_id: str, platform: str, top_n: int) -> JobState:
        upload_info = self.get_uploaded_file(file_id)
        if not upload_info:
            raise ValueError(f"Uploaded file with id '{file_id}' not found.")

        keywords = upload_info["keywords"]
        if not keywords:
            raise ValueError("No keywords found for this file.")

        job_id = str(uuid.uuid4())
        job_dir = settings.JOBS_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        output_csv = job_dir / "results.csv"

        csv_writer = LiveCSVWriter(file_path=output_csv, top_n=top_n)

        job_state = JobState(
            job_id=job_id,
            platform=platform,
            top_n=top_n,
            keywords=keywords,
            uploaded_filename=upload_info.get("filename", "uploaded_keywords"),
            status="queued",
            total_keywords=len(keywords),
            processed_keywords=0,
            completed_count=0,
            failed_count=0,
            current_keyword=None,
            created_at=datetime.now(timezone.utc),
            started_at=None,
            completed_at=None,
            output_file=output_csv,
            error=None,
            cancel_requested=False,
            csv_writer=csv_writer,
            results=[],
            logs=[],
            subscribers=[],
        )

        self._jobs[job_id] = job_state
        self.save_meta(job_id)
        self.add_log(job_id, f"Job created for platform '{platform}' with {len(keywords)} keywords (Top N={top_n}).")
        logger.info(f"Created job {job_id} for platform {platform}")
        return job_state

    def save_meta(self, job_id: str) -> None:
        """Saves or updates the meta.json file for a job on disk."""
        job = self.get_job(job_id)
        if not job:
            return

        job_dir = settings.JOBS_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        meta_file = job_dir / "meta.json"

        meta_data = {
            "job_id": job.job_id,
            "uploaded_filename": job.uploaded_filename,
            "platform": job.platform,
            "top_n": job.top_n,
            "status": job.status,
            "total_keywords": job.total_keywords,
            "completed_count": job.completed_count,
            "failed_count": job.failed_count,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "output_file": str(job.output_file) if job.output_file else None,
            "error": job.error,
        }

        try:
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write meta.json for job {job_id}: {e}")

    def list_jobs(self) -> list[dict]:
        """
        Lists all past and active jobs across disk and memory,
        ordered from newest to oldest.
        """
        jobs_dict: dict[str, dict] = {}

        # 1. Inspect on-disk directories
        if settings.JOBS_DIR.exists():
            for job_dir in settings.JOBS_DIR.iterdir():
                if not job_dir.is_dir():
                    continue

                job_id = job_dir.name
                meta_file = job_dir / "meta.json"
                results_file = job_dir / "results.csv"
                has_results = results_file.exists() and results_file.stat().st_size > 0

                if meta_file.exists():
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                        meta["has_results_file"] = has_results
                        jobs_dict[job_id] = meta
                    except Exception as e:
                        logger.debug(f"Error reading {meta_file}: {e}")
                elif has_results:
                    # Synthesize info from directory and results.csv for past pre-runs
                    mtime = datetime.fromtimestamp(results_file.stat().st_mtime, tz=timezone.utc)
                    jobs_dict[job_id] = {
                        "job_id": job_id,
                        "uploaded_filename": "keywords_spreadsheet",
                        "platform": "unknown",
                        "top_n": 3,
                        "status": "completed",
                        "total_keywords": 0,
                        "completed_count": 0,
                        "failed_count": 0,
                        "created_at": mtime.isoformat(),
                        "started_at": mtime.isoformat(),
                        "completed_at": mtime.isoformat(),
                        "output_file": str(results_file),
                        "error": None,
                        "has_results_file": True,
                    }

        # 2. Overlay in-memory jobs (which have real-time live status for active runs)
        for job_id, job in self._jobs.items():
            has_results = bool(job.output_file and job.output_file.exists() and job.output_file.stat().st_size > 0)
            jobs_dict[job_id] = {
                "job_id": job.job_id,
                "uploaded_filename": job.uploaded_filename or "uploaded_keywords",
                "platform": job.platform,
                "top_n": job.top_n,
                "status": job.status,
                "total_keywords": job.total_keywords,
                "completed_count": job.completed_count,
                "failed_count": job.failed_count,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "output_file": str(job.output_file) if job.output_file else None,
                "error": job.error,
                "has_results_file": has_results,
            }

        # Sort newest first
        def sort_key(item: dict) -> str:
            return item.get("started_at") or item.get("created_at") or item.get("completed_at") or ""

        sorted_jobs = sorted(jobs_dict.values(), key=sort_key, reverse=True)
        return sorted_jobs

    def clear_history(self) -> int:
        """
        Deletes all historical pre-run job directories and uploads,
        skipping any active 'running' job.
        Returns the number of cleared job runs.
        """
        running_job_ids = {
            job_id for job_id, job in self._jobs.items() if job.status == "running"
        }

        cleared_count = 0

        # 1. Clean jobs directory
        if settings.JOBS_DIR.exists():
            for item in settings.JOBS_DIR.iterdir():
                if item.is_dir() and item.name not in running_job_ids:
                    try:
                        shutil.rmtree(item)
                        cleared_count += 1
                    except Exception as e:
                        logger.warning(f"Error removing job dir {item}: {e}")

        # 2. Clean uploads directory (preserve .gitkeep)
        if settings.UPLOADS_DIR.exists():
            for item in settings.UPLOADS_DIR.iterdir():
                if item.name == ".gitkeep":
                    continue
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                except Exception as e:
                    logger.warning(f"Error removing upload file {item}: {e}")

        # 3. Clean in-memory structures (retain running jobs)
        self._jobs = {
            job_id: job for job_id, job in self._jobs.items() if job_id in running_job_ids
        }
        self._uploaded_files.clear()

        logger.info(f"Cleared {cleared_count} past jobs from history.")
        return cleared_count

    def get_job(self, job_id: str) -> JobState | None:
        # Check in memory first
        if job_id in self._jobs:
            return self._jobs[job_id]

        # Check disk
        job_dir = settings.JOBS_DIR / job_id
        meta_file = job_dir / "meta.json"
        results_file = job_dir / "results.csv"

        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                
                # Reconstruct light JobState
                top_n = meta.get("top_n", 3)
                output_csv = results_file if results_file.exists() else None
                csv_writer = LiveCSVWriter(file_path=results_file, top_n=top_n) if results_file.exists() else None
                
                started_dt = None
                if meta.get("started_at"):
                    started_dt = datetime.fromisoformat(meta["started_at"])
                completed_dt = None
                if meta.get("completed_at"):
                    completed_dt = datetime.fromisoformat(meta["completed_at"])
                created_dt = datetime.now(timezone.utc)
                if meta.get("created_at"):
                    created_dt = datetime.fromisoformat(meta["created_at"])

                job_state = JobState(
                    job_id=job_id,
                    platform=meta.get("platform", "unknown"),
                    top_n=top_n,
                    keywords=[],
                    uploaded_filename=meta.get("uploaded_filename", "keywords"),
                    status=meta.get("status", "completed"),
                    total_keywords=meta.get("total_keywords", 0),
                    processed_keywords=meta.get("total_keywords", 0),
                    completed_count=meta.get("completed_count", 0),
                    failed_count=meta.get("failed_count", 0),
                    current_keyword=None,
                    created_at=created_dt,
                    started_at=started_dt,
                    completed_at=completed_dt,
                    output_file=output_csv,
                    error=meta.get("error"),
                    cancel_requested=False,
                    csv_writer=csv_writer,
                    results=[],
                    logs=[],
                    subscribers=[],
                )
                self._jobs[job_id] = job_state
                return job_state
            except Exception as e:
                logger.debug(f"Failed to restore job {job_id} from meta.json: {e}")

        elif results_file.exists():
            # Legacy directory without meta.json
            mtime = datetime.fromtimestamp(results_file.stat().st_mtime, tz=timezone.utc)
            csv_writer = LiveCSVWriter(file_path=results_file, top_n=3)
            job_state = JobState(
                job_id=job_id,
                platform="unknown",
                top_n=3,
                keywords=[],
                uploaded_filename="keywords_spreadsheet",
                status="completed",
                total_keywords=0,
                processed_keywords=0,
                completed_count=0,
                failed_count=0,
                current_keyword=None,
                created_at=mtime,
                started_at=mtime,
                completed_at=mtime,
                output_file=results_file,
                error=None,
                cancel_requested=False,
                csv_writer=csv_writer,
                results=[],
                logs=[],
                subscribers=[],
            )
            self._jobs[job_id] = job_state
            return job_state

        return None

    def cancel_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if not job:
            return False

        if job.status in ("completed", "failed", "cancelled"):
            return False

        job.cancel_requested = True
        self.add_log(job_id, "Cancellation requested by user.")
        self.save_meta(job_id)
        logger.info(f"Cancellation requested for job {job_id}")
        return True

    def add_log(self, job_id: str, message: str) -> None:
        job = self.get_job(job_id)
        if not job:
            return

        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [JOB {job_id[:8]}] {message}"
        job.logs.append(log_entry)
        logger.info(log_entry)

        # Broadcast log event to SSE subscribers
        self.broadcast_event(job_id, "log", {"message": log_entry})

    def broadcast_event(self, job_id: str, event_type: str, data: dict) -> None:
        job = self.get_job(job_id)
        if not job or not job.subscribers:
            return

        payload = {"event": event_type, "data": data}
        for queue in list(job.subscribers):
            try:
                queue.put_nowait(payload)
            except Exception as e:
                logger.debug(f"Failed to put event into subscriber queue: {e}")

    def subscribe(self, job_id: str) -> asyncio.Queue | None:
        job = self.get_job(job_id)
        if not job:
            return None
        queue: asyncio.Queue = asyncio.Queue()
        job.subscribers.append(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> None:
        job = self.get_job(job_id)
        if not job:
            return
        if queue in job.subscribers:
            job.subscribers.remove(queue)


# Global job manager singleton
job_manager = JobManager()

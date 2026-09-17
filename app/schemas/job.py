from typing import Literal
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    keyword_count: int


class JobCreateRequest(BaseModel):
    file_id: str
    platform: Literal["amazon", "flipkart", "mock"] = "amazon"
    top_n: int = Field(default=3, ge=1, le=20)


class JobCreateResponse(BaseModel):
    job_id: str


class JobResultRow(BaseModel):
    keyword: str
    sp_list: list[str]
    sponsored_display: str
    success: bool
    error: str | None = None
    row: list[str]


class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    platform: str
    top_n: int
    total_keywords: int
    processed_keywords: int
    completed_count: int
    failed_count: int
    uploaded_filename: str = ""
    current_keyword: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    output_file: str | None = None
    error: str | None = None
    headers: list[str] = Field(default_factory=list)


class JobHistoryItem(BaseModel):
    job_id: str
    uploaded_filename: str
    platform: str
    top_n: int
    status: str
    total_keywords: int
    completed_count: int
    failed_count: int
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    has_results_file: bool = False


class JobResultsResponse(BaseModel):
    job_id: str
    headers: list[str]
    rows: list[list[str]]
    results: list[JobResultRow]

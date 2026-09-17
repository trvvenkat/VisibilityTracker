import logging
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.config import settings
from app.schemas.job import UploadResponse
from app.services.auth import require_authenticated_user
from app.services.file_parser import FileParseError, parse_keyword_file
from app.services.job_manager import job_manager

logger = logging.getLogger("visibility_tracker.api.upload")

router = APIRouter(prefix="/api", tags=["upload"])

ALLOWED_EXTENSIONS = {".csv", ".xls", ".xlsx"}


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and validate keyword spreadsheet (CSV, XLS, XLSX)",
)
async def upload_keywords_file(
    file: UploadFile = File(...),
    user: str = Depends(require_authenticated_user),
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed extensions are .csv, .xls, .xlsx",
        )

    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}_{Path(file.filename).name}"
    target_path = settings.UPLOADS_DIR / safe_filename

    try:
        # Save file to disk
        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty.",
            )

        with open(target_path, "wb") as f:
            f.write(content)

        # Parse and validate keywords
        keywords = parse_keyword_file(target_path)
        if not keywords:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No non-empty keywords could be extracted from this file.",
            )

        # Register with job manager
        job_manager.register_uploaded_file(
            file_id=file_id,
            filename=file.filename,
            path=target_path,
            keywords=keywords,
        )

        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            keyword_count=len(keywords),
        )

    except FileParseError as e:
        if target_path.exists():
            target_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process file upload: {e}", exc_info=True)
        if target_path.exists():
            target_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing upload: {e}",
        )

import asyncio
from datetime import datetime, timezone
import logging
from app.config import settings
from app.scrapers import AmazonScraper, FlipkartScraper, MockScraper, PlatformScraper
from app.schemas.job import JobResultRow
from app.services.job_manager import job_manager

logger = logging.getLogger("visibility_tracker.services.visibility_checker")


def get_scraper_for_platform(platform: str) -> PlatformScraper:
    plat = platform.strip().lower()
    if plat == "amazon":
        return AmazonScraper(headless=settings.BROWSER_HEADLESS, timeout=settings.NAVIGATION_TIMEOUT)
    elif plat == "flipkart":
        return FlipkartScraper(headless=settings.BROWSER_HEADLESS, timeout=settings.NAVIGATION_TIMEOUT)
    elif plat == "mock":
        return MockScraper(simulate_latency=0.2)
    else:
        raise ValueError(f"Unknown platform: '{platform}'. Supported: amazon, flipkart, mock")


async def run_visibility_check_job(job_id: str) -> None:
    """
    Executes a visibility check job sequentially across all keywords.
    Ensures per-keyword error isolation, incremental live CSV writing,
    clean browser lifecycle management, and real-time SSE event dispatching.
    """
    job = job_manager.get_job(job_id)
    if not job:
        logger.error(f"Cannot run job {job_id}: Job not found")
        return

    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    job_manager.save_meta(job_id)
    job_manager.add_log(job_id, f"Started visibility check on '{job.platform}' ({job.total_keywords} keywords)")
    job_manager.broadcast_event(job_id, "status", job.to_status_response().model_dump())

    scraper = None
    try:
        scraper = get_scraper_for_platform(job.platform)
        job_manager.add_log(job_id, f"Initializing browser automation for {job.platform}...")
        await scraper.initialize()
        job_manager.add_log(job_id, "Browser automation initialized successfully.")

        total = job.total_keywords
        for idx, keyword in enumerate(job.keywords, start=1):
            # Check for user cancellation
            if job.cancel_requested:
                job.status = "cancelled"
                job_manager.add_log(job_id, f"Job cancelled by user at keyword {idx}/{total}.")
                break

            job.current_keyword = keyword
            job_manager.broadcast_event(job_id, "status", job.to_status_response().model_dump())
            job_manager.add_log(job_id, f"Processing [{idx}/{total}]: '{keyword}'")

            try:
                search_result = await scraper.search(keyword, top_n=job.top_n)
            except Exception as e:
                logger.error(f"Unexpected exception while searching '{keyword}': {e}", exc_info=True)
                search_result = None

            # Incremental CSV writing and progress tracking
            if search_result and search_result.success:
                row = job.csv_writer.append_row(
                    keyword=keyword,
                    sponsored_products=search_result.sponsored_products,
                    sponsored_display=search_result.sponsored_display,
                )
                job.completed_count += 1
                sp_count = len(search_result.sponsored_products)
                sd_name = search_result.sponsored_display.name if search_result.sponsored_display else "N/A"
                job_manager.add_log(
                    job_id,
                    f"✓ [{idx}/{total}] '{keyword}': Found {sp_count} SP listings, Sponsored Display: {sd_name}",
                )

                result_row = JobResultRow(
                    keyword=keyword,
                    sp_list=[sp.name for sp in search_result.sponsored_products],
                    sponsored_display=sd_name,
                    success=True,
                    error=None,
                    row=row,
                )
            else:
                row = job.csv_writer.append_failure_row(keyword=keyword)
                job.failed_count += 1
                err_msg = (search_result.error if search_result else "Scraper exception") or "Failed to load results"
                job_manager.add_log(job_id, f"✗ [{idx}/{total}] '{keyword}': Failed ({err_msg})")

                result_row = JobResultRow(
                    keyword=keyword,
                    sp_list=[],
                    sponsored_display="N/A",
                    success=False,
                    error=err_msg,
                    row=row,
                )

            job.results.append(result_row)
            job.processed_keywords += 1

            # Broadcast new row and updated status
            job_manager.broadcast_event(job_id, "result", result_row.model_dump())
            job_manager.broadcast_event(job_id, "status", job.to_status_response().model_dump())

            # Polite pacing between requests on live platforms
            if idx < total and not job.cancel_requested and job.platform != "mock":
                if settings.DELAY_BETWEEN_KEYWORDS > 0:
                    await asyncio.sleep(settings.DELAY_BETWEEN_KEYWORDS)

        # Set terminal status if not cancelled
        if job.status != "cancelled":
            job.status = "completed"
            job_manager.add_log(
                job_id,
                f"Job completed: {job.completed_count} successful, {job.failed_count} failed out of {total} keywords.",
            )

    except Exception as e:
        logger.error(f"Fatal error during job {job_id}: {e}", exc_info=True)
        job.status = "failed"
        job.error = str(e)
        job_manager.add_log(job_id, f"Fatal error: {e}")

    finally:
        job.completed_at = datetime.now(timezone.utc)
        job.current_keyword = None
        job_manager.save_meta(job_id)

        if scraper:
            try:
                await scraper.close()
                job_manager.add_log(job_id, "Browser resources released cleanly.")
            except Exception as e:
                logger.debug(f"Error during scraper cleanup: {e}")

        job_manager.broadcast_event(job_id, "status", job.to_status_response().model_dump())

import csv
import logging
import os
import threading
from pathlib import Path
from app.scrapers.base import SponsoredProduct

logger = logging.getLogger("visibility_tracker.services.csv_writer")


class LiveCSVWriter:
    """
    Manages incremental, thread-safe streaming to an output CSV file.
    Flushes and syncs to disk after each row to guarantee data durability.
    """

    def __init__(self, file_path: Path | str, top_n: int = 3):
        self.file_path = Path(file_path)
        self.top_n = max(1, top_n)
        self._lock = threading.Lock()

        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate header: KW, SP1, SP2, ..., SPN, Sponsored Display
        self.headers = ["KW"] + [f"SP{i}" for i in range(1, self.top_n + 1)] + ["Sponsored Display"]

        # Initialize file with header if not exists
        if not self.file_path.exists() or self.file_path.stat().st_size == 0:
            with open(self.file_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.headers)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            logger.info(f"Initialized live CSV at {self.file_path} with headers: {self.headers}")

    def append_row(
        self,
        keyword: str,
        sponsored_products: list[SponsoredProduct] | None,
        sponsored_display: SponsoredProduct | None,
    ) -> list[str]:
        """
        Formats and appends a single result row to the CSV file, immediately flushing to disk.
        Returns the formatted row as a list of strings.
        """
        with self._lock:
            # Build SP columns
            sp_values: list[str] = []
            sp_list = sponsored_products or []

            for i in range(self.top_n):
                if i < len(sp_list) and sp_list[i].name:
                    # Clean product name: remove newlines/tabs
                    clean_name = sp_list[i].name.replace("\r", " ").replace("\n", " ").strip()
                    sp_values.append(clean_name if clean_name else "N/A")
                else:
                    sp_values.append("N/A")

            # Build Sponsored Display column
            display_val = "N/A"
            if sponsored_display and sponsored_display.name:
                clean_display = sponsored_display.name.replace("\r", " ").replace("\n", " ").strip()
                if clean_display:
                    display_val = clean_display

            row = [keyword.strip()] + sp_values + [display_val]

            # Append to file and flush immediately
            with open(self.file_path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(row)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass

            logger.debug(f"Appended row to {self.file_path.name}: {row}")
            return row

    def append_failure_row(self, keyword: str) -> list[str]:
        """Convenience method to write N/A for all positions when a search fails."""
        return self.append_row(keyword=keyword, sponsored_products=[], sponsored_display=None)

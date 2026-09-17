import logging
from pathlib import Path
import pandas as pd

logger = logging.getLogger("visibility_tracker.services.file_parser")

KEYWORD_COLUMN_CANDIDATES = [
    "keyword",
    "keywords",
    "kw",
    "search_term",
    "search_query",
    "query",
    "search term",
    "search query",
    "products",
    "product",
]


class FileParseError(Exception):
    """Custom exception for file parsing issues."""
    pass


def parse_keyword_file(file_path: Path | str) -> list[str]:
    """
    Parses an uploaded CSV, XLS, or XLSX file and extracts a list of valid keywords.

    Rules:
    - Auto-detects format from file extension.
    - Matches preferred column headers (case-insensitive: 'keyword', 'kw', etc.)
    - Falls back to the first non-empty text column if no candidate header matches.
    - Strips surrounding whitespace from each keyword.
    - Ignores empty or whitespace-only rows.
    - Validates that at least 1 valid keyword is present.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileParseError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in (".csv", ".xls", ".xlsx"):
        raise FileParseError(f"Unsupported file format '{suffix}'. Supported formats: .csv, .xls, .xlsx")

    if path.stat().st_size == 0:
        raise FileParseError("The uploaded file is empty.")

    try:
        if suffix == ".csv":
            # Try reading with utf-8, fallback to latin1 if encoding issue
            try:
                df = pd.read_csv(path, dtype=str, skip_blank_lines=True)
            except UnicodeDecodeError:
                df = pd.read_csv(path, dtype=str, encoding="latin1", skip_blank_lines=True)
        elif suffix in (".xls", ".xlsx"):
            engine = "openpyxl" if suffix == ".xlsx" else "xlrd"
            df = pd.read_excel(path, dtype=str, engine=engine)
        else:
            raise FileParseError(f"Unsupported extension: {suffix}")
    except pd.errors.EmptyDataError:
        raise FileParseError("The uploaded file is empty.")
    except Exception as e:
        logger.error(f"Failed to read file {path}: {e}")
        raise FileParseError(f"Failed to read spreadsheet file: {e}")

    if df.empty or len(df.columns) == 0:
        raise FileParseError("The uploaded file is empty.")

    # 1. Look for preferred column header
    target_col = None
    for col in df.columns:
        clean_col = str(col).strip().lower()
        if clean_col in KEYWORD_COLUMN_CANDIDATES:
            target_col = col
            break

    # 2. If no candidate column matches, inspect columns in order
    if target_col is None:
        for col in df.columns:
            # Check if column has non-null text values
            series = df[col].dropna().astype(str).str.strip()
            valid_values = series[series != ""]
            if len(valid_values) > 0:
                target_col = col
                break

    if target_col is None:
        raise FileParseError("Could not detect a valid keyword column in the uploaded file.")

    # Extract, strip, and filter keywords
    raw_series = df[target_col].dropna().astype(str)
    keywords: list[str] = []
    seen = set()

    for item in raw_series:
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            keywords.append(cleaned)
            seen.add(cleaned)

    if not keywords:
        raise FileParseError("The file does not contain any valid, non-empty keywords.")

    logger.info(f"Successfully parsed {len(keywords)} keywords from column '{target_col}' in {path.name}")
    return keywords

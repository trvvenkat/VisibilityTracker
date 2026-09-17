import pytest
import pandas as pd
from pathlib import Path
from app.services.file_parser import parse_keyword_file, FileParseError


def test_parse_csv_with_keyword_header(tmp_path):
    file = tmp_path / "keywords.csv"
    file.write_text("keyword\niphone 17\n samsung s26 \nmacbook air\n", encoding="utf-8")
    
    kws = parse_keyword_file(file)
    assert kws == ["iphone 17", "samsung s26", "macbook air"]


def test_parse_csv_with_kw_header(tmp_path):
    file = tmp_path / "test.csv"
    file.write_text("KW,OtherColumn\nairpods,electronics\nwireless headphones,audio\n", encoding="utf-8")
    
    kws = parse_keyword_file(file)
    assert kws == ["airpods", "wireless headphones"]


def test_parse_csv_fallback_column(tmp_path):
    file = tmp_path / "fallback.csv"
    file.write_text("ItemName,Category\ncoffee maker,appliances\nblender,appliances\n", encoding="utf-8")
    
    kws = parse_keyword_file(file)
    assert kws == ["coffee maker", "blender"]


def test_parse_xlsx_file(tmp_path):
    file = tmp_path / "test.xlsx"
    df = pd.DataFrame({"keywords": ["smart watch", "fitness band", "smart ring"]})
    df.to_excel(file, index=False, engine="openpyxl")
    
    kws = parse_keyword_file(file)
    assert kws == ["smart watch", "fitness band", "smart ring"]


def test_parse_empty_csv(tmp_path):
    file = tmp_path / "empty.csv"
    file.write_text("", encoding="utf-8")
    
    with pytest.raises(FileParseError, match="empty"):
        parse_keyword_file(file)


def test_parse_csv_whitespace_and_duplicates(tmp_path):
    file = tmp_path / "dups.csv"
    file.write_text("keyword\n  gaming mouse  \n\n  \ngaming mouse\nmechanical keyboard\n", encoding="utf-8")
    
    kws = parse_keyword_file(file)
    assert kws == ["gaming mouse", "mechanical keyboard"]


def test_unsupported_extension(tmp_path):
    file = tmp_path / "test.txt"
    file.write_text("keyword\nfoo\n", encoding="utf-8")
    
    with pytest.raises(FileParseError, match="Unsupported file format"):
        parse_keyword_file(file)


def test_nonexistent_file(tmp_path):
    file = tmp_path / "does_not_exist.csv"
    with pytest.raises(FileParseError, match="File not found"):
        parse_keyword_file(file)

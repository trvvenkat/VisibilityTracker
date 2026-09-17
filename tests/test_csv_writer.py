import csv
from pathlib import Path
from app.scrapers.base import SponsoredProduct
from app.services.csv_writer import LiveCSVWriter


def test_headers_n_1(tmp_path):
    csv_file = tmp_path / "n1.csv"
    writer = LiveCSVWriter(csv_file, top_n=1)
    assert writer.headers == ["KW", "SP1", "Sponsored Display"]

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        assert reader[0] == ["KW", "SP1", "Sponsored Display"]


def test_headers_n_3(tmp_path):
    csv_file = tmp_path / "n3.csv"
    writer = LiveCSVWriter(csv_file, top_n=3)
    assert writer.headers == ["KW", "SP1", "SP2", "SP3", "Sponsored Display"]


def test_headers_n_5(tmp_path):
    csv_file = tmp_path / "n5.csv"
    writer = LiveCSVWriter(csv_file, top_n=5)
    assert writer.headers == ["KW", "SP1", "SP2", "SP3", "SP4", "SP5", "Sponsored Display"]


def test_append_row_full(tmp_path):
    csv_file = tmp_path / "results.csv"
    writer = LiveCSVWriter(csv_file, top_n=3)

    sp_list = [
        SponsoredProduct(position=1, name="Apple iPhone 17 Case"),
        SponsoredProduct(position=2, name="Spigen iPhone Case"),
        SponsoredProduct(position=3, name="ESR iPhone Case"),
    ]
    sd = SponsoredProduct(position=0, name="Official Apple Store Banner")

    row = writer.append_row("iphone 17", sp_list, sd)
    assert row == [
        "iphone 17",
        "Apple iPhone 17 Case",
        "Spigen iPhone Case",
        "ESR iPhone Case",
        "Official Apple Store Banner",
    ]

    with open(csv_file, "r", encoding="utf-8") as f:
        lines = list(csv.reader(f))
        assert len(lines) == 2  # header + row
        assert lines[1] == row


def test_append_row_missing_positions(tmp_path):
    csv_file = tmp_path / "missing.csv"
    writer = LiveCSVWriter(csv_file, top_n=3)

    # Only 1 SP listing found, no sponsored display
    sp_list = [
        SponsoredProduct(position=1, name="Samsung Cover"),
    ]

    row = writer.append_row("samsung s26", sp_list, sponsored_display=None)
    assert row == ["samsung s26", "Samsung Cover", "N/A", "N/A", "N/A"]


def test_append_failure_row(tmp_path):
    csv_file = tmp_path / "failure.csv"
    writer = LiveCSVWriter(csv_file, top_n=3)

    row = writer.append_failure_row("blocked query")
    assert row == ["blocked query", "N/A", "N/A", "N/A", "N/A"]

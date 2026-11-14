"""Offline tests: the statement parser, the PDF row reader, and the published dashboard data."""

import json
from pathlib import Path

import pandas as pd
import pytest

from payments import build, parse

ROOT = Path(__file__).resolve().parents[1]

STATEMENT = """comparative summary statement of December, 2021 and January, 2022

Serial no.\tDescription\tAmount in December, 2021\tAmount in January, 2022\t% Change
2\t No. of agents\t1123113\t1134868\t1.05%
3\tNo. of registered customer in Lac\t\t\t
\t      Total\t1114.67\t1140.18\t2.29%
8\tTotal transaction in crore BDT\t71173.09\t73367.52\t3.08%
B.\tProduct Wise Information\tAmount (in crore BDT)\tAmount (in crore BDT)\t
   2\tCash In\t22455.10\t22408.94\t-0.21%
  3\tCash Out\t\t\t
\t      Customer\t\t\t
\tTotal\t18772.74\t19730.76\t5.1%
   7\tMerchant Payment\t3453.39\t3131.06\t-9.33%
"""


def test_statement_parser_reads_both_months_and_sections(tmp_path):
    f = tmp_path / "2022-01.txt"
    f.write_text(STATEMENT, "utf8")
    df = parse.mfs_statement(f).set_index(["month", "metric"]).value
    assert df[("2021-12", "agents")] == 1123113 and df[("2022-01", "agents")] == 1134868
    assert df[("2022-01", "customers_total")] == 1140.18   # "Total" under registered customers
    assert df[("2022-01", "cash_out_total")] == 19730.76   # "Total" under cash out, not customers
    assert df[("2021-12", "merchant")] == 3453.39
    assert ("2022-01", "cash_out_customer") not in df.index  # blank cells stay missing


def test_single_month_page(tmp_path):
    f = tmp_path / "2025-03.txt"
    f.write_text("comparative summary statement of February, 2025 and \n\n2\t No. of agents\t1856190\t\t\n", "utf8")
    df = parse.mfs_statement(f)
    assert list(df.month.unique()) == ["2025-02"]


def test_pdf_row_reader_keeps_labels_and_numbers():
    rows = parse._rows("2023-24 1 2 3 4\nJuly 5 6 7 8\n2025-26P\nnot a row\n")
    assert rows == [("2023-24", [1, 2, 3, 4]), ("July", [5, 6, 7, 8]), ("2025-26", [])]


def test_financial_year_months_map_to_calendar_months():
    assert build._calendar_month("2025-26", "July") == "2025-07"
    assert build._calendar_month("2025-26", "December") == "2025-12"
    assert build._calendar_month("2025-26", "January") == "2026-01"
    assert build._calendar_month("2025-26", "June") == "2026-06"


@pytest.fixture(scope="module")
def data():
    p = ROOT / "dashboard" / "data" / "payments.json"
    if not p.exists():
        pytest.skip("run `python -m payments` first")
    return json.loads(p.read_text("utf8"))


def test_product_shares_add_up_each_month(data):
    m = pd.DataFrame(data["mix"])
    assert m.groupby("month").share.sum().between(0.99, 1.01).all()


def test_nagad_gap_is_flagged_for_twelve_months(data):
    m = pd.DataFrame(data["month"])
    gap = m[m.nagad_missing].month
    assert gap.min() == "2025-03" and gap.max() == "2026-02" and len(gap) == 12


def test_headline_ratios_match_the_tables(data):
    h, fy = data["headline"], pd.DataFrame(data["fy"]).set_index("fy")
    assert h["ib_fy26"] == pytest.approx(fy.loc["2025-26", "ib_v"])
    assert h["ib_fy26"] / h["ib_fy23"] == pytest.approx(4.14, abs=0.01)
    assert 0 < h["merchant_share_first"] < h["merchant_share_last"] < 0.1

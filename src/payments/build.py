"""Raw pages -> DuckDB warehouse: MFS product detail by month, channel totals by month and financial year."""

from pathlib import Path

import duckdb
import pandas as pd

from . import fetch, parse

ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"
MET_ISSUES = ["2025-08", "2026-08"]  # August issues close a financial year; the latest wins on overlap
# Nagad stopped reporting to Bangladesh Bank from March 2025 and resumed in March 2026 (FE, BSS).
NAGAD_GAP = ("2025-03", "2026-02")
PRODUCTS = ["cash_in", "cash_out_total", "p2p", "salary", "utility", "merchant", "government", "remittance", "others"]
FY_MONTHS = ["July", "August", "September", "October", "November", "December", "January", "February", "March",
             "April", "May", "June"]


def _calendar_month(fy: str, period: str) -> str:
    start = int(fy[:4])
    i = FY_MONTHS.index(period)
    return f"{start if i < 6 else start + 1}-{(i + 7 - 1) % 12 + 1:02d}"


def channels() -> pd.DataFrame:
    frames = []
    for rank, issue in enumerate(MET_ISSUES):
        df = parse.iig_mfs_channels(fetch.met_issue(issue))
        df["issue"], df["rank"] = issue, rank
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["month"] = [None if p == "FY" else _calendar_month(f, p) for f, p in zip(df.fy, df.period, strict=True)]
    return df


def _load(con, name, df):
    con.register("_df", df)
    con.execute(f"create or replace table {name} as select * from _df")
    con.unregister("_df")


MARTS = f"""
create or replace table channel_month as
select * exclude (rnk) from (
    select *, row_number() over (partition by month order by rank desc) as rnk from channels_raw where month is not null)
where rnk = 1;

create or replace table channel_fy as
select * exclude (rnk) from (
    select *, row_number() over (partition by fy order by rank desc) as rnk from channels_raw where period = 'FY')
where rnk = 1;

create or replace table mfs_month as
pivot (select month, metric, value from (
    select *, row_number() over (partition by month, metric order by page desc) as rnk from mfs_raw) where rnk = 1)
on metric using first(value) group by month order by month;

create or replace table mfs_mix as
unpivot (select month, value_total, {", ".join(PRODUCTS)} from mfs_month)
on {", ".join(PRODUCTS)} into name product value amount;

-- Three comparable 12-month windows ending in February, the last month with product detail
create or replace table mfs_mix_year as
select case when month between '2022-03' and '2023-02' then 'Mar 2022 to Feb 2023'
            when month between '2023-03' and '2024-02' then 'Mar 2023 to Feb 2024'
            when month between '2024-03' and '2025-02' then 'Mar 2024 to Feb 2025' end as span,
       product, sum(amount) as amount
from mfs_mix where month between '2022-03' and '2025-02' group by all;

create or replace table nagad_gap as
select month, month between '{NAGAD_GAP[0]}' and '{NAGAD_GAP[1]}' as nagad_missing from channel_month;
"""


def run(quiet: bool = False) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(WAREHOUSE))
    _load(con, "mfs_raw", parse.mfs_all(fetch.mfs_statements("2022-01", "2025-04")))
    _load(con, "channels_raw", channels())
    for stmt in filter(str.strip, MARTS.split(";")):
        con.execute(stmt)
    if not quiet:
        a = con.execute("select min(month), max(month), count(*) from mfs_month").fetchone()
        b = con.execute("select min(month), max(month), count(*) from channel_month").fetchone()
        print(f"MFS product detail {a[0]} to {a[1]} ({a[2]} months); channel totals {b[0]} to {b[1]} ({b[2]} months)")
    return con

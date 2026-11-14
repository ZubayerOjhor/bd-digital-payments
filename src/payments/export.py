"""Write dashboard/data/payments.json for the dashboard and the memo."""

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from .build import NAGAD_GAP, PRODUCTS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "dashboard" / "data"
LABELS = {"cash_in": "Cash in", "cash_out_total": "Cash out", "p2p": "Person to person", "salary": "Salary (B2P)",
          "utility": "Utility bills (P2B)", "merchant": "Merchant payment", "government": "Government (G2P)",
          "remittance": "Inward remittance", "others": "Others"}


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records", double_precision=6))


def build(con: duckdb.DuckDBPyConnection) -> dict:
    q = lambda s: con.execute(s).df()  # noqa: E731
    fy = q("""select fy, mfs_v, mfs_n, mfs_agents, mfs_subscribers, ib_v, ib_n, ib_customers, card_v, card_n, cards_total,
                     ab_v, ab_n, pos, atms from channel_fy order by fy""")
    month = q("""select c.month, c.fy, c.mfs_v, c.mfs_n, c.mfs_agents, c.mfs_subscribers, c.ib_v, c.ib_n, c.ib_customers,
                        c.card_v, c.card_n, c.ab_v, g.nagad_missing
                 from channel_month c join nagad_gap g using (month) order by month""")
    mix = q("select month, product, amount, value_total from mfs_mix order by month, product")
    mix["share"] = mix.amount / mix.value_total
    year = q("select span, product, amount from mfs_mix_year order by span, product")
    year["share"] = year.amount / year.groupby("span").amount.transform("sum")
    users = q("select month, active_accounts_lac, customers_total, agents, merchants_total from mfs_month order by month")
    providers = pd.read_csv(ROOT / "data" / "ref" / "providers_q2_2026.csv")

    y = year.pivot(index="product", columns="span", values="amount")
    first, last = y.columns[0], y.columns[-1]
    growth = ((y[last] / y[first] - 1)).to_dict()
    sh = year.pivot(index="product", columns="span", values="share")
    f = fy.set_index("fy")
    cash = ["cash_in", "cash_out_total"]
    headline = {
        "mfs_fy15": float(f.loc["2014-15", "mfs_v"]), "mfs_fy26": float(f.loc["2025-26", "mfs_v"]),
        "ib_fy15": float(f.loc["2014-15", "ib_v"]), "ib_fy23": float(f.loc["2022-23", "ib_v"]), "ib_fy26": float(f.loc["2025-26", "ib_v"]),
        "mfs_fy23": float(f.loc["2022-23", "mfs_v"]), "card_fy26": float(f.loc["2025-26", "card_v"]),
        "ib_customers_fy25": float(f.loc["2024-25", "ib_customers"]), "ib_customers_fy26": float(f.loc["2025-26", "ib_customers"]),
        "ib_n_fy23": float(f.loc["2022-23", "ib_n"]), "ib_n_fy26": float(f.loc["2025-26", "ib_n"]),
        "ib_ticket_fy24": float(f.loc["2023-24", "ib_v"] * 1e7 / f.loc["2023-24", "ib_n"]),
        "ib_ticket_fy26": float(f.loc["2025-26", "ib_v"] * 1e7 / f.loc["2025-26", "ib_n"]),
        "mfs_ticket_fy26": float(f.loc["2025-26", "mfs_v"] * 1e7 / f.loc["2025-26", "mfs_n"]),
        "cash_share_first": float(sh.loc[cash, first].sum()), "cash_share_last": float(sh.loc[cash, last].sum()),
        "merchant_share_first": float(sh.loc["merchant", first]), "merchant_share_last": float(sh.loc["merchant", last]),
        "growth": {k: float(v) for k, v in growth.items()},
        "span_first": first, "span_last": last,
        "nagad_gap": list(NAGAD_GAP),
        "q2_2026_total_lakh_crore": 6.60,
    }
    return {
        "meta": {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "labels": LABELS, "products": PRODUCTS,
                 "detail_months": [mix.month.min(), mix.month.max()], "channel_months": [month.month.min(), month.month.max()]},
        "headline": headline, "fy": _records(fy), "month": _records(month), "mix": _records(mix),
        "mix_year": _records(year), "users": _records(users), "providers": _records(providers),
    }


def write(con: duckdb.DuckDBPyConnection) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    d = build(con)
    (OUT / "payments.json").write_text(json.dumps(d, separators=(",", ":")), "utf8")
    return d

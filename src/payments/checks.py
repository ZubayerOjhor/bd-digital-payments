"""Checks that must pass before anything is exported."""

from dataclasses import dataclass

import duckdb

from .build import PRODUCTS


@dataclass
class Result:
    name: str
    ok: bool
    detail: str


def run(con: duckdb.DuckDBPyConnection) -> list[Result]:
    one = lambda sql: con.execute(sql).fetchone()  # noqa: E731
    out = []

    # 1. Each statement page shows two months, so most months appear twice. Both copies must agree.
    n = one("""select count(*) from (select month, metric, max(value) - min(value) d, max(abs(value)) m
                from mfs_raw group by all having count(*) > 1) where d > 0.005 * m""")[0]
    out.append(Result("Months reported on two statement pages agree", n == 0, f"{n} disagreements"))

    # 2. Product lines add up to the total value (the published lines are rounded, so allow 1%)
    gap, m = one(f"select max(abs(({' + '.join(PRODUCTS)}) / value_total - 1)), arg_max(month, abs(({' + '.join(PRODUCTS)}) / value_total - 1)) from mfs_month")
    out.append(Result("MFS products add up to the total", gap < 0.01, f"largest gap {gap:.2%} in {m}"))

    # 3. Two Bangladesh Bank publications agree on MFS value (statement page vs Monthly Economic Trends)
    worst, month, exact = one("""select max(abs(m.value_total / c.mfs_v - 1)), arg_max(month, abs(m.value_total / c.mfs_v - 1)),
                                        avg((abs(m.value_total / c.mfs_v - 1) < 0.001)::int)
                                 from mfs_month m join channel_month c using (month)""")
    out.append(Result("MFS statement and Monthly Economic Trends agree", worst < 0.04,
                      f"{exact:.0%} of months within 0.1%; largest gap {worst:.1%} in {month}"))

    # 4. Overlapping months in two Monthly Economic Trends issues agree (no silent revisions)
    rev = one("""select max(abs(a.mfs_v / b.mfs_v - 1)) + max(abs(a.ib_v / b.ib_v - 1)) + max(abs(a.card_v / b.card_v - 1))
                 from channels_raw a join channels_raw b on a.month = b.month and a.issue < b.issue""")[0]
    out.append(Result("Overlapping months agree across report issues", rev < 0.01, f"largest revision {rev:.2%}"))

    # 5. A complete financial year equals the sum of its 12 months
    fy = one("""with m as (select fy, count(*) n, sum(mfs_v) mfs, sum(ib_v) ib, sum(card_v) card from channel_month group by 1)
                select max(greatest(abs(m.mfs / f.mfs_v - 1), abs(m.ib / f.ib_v - 1), abs(m.card / f.card_v - 1)))
                from m join channel_fy f using (fy) where m.n = 12""")[0]
    out.append(Result("Financial-year totals equal the sum of their months", fy < 0.005, f"largest gap {fy:.3%}"))

    # 6. No missing months in either series
    g1 = one("select count(*) from (select month, lag(month) over (order by month) p from mfs_month) where p is not null and strptime(month, '%Y-%m') - interval 1 month <> strptime(p, '%Y-%m')")[0]
    g2 = one("select count(*) from (select month, lag(month) over (order by month) p from channel_month) where p is not null and strptime(month, '%Y-%m') - interval 1 month <> strptime(p, '%Y-%m')")[0]
    out.append(Result("No missing months", g1 + g2 == 0, f"{g1} gaps in product detail, {g2} in channel totals"))

    # 7. The Nagad reporting gap is visible where the press says it is: a fall in MFS agents in March 2025
    #    and a jump when reporting resumed in March 2026. Comparisons across these months are not like for like.
    drop, jump = one("""select (select mfs_agents from channel_month where month = '2025-03') / (select mfs_agents from channel_month where month = '2025-02') - 1,
                               (select mfs_agents from channel_month where month = '2026-03') / (select mfs_agents from channel_month where month = '2026-02') - 1""")
    out.append(Result("Nagad reporting gap located (Mar 2025 to Feb 2026)", drop < -0.15 and jump > 0.25,
                      f"MFS agents {drop:+.0%} in Mar 2025, {jump:+.0%} in Mar 2026"))
    return out

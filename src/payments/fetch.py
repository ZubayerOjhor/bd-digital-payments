"""Download Bangladesh Bank's payment statistics into data/raw, once. Reruns read the cache.

Two sources, both from Bangladesh Bank:
- MFS comparative summary statements (bb.org.bd, Payment and Settlement Systems > Mobile Financial Services).
  One page per month with that month and the one before: accounts, agents, and transaction value by product
  (cash in, cash out, P2P, salary, utility bills, merchant, government, remittance). The site offers
  January 2022 onward and returns "No data found" after February 2025.
- Monthly Economic Trends, Table IIG (E-banking and e-commerce statistics): cards, internet banking, MFS,
  agent banking and e-commerce, annual from FY2014-15 and monthly for recent years.

The site sits behind a JavaScript bot check, so pages are fetched with a real (headless) browser.
"""

import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
MFS_URL = "https://www.bb.org.bd/en/index.php/financialactivity/mfsdata"
MET_URL = "https://www.bb.org.bd/pub/monthly/econtrds/et{mon}{yy}.pdf"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def _months(first: str, last: str) -> list[str]:
    y, m = map(int, first.split("-"))
    out = []
    while f"{y}-{m:02d}" <= last:
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def mfs_statements(first: str = "2022-01", last: str = "2025-12") -> list[Path]:
    """Save the statement table for every month as text. Months with no data are recorded as empty files."""
    out_dir = RAW / "bb_mfs"
    out_dir.mkdir(parents=True, exist_ok=True)
    todo = [m for m in _months(first, last) if not (out_dir / f"{m}.txt").exists()]
    if todo:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(user_agent=UA)
            for month in todo:
                y, m = month.split("-")
                for _ in range(5):  # the bot check sometimes serves an empty page first
                    pg.goto(MFS_URL, wait_until="networkidle", timeout=90000)
                    try:
                        pg.wait_for_selector("#select_month", timeout=15000)
                        break
                    except Exception:
                        pg.wait_for_timeout(3000)
                pg.select_option("#select_month", m)
                pg.select_option("#select_year", y)
                with pg.expect_navigation(wait_until="networkidle", timeout=90000):
                    pg.click("input[name=mfssearch_submit]")
                text = pg.inner_text("body")
                start, end = text.find("comparative summary statement"), text.find("[1 lac = 0.10 million")
                body = "" if "No data found" in text else text[start:end]
                (out_dir / f"{month}.txt").write_text(body, "utf8")
                print(month, "ok" if body else "no data")
            b.close()
    return sorted(out_dir.glob("*.txt"))


def met_issue(month: str) -> Path:
    """Download one Monthly Economic Trends issue, e.g. month='2026-08' -> etaug26.pdf."""
    y, m = month.split("-")
    mon = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"][int(m) - 1]
    url = MET_URL.format(mon=mon, yy=y[2:])
    path = RAW / "met" / Path(url).name
    if path.exists() and path.read_bytes()[:4] == b"%PDF":
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(user_agent=UA, accept_downloads=True)
        pg = ctx.new_page()
        for _ in range(4):
            try:
                with pg.expect_download(timeout=90000) as d:
                    try:
                        pg.goto(url, timeout=90000)
                    except Exception:
                        pass  # navigation is aborted when the download starts
                d.value.save_as(path)
                break
            except Exception:
                pg.wait_for_timeout(4000)
        b.close()
    if not path.exists() or path.read_bytes()[:4] != b"%PDF":
        raise RuntimeError(f"could not download {url}")
    return path


NUM = re.compile(r"-?\d[\d,]*\.?\d*%?")

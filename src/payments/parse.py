"""Parse the raw Bangladesh Bank pages into tidy tables."""

import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], 1)}

# Statement row label -> metric name. Rows under "registered customer", "merchant" and "Cash Out" are
# disambiguated by the section they sit in.
SIMPLE = {
    "No. of agents": "agents",
    "Total No of MFS users": "users_lac",
    "No. of active accounts": "active_accounts_lac",
    "No. of total transaction": "transactions",
    "Total transaction in crore BDT": "value_total",
    "Inward Remittance": "remittance",
    "Cash In": "cash_in",
    "P2P transaction": "p2p",
    "Salary Disbursement": "salary",
    "Utility Bill Payment": "utility",
    "Merchant Payment": "merchant",
    "Government Payment": "government",
    "Others": "others",
}
SECTIONS = {"No. of registered customer": "customers", "No of merchant": "merchants", "Cash Out": "cash_out"}
SUBROWS = {"Male": "male", "Female": "female", "Total": "total", "Regular Merchant": "regular", "PRA": "pra",
           "Customer": "customer", "Merchant + PRA": "merchant"}


def _num(s: str) -> float | None:
    s = s.strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def mfs_statement(path: Path) -> pd.DataFrame:
    """One statement page -> rows (month, metric, value) for both months on the page."""
    text = path.read_text("utf8")
    if not text.strip():
        return pd.DataFrame(columns=["month", "metric", "value", "page"])
    # The page for March 2025 carries February only: the second month can be missing
    head = re.search(r"statement of (\w+), (\d{4}) and(?: (\w+), (\d{4}))?", text)
    prev = f"{head.group(2)}-{MONTHS[head.group(1)]:02d}"
    cur = f"{head.group(4)}-{MONTHS[head.group(3)]:02d}" if head.group(3) else None
    rows, section = [], None
    for line in text.splitlines():
        cells = [c.strip() for c in line.split("\t")]
        label = next((c for c in cells if c and not re.fullmatch(r"[A-Z]?\.?\d*\.?", c)), "")
        if not label:
            continue
        for key, sec in SECTIONS.items():
            if label.startswith(key):
                section = sec
        metric = None
        if section and label in SUBROWS:
            metric = f"{section}_{SUBROWS[label]}"
        else:
            metric = next((v for k, v in SIMPLE.items() if label.startswith(k)), None)
            if metric:
                section = None
        if not metric:
            continue
        nums = [_num(c) for c in cells[cells.index(label) + 1:]][:2]
        for month, v in zip((prev, cur), nums, strict=False):
            if v is not None and month:
                rows.append({"month": month, "metric": metric, "value": v, "page": path.stem})
    return pd.DataFrame(rows)


def mfs_all(paths: list[Path]) -> pd.DataFrame:
    return pd.concat([mfs_statement(p) for p in paths], ignore_index=True)


# ---------------- Monthly Economic Trends, Table IIG ----------------

PERIOD = re.compile(r"^(\d{4}-\d{2})P?\b|^(July|August|September|October|November|December|January|February|March|April|May|June)\b")


def _rows(page_text: str) -> list[tuple[str | None, list[float]]]:
    out = []
    for line in page_text.splitlines():
        line = line.strip()
        m = PERIOD.match(line)
        label = (m.group(1) or m.group(2)) if m else None
        rest = line[m.end():] if m else line
        toks = rest.split()
        if toks and all(re.fullmatch(r"-?\d+(\.\d+)?", t) for t in toks) and len(toks) >= 4:
            out.append((label, [float(t) for t in toks]))
        elif label and not toks:
            out.append((label, []))
    return out


def iig_pages(pdf: Path) -> tuple[int, int]:
    """Table IIG runs over several facing pages. Return the last two: totals with internet banking, then the
    concluding page with MFS and agent banking."""
    r = PdfReader(str(pdf))
    last = next(i for i, p in enumerate(r.pages) if "TABLE IIG (Concld.)" in (p.extract_text() or ""))
    if "Internet" not in (r.pages[last - 1].extract_text() or ""):
        raise ValueError(f"{pdf.name}: page before Table IIG (Concld.) has no internet banking columns")
    return last - 1, last


def iig_mfs_channels(pdf: Path) -> pd.DataFrame:
    """Channel totals from Table IIG: card transactions, internet banking, MFS, agent banking, e-commerce.

    Page 3 holds period labels plus total card transactions, card counts, internet banking and e-commerce;
    page 4 holds MFS and agent banking. Rows on the two pages are in the same order.
    """
    r = PdfReader(str(pdf))
    p3, p4 = iig_pages(pdf)
    rows3 = _rows(r.pages[p3].extract_text())
    # Skip the row of printed column numbers (34 36 37 ...), which is numeric too
    rows4 = [x for x in _rows(r.pages[p4].extract_text()) if x[1] and x[1][0] >= 1000]
    labels, fy, out = [], None, []
    for label, vals in rows3:
        if label and "-" in label:
            fy = label
            if not vals:
                continue  # an open financial year has a label row with no totals
            labels.append((fy, "FY", vals))
        elif label:
            labels.append((fy, label, vals))
    if len(labels) != len(rows4):
        raise ValueError(f"{pdf.name}: {len(labels)} labelled rows on page 3 but {len(rows4)} on page 4")
    for (fy, period, v3), (_, v4) in zip(labels, rows4, strict=True):
        # Some issues print the internet banking amount as the first column of the last page instead
        if len(v3) == 10 and len(v4) in (11, 5):
            v3, v4 = [*v3, v4[0]], v4[1:]
        if len(v3) != 11 or len(v4) not in (10, 4):
            raise ValueError(f"{pdf.name} {fy} {period}: unexpected columns {len(v3)}, {len(v4)}")
        rec = {"fy": fy, "period": period,
               "card_n": v3[2], "card_v": v3[3], "cards_credit": v3[4], "cards_debit": v3[5], "cards_prepaid": v3[6],
               "cards_total": v3[7], "ib_customers": v3[8], "ib_n": v3[9], "ib_v": v3[10],
               "mfs_agents": v4[0], "mfs_n": v4[1], "mfs_v": v4[2], "mfs_subscribers": v4[3]}
        if len(v4) == 10:
            rec |= {"ab_agents": v4[4], "ab_n": v4[5], "ab_v": v4[6], "ab_subscribers": v4[7], "atms": v4[8], "pos": v4[9]}
        out.append(rec)
    return pd.DataFrame(out)

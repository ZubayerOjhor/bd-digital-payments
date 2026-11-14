"""python -m payments [build|export|all]   (fetching happens inside build and is cached in data/raw)"""

import sys

from . import build, checks, export


def main(step: str) -> None:
    con = build.run()
    results = checks.run(con)
    for r in results:
        print("PASS" if r.ok else "FAIL", r.name, "|", r.detail)
    if not all(r.ok for r in results):
        raise SystemExit("Data checks failed: nothing exported.")
    if step in ("export", "all"):
        d = export.write(con)
        print("wrote dashboard/data/payments.json,", len(d["month"]), "months of channel totals")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")

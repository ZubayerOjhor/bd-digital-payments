"""Serve the dashboard and screenshot every tab into docs/screens (also a smoke test: fails on console errors)."""

import functools
import http.server
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TABS = ["answer", "channels", "mfs", "banks", "market", "method"]


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "dashboard"))
    handler.log_message = lambda *a, **k: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=2)
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{server.server_address[1]}/#answer", wait_until="networkidle")
        page.wait_for_timeout(1200)
        for i, tab in enumerate(TABS, 1):
            page.click(f"button[data-tab={tab}]")
            page.wait_for_timeout(900)
            page.evaluate("document.querySelector('.tabs').style.position='static'; window.scrollTo(0, 0)")
            page.screenshot(path=str(out / f"{i:02d}_{tab}.png"), full_page=True)
        b.close()
    server.shutdown()
    print(f"{len(TABS)} screenshots -> {out}")
    if errors:
        print("console errors:", *errors, sep="\n  ")
        sys.exit(1)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "screens")

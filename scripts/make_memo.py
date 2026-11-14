"""Render memo/memo.html to memo/strategy_memo.pdf (A4, 4 pages). Charts come from dashboard/data/payments.json."""

import functools
import http.server
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    handler.log_message = lambda *a, **k: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto(f"http://127.0.0.1:{server.server_address[1]}/memo/memo.html", wait_until="networkidle")
        page.evaluate("() => window.ready")
        page.wait_for_timeout(600)
        over = page.evaluate("""() => [...document.querySelectorAll('.page')].map((pg, i) => {
            const f = pg.querySelector('.foot').getBoundingClientRect().top;
            const last = Math.max(...[...pg.children].filter(c => !c.classList.contains('foot')).map(c => c.getBoundingClientRect().bottom));
            return [i + 1, Math.round(f - last)]; })""")
        print("space above footer (px) per page:", over)
        page.pdf(path=str(ROOT / "memo" / "strategy_memo.pdf"), format="A4", print_background=True, prefer_css_page_size=True)
        b.close()
    server.shutdown()
    print("memo/strategy_memo.pdf")


if __name__ == "__main__":
    main()

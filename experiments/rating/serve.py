"""Serves the rating page on http://127.0.0.1:8125/ and keeps the answers in experiments/rating/results.json."""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).parent
FINAL = "--final" in sys.argv                                  # the 200-line final check: final.html, final_results.json
HYBRID = "--hybrid" in sys.argv                                # the second model's output on the routed lines
PAGE = HERE / ("hybrid.html" if HYBRID else "final.html" if FINAL else "index.html")
RESULTS = HERE / ("hybrid_results.json" if HYBRID else "final_results.json" if FINAL else "results.json")


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, kind: str = "application/json; charset=utf-8", status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._send(PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/state":
            if RESULTS.exists():
                self._send(json.dumps(json.loads(RESULTS.read_text(encoding="utf-8")).get("state", {})).encode("utf-8"))
            else:
                self._send(b"{}")
        else:
            self._send(b"not found", "text/plain", 404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/save":
            self._send(b"not found", "text/plain", 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            temp = RESULTS.with_suffix(".tmp")
            temp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
            temp.replace(RESULTS)
            self._send(b"{}")
        except Exception as exc:  # noqa: BLE001 - the page shows that saving failed; the server must keep running
            self._send(str(exc).encode("utf-8"), "text/plain", 500)

    def log_message(self, *args) -> None:  # quiet
        pass


if __name__ == "__main__":
    print("Puanlama sayfası: http://127.0.0.1:8125/  (durdurmak için Ctrl+C)", flush=True)
    HTTPServer(("127.0.0.1", 8125), Handler).serve_forever()

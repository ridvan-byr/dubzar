"""Recovers answers that the rating page kept only in the browser (the results server was not running when they were given).

    python experiments/rating/recover.py      then open http://127.0.0.1:8125/ in the SAME browser that was used for rating

It serves a page on the same address (so the same browser storage), reads the saved answers from it and writes them, together with
the hidden A/B mapping, to results.json. It never reads the old results file's state back into the page.
"""

import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = HERE / "results.json"

PAGE = """<!DOCTYPE html><meta charset="utf-8"><title>Kurtarma</title>
<body style="font-family:Segoe UI,system-ui;background:#231f1b;color:#f7f5f0;padding:40px;line-height:1.6">
<h2>Puanlama kurtarma</h2><p id="msg">Bakılıyor…</p>
<script>
(async()=>{
  const raw=localStorage.getItem("rating");
  if(!raw){document.getElementById("msg").textContent="Bu tarayıcıda kayıtlı puanlama yok. Puanlamayı yaptığın tarayıcıdan aç.";return}
  const state=JSON.parse(raw);
  const n=Object.keys(state.ratings||{}).length;
  const r=await fetch("/recover",{method:"POST",body:JSON.stringify(state)});
  const out=await r.json();
  document.getElementById("msg").innerHTML="Bulundu: <b>"+n+"</b> satır puanlanmış. Kaydedildi: <b>"+out.saved+"</b> satır. Bunu Claude'a söyleyebilirsin.";
})();
</script>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, kind: str = "text/html; charset=utf-8", status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        self._send(PAGE.encode("utf-8"))

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        state = json.loads(self.rfile.read(length).decode("utf-8"))
        # the hidden mapping lives in index.html (DATA); rebuild it from there
        html = (HERE / "index.html").read_text(encoding="utf-8")
        data = json.loads(re.search(r"const DATA=(\[.*?\]);\nconst WHY", html, re.S).group(1))
        mapping = [{"id": d["id"], "a_is": d["a_is"], "category": d["category"], "en": d["en"],
                    "tr_dubzar": d["a"] if d["a_is"] == "dubzar" else d["b"],
                    "tr_claude": d["a"] if d["a_is"] == "claude" else d["b"]} for d in data]
        temp = RESULTS.with_suffix(".tmp")
        temp.write_text(json.dumps({"state": state, "mapping": mapping}, ensure_ascii=False, indent=1), encoding="utf-8")
        temp.replace(RESULTS)
        self._send(json.dumps({"saved": len(state.get("ratings", {}))}).encode("utf-8"), "application/json")

    def log_message(self, *args) -> None:
        pass


if __name__ == "__main__":
    print("Kurtarma sayfası: http://127.0.0.1:8125/", flush=True)
    HTTPServer(("127.0.0.1", 8125), Handler).serve_forever()

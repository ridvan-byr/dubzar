"""Live progress page for the training pipeline on http://127.0.0.1:8126/ (reads training/status.json, refreshes by itself)."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).parent
STATUS = HERE / "status.json"

PAGE = """<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dubzar eğitim süreci</title><style>
:root{--bg:#231f1b;--surface:#352F2A;--line:#4A423B;--text:#F7F5F0;--muted:#A89F94;--accent:#F2C14E;--ok:#7fe0b0}
*{box-sizing:border-box;margin:0}body{font-family:"Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--text);padding:32px 20px}
main{max-width:720px;margin:0 auto}h1{font-size:22px;font-weight:500}.sub{color:var(--muted);font-size:14px;margin:4px 0 22px}
.banner{padding:14px 18px;border-radius:14px;margin-bottom:20px;background:var(--surface);border:1px solid var(--line);font-size:16px}
.banner.done{border-color:var(--ok);color:var(--ok)}
.stage{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:14px 18px;margin-bottom:10px}
.row{display:flex;justify-content:space-between;gap:12px;font-size:15px}.row span:last-child{color:var(--muted)}
.track{height:8px;border-radius:4px;background:var(--line);overflow:hidden;margin:10px 0 6px}.fill{height:100%;background:var(--accent);transition:width .6s}
.stage.done .fill{background:var(--ok)}.detail{color:var(--muted);font-size:13px;min-height:18px}
pre{background:#1a1713;border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-top:18px;font:12.5px/1.5 Consolas,monospace;color:var(--muted);max-height:260px;overflow:auto;white-space:pre-wrap}
</style></head><body><main><h1>Dubzar · eğitim süreci</h1><p class="sub" id="sub"></p><div id="banner" class="banner"></div><div id="stages"></div><pre id="log"></pre></main>
<script>
async function tick(){try{const s=await (await fetch("/status.json",{cache:"no-store"})).json();const st=Object.values(s.stages);
const done=st.filter(x=>x.state=="bitti").length,run=st.find(x=>x.state=="sürüyor");
const age=s.updated?Math.round(Date.now()/1000-s.updated):null;
document.getElementById("sub").textContent=age===null?"Henüz başlamadı":`Son güncelleme ${age} sn önce`;
const b=document.getElementById("banner");
if(done==st.length){b.className="banner done";b.textContent="Hepsi bitti."}
else{b.className="banner";b.textContent=run?`Şu an: ${run.title} (%${Math.round(run.percent)})`:`${done} / ${st.length} aşama bitti`+(age!==null&&age>600?" · 10 dakikadır güncelleme yok, takılmış olabilir":"")}
document.getElementById("stages").innerHTML=st.map(x=>`<div class="stage ${x.state=="bitti"?"done":""}"><div class="row"><span>${x.title}</span><span>${x.state=="bitti"?"bitti":x.state=="sürüyor"?"%"+Math.round(x.percent):x.state}</span></div><div class="track"><div class="fill" style="width:${x.percent}%"></div></div><div class="detail">${x.detail||""}</div></div>`).join("");
const l=document.getElementById("log");l.textContent=(s.log||[]).join("\\n");l.scrollTop=l.scrollHeight}catch(e){}}
tick();setInterval(tick,2000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            body, kind = PAGE.encode("utf-8"), "text/html; charset=utf-8"
        elif self.path.startswith("/status.json"):
            body = STATUS.read_bytes() if STATUS.exists() else json.dumps({"stages": {}, "log": [], "updated": 0}).encode()
            kind = "application/json"
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        pass


if __name__ == "__main__":
    print("Süreç sayfası: http://127.0.0.1:8126/", flush=True)
    HTTPServer(("127.0.0.1", 8126), Handler).serve_forever()

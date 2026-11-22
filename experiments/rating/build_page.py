"""Builds experiments/rating/index.html: a blind rating page for Dubzar's translation against Claude's, on rating_set.SET.

    python experiments/rating/build_page.py     (translates the 90 lines with the current Dubzar translator)
    python experiments/rating/serve.py          (serves the page; every answer is saved to results.json)

Which translation is A and which is B is random per line and hidden; the page only shows it at the end.
"""

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from rating_set import SET  # noqa: E402

PAGE = r"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Çeviri puanlama</title>
<style>
:root{--bg:#231f1b;--surface:#352F2A;--line:#4A423B;--text:#F7F5F0;--muted:#A89F94;--accent:#F2C14E;--ink:#2B2622;--ok:#7fe0b0;--minor:#F2C14E;--bad:#ff8f8f}
*{box-sizing:border-box;margin:0}body{font-family:"Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.5}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:14px 20px;z-index:5}
header .row{max-width:900px;margin:0 auto;display:flex;align-items:center;gap:16px;justify-content:space-between}
.bar{height:6px;border-radius:3px;background:var(--line);overflow:hidden;max-width:900px;margin:10px auto 0}.bar i{display:block;height:100%;background:var(--accent);width:0;transition:width .3s}
main{max-width:900px;margin:0 auto;padding:24px 20px 80px}
.chip{display:inline-block;font-size:12px;padding:3px 10px;border-radius:999px;border:1px solid var(--line);color:var(--muted)}
.ctx{margin-top:14px;color:var(--muted);font-size:15px}.ctx b{color:var(--text);font-weight:500}
.en{font-size:30px;font-weight:500;letter-spacing:-.01em;margin:10px 0 22px;line-height:1.25}
.grid{display:grid;gap:14px;grid-template-columns:1fr}@media(min-width:760px){.grid{grid-template-columns:1fr 1fr}}
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:18px}
.card h3{font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:500}
.tr{font-size:22px;margin:8px 0 14px;min-height:34px}
.btns{display:flex;gap:8px;flex-wrap:wrap}
button{font:inherit;color:var(--text);background:transparent;border:1px solid var(--line);border-radius:999px;padding:9px 16px;cursor:pointer;transition:background .15s,border-color .15s}
button:hover{border-color:var(--muted)}
button.on.ok{background:var(--ok);color:var(--ink);border-color:var(--ok)}button.on.minor{background:var(--minor);color:var(--ink);border-color:var(--minor)}button.on.bad{background:var(--bad);color:var(--ink);border-color:var(--bad)}
.why{margin-top:12px;display:none;flex-wrap:wrap;gap:6px}.why.show{display:flex}.why button{font-size:13px;padding:5px 12px}.why button.on{background:var(--line)}
.pref{margin-top:20px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}.pref span{color:var(--muted)}.pref button.on{background:var(--accent);color:var(--ink);border-color:var(--accent)}
.nav{display:flex;justify-content:space-between;margin-top:26px;gap:10px}.nav .primary{background:var(--accent);color:var(--ink);border-color:var(--accent)}
.hint{color:var(--muted);font-size:13px;margin-top:6px}
#result{display:none;margin-top:30px}table{width:100%;border-collapse:collapse;margin-top:10px}th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);font-size:15px}th{color:var(--muted);font-weight:500;font-size:13px}
.saved{font-size:12px;color:var(--muted)}
</style></head><body>
<header><div class="row"><b>Çeviri puanlama</b><span id="count">1 / 90</span><span class="saved" id="saved"></span><button id="finish">Sonuçları göster</button></div><div class="bar"><i id="fill"></i></div></header>
<main>
 <div id="item"></div>
 <div id="result"></div>
</main>
<script>
const DATA=__DATA__;
const WHY=[["meaning","Anlam yanlış"],["natural","Doğal değil"],["register","Üslup (sen/siz, argo)"],["term","Oyun terimi"],["name","İsim"],["missing","Eksik ya da fazla"]];
let state={ratings:{},at:0};
const $=s=>document.querySelector(s);
async function load(){try{const r=await fetch("/state");if(r.ok){const s=await r.json();if(s&&s.ratings)state=s}}catch(e){}
  if(!Object.keys(state.ratings).length){try{const l=JSON.parse(localStorage.getItem("rating")||"null");if(l)state=l}catch(e){}}
  render()}
let timer;function save(){localStorage.setItem("rating",JSON.stringify(state));clearTimeout(timer);timer=setTimeout(async()=>{try{await fetch("/save",{method:"POST",body:JSON.stringify({state,mapping:DATA.map(d=>({id:d.id,a_is:d.a_is,category:d.category,en:d.en,tr_dubzar:d.a_is=="dubzar"?d.a:d.b,tr_claude:d.a_is=="claude"?d.a:d.b}))})});$("#saved").textContent="kaydedildi"}catch(e){$("#saved").textContent="sunucuya kaydedilemedi (tarayıcıda duruyor)"}},300)}
function r(id){return state.ratings[id]=state.ratings[id]||{}}
function render(){
  const d=DATA[state.at],rt=r(d.id),done=DATA.filter(x=>{const q=state.ratings[x.id];return q&&q.a&&q.b}).length;
  $("#count").textContent=`${state.at+1} / ${DATA.length}  (puanlanan: ${done})`;$("#fill").style.width=100*done/DATA.length+"%";
  const card=(k,label)=>{const q=rt[k]||{};return `<div class="card"><h3>${label}</h3><div class="tr">${esc(d[k])}</div>
   <div class="btns">${[["ok","Düzgün"],["minor","Küçük sorun"],["bad","Ciddi hata"]].map(([v,t])=>`<button class="${v}${q.r==v?" on":""}" data-k="${k}" data-r="${v}">${t}</button>`).join("")}</div>
   <div class="why${q.r&&q.r!="ok"?" show":""}">${WHY.map(([v,t])=>`<button class="${(q.why||[]).includes(v)?"on":""}" data-k="${k}" data-w="${v}">${t}</button>`).join("")}</div></div>`};
  $("#item").innerHTML=`<span class="chip">${d.category}</span>${d.context?`<div class="ctx">Önceki satır: <b>${esc(d.context)}</b></div>`:""}
   <div class="en">${esc(d.en)}</div><div class="grid">${card("a","Çeviri A")}${card("b","Çeviri B")}</div>
   <div class="pref"><span>Hangisi daha iyi?</span>${[["a","A"],["eq","Eşit"],["b","B"]].map(([v,t])=>`<button class="${rt.pref==v?"on":""}" data-p="${v}">${t}</button>`).join("")}</div>
   <div class="nav"><button id="prev" ${state.at==0?"disabled":""}>← Önceki</button><button class="primary" id="next">${state.at==DATA.length-1?"Bitir":"Sonraki →"}</button></div>
   <p class="hint">"Düzgün": anlam doğru, doğal, üslup uygun. "Küçük sorun": anlaşılıyor ama kulağa yanlış geliyor. "Ciddi hata": anlam yanlış ya da saçma.</p>`;
}
function esc(s){return String(s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}
document.addEventListener("click",e=>{const t=e.target.closest("button");if(!t)return;const d=DATA[state.at],rt=r(d.id);
  if(t.dataset.r){const q=rt[t.dataset.k]=rt[t.dataset.k]||{};q.r=t.dataset.r;if(q.r=="ok")q.why=[];save();render()}
  else if(t.dataset.w){const q=rt[t.dataset.k];q.why=q.why||[];const i=q.why.indexOf(t.dataset.w);i<0?q.why.push(t.dataset.w):q.why.splice(i,1);save();render()}
  else if(t.dataset.p){rt.pref=t.dataset.p;save();render()}
  else if(t.id=="prev"){state.at--;save();render();scrollTo(0,0)}
  else if(t.id=="next"){if(state.at<DATA.length-1){state.at++;save();render();scrollTo(0,0)}else summary()}
  else if(t.id=="finish")summary()});
function summary(){
  const sys={dubzar:{ok:0,minor:0,bad:0,why:{},n:0},claude:{ok:0,minor:0,bad:0,why:{},n:0}},pref={dubzar:0,claude:0,eq:0},cat={};
  for(const d of DATA){const q=state.ratings[d.id];if(!q)continue;
    for(const k of ["a","b"]){const s=d.a_is==(k=="a"?"dubzar":"claude")||false;const who=(k=="a")?d.a_is:(d.a_is=="dubzar"?"claude":"dubzar");const x=q[k];if(!x||!x.r)continue;
      sys[who][x.r]++;sys[who].n++;(x.why||[]).forEach(w=>sys[who].why[w]=(sys[who].why[w]||0)+1);
      if(who=="dubzar"){cat[d.category]=cat[d.category]||{ok:0,minor:0,bad:0,n:0};cat[d.category][x.r]++;cat[d.category].n++}}
    if(q.pref){pref[q.pref=="eq"?"eq":(q.pref=="a"?d.a_is:(d.a_is=="dubzar"?"claude":"dubzar"))]++}}
  const pc=(v,n)=>n?Math.round(100*v/n)+"%":"-";const name={dubzar:"Dubzar (şimdiki)",claude:"Claude"};
  const whyName=Object.fromEntries(WHY);
  let h=`<h2>Sonuç</h2><table><tr><th></th><th>Puanlanan</th><th>Düzgün</th><th>Küçük sorun</th><th>Ciddi hata</th></tr>`+
   ["dubzar","claude"].map(k=>`<tr><td>${name[k]}</td><td>${sys[k].n}</td><td>${pc(sys[k].ok,sys[k].n)}</td><td>${pc(sys[k].minor,sys[k].n)}</td><td>${pc(sys[k].bad,sys[k].n)}</td></tr>`).join("")+`</table>`;
  h+=`<h2 style="margin-top:24px">Tercih</h2><p>Dubzar daha iyi: <b>${pref.dubzar}</b> · Eşit: <b>${pref.eq}</b> · Claude daha iyi: <b>${pref.claude}</b></p>`;
  h+=`<h2 style="margin-top:24px">Dubzar'ın sorun türleri</h2><p>${Object.entries(sys.dubzar.why).sort((a,b)=>b[1]-a[1]).map(([w,c])=>`${whyName[w]}: <b>${c}</b>`).join(" · ")||"-"}</p>`;
  h+=`<h2 style="margin-top:24px">Dubzar, türe göre</h2><table><tr><th>Tür</th><th>Düzgün</th><th>Küçük sorun</th><th>Ciddi hata</th></tr>`+Object.entries(cat).map(([c,v])=>`<tr><td>${c}</td><td>${pc(v.ok,v.n)}</td><td>${pc(v.minor,v.n)}</td><td>${pc(v.bad,v.n)}</td></tr>`).join("")+`</table>`;
  $("#item").style.display="none";$("#result").style.display="block";$("#result").innerHTML=h+`<div class="nav"><button id="back">← Geri dön</button></div>`;
  $("#back").onclick=()=>{$("#result").style.display="none";$("#item").style.display="block";render()};scrollTo(0,0)}
load();
</script></body></html>"""


SINGLE = r"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Çeviri puanlama (son kontrol)</title>
<style>
:root{--bg:#231f1b;--surface:#352F2A;--line:#4A423B;--text:#F7F5F0;--muted:#A89F94;--accent:#F2C14E;--ink:#2B2622;--ok:#7fe0b0;--minor:#F2C14E;--bad:#ff8f8f}
*{box-sizing:border-box;margin:0}body{font-family:"Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.5}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:14px 20px;z-index:5}
header .row{max-width:760px;margin:0 auto;display:flex;align-items:center;gap:16px;justify-content:space-between}
.bar{height:6px;border-radius:3px;background:var(--line);overflow:hidden;max-width:760px;margin:10px auto 0}.bar i{display:block;height:100%;background:var(--accent);width:0;transition:width .3s}
main{max-width:760px;margin:0 auto;padding:24px 20px 80px}
.chip{display:inline-block;font-size:12px;padding:3px 10px;border-radius:999px;border:1px solid var(--line);color:var(--muted)}
.ctx{margin-top:14px;color:var(--muted);font-size:15px}.ctx b{color:var(--text);font-weight:500}
.en{font-size:26px;font-weight:500;margin:10px 0 18px;line-height:1.25}
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:20px}
.tr{font-size:24px;margin:0 0 16px}
.btns{display:flex;gap:8px;flex-wrap:wrap}
button{font:inherit;color:var(--text);background:transparent;border:1px solid var(--line);border-radius:999px;padding:9px 16px;cursor:pointer}
button:hover{border-color:var(--muted)}
button.on.ok{background:var(--ok);color:var(--ink);border-color:var(--ok)}button.on.minor{background:var(--minor);color:var(--ink);border-color:var(--minor)}button.on.bad{background:var(--bad);color:var(--ink);border-color:var(--bad)}
.why{margin-top:12px;display:none;flex-wrap:wrap;gap:6px}.why.show{display:flex}.why button{font-size:13px;padding:5px 12px}.why button.on{background:var(--line)}
.nav{display:flex;justify-content:space-between;margin-top:24px;gap:10px}.nav .primary{background:var(--accent);color:var(--ink);border-color:var(--accent)}
.hint{color:var(--muted);font-size:13px;margin-top:8px}.saved{font-size:12px;color:var(--muted)}
#result{display:none;margin-top:30px}table{width:100%;border-collapse:collapse;margin-top:10px}th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);font-size:15px}th{color:var(--muted);font-weight:500;font-size:13px}
</style></head><body>
<header><div class="row"><b>Son kontrol</b><span id="count"></span><span class="saved" id="saved"></span><button id="finish">Sonuçları göster</button></div><div class="bar"><i id="fill"></i></div></header>
<main><div id="item"></div><div id="result"></div></main>
<script>
const DATA=__DATA__;
const WHY=[["meaning","Anlam yanlış"],["natural","Doğal değil"],["register","Üslup (sen/siz, argo)"],["term","Oyun terimi"],["name","İsim"],["missing","Eksik ya da fazla"]];
let state={ratings:{},at:0};const $=s=>document.querySelector(s);
async function load(){try{const r=await fetch("/state");if(r.ok){const s=await r.json();if(s&&s.ratings&&Object.keys(s.ratings).length)state=s}}catch(e){}
  if(!Object.keys(state.ratings).length){try{const l=JSON.parse(localStorage.getItem("rating_final")||"null");if(l)state=l}catch(e){}}render()}
let timer;function save(){localStorage.setItem("rating_final",JSON.stringify(state));clearTimeout(timer);timer=setTimeout(async()=>{try{const r=await fetch("/save",{method:"POST",body:JSON.stringify({state,mapping:DATA})});if(!r.ok)throw 0;$("#saved").textContent="kaydedildi"}catch(e){$("#saved").textContent="SUNUCUYA KAYDEDİLEMEDİ: sunucu kapanmış olabilir, Claude'a söyle"}},300)}
function r(id){return state.ratings[id]=state.ratings[id]||{}}
function esc(s){return String(s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}
function render(){const d=DATA[state.at],q=r(d.id),done=DATA.filter(x=>state.ratings[x.id]&&state.ratings[x.id].r).length;
  $("#count").textContent=`${state.at+1} / ${DATA.length}  (puanlanan: ${done})`;$("#fill").style.width=100*done/DATA.length+"%";
  $("#item").innerHTML=`<span class="chip">${d.category}</span>${d.context?`<div class="ctx">Önceki satır: <b>${esc(d.context)}</b></div>`:""}
  <div class="en">${esc(d.en)}</div><div class="card"><div class="tr">${esc(d.tr)}</div>
  <div class="btns">${[["ok","Düzgün"],["minor","Küçük sorun"],["bad","Ciddi hata"]].map(([v,t])=>`<button class="${v}${q.r==v?" on":""}" data-r="${v}">${t}</button>`).join("")}</div>
  <div class="why${q.r&&q.r!="ok"?" show":""}">${WHY.map(([v,t])=>`<button class="${(q.why||[]).includes(v)?"on":""}" data-w="${v}">${t}</button>`).join("")}</div></div>
  <div class="nav"><button id="prev" ${state.at==0?"disabled":""}>← Önceki</button><button class="primary" id="next">${state.at==DATA.length-1?"Bitir":"Sonraki →"}</button></div>
  <p class="hint">"Düzgün": anlam doğru, doğal, üslup uygun. "Küçük sorun": anlaşılıyor ama kulağa yanlış geliyor. "Ciddi hata": anlam yanlış ya da saçma.</p>`}
document.addEventListener("click",e=>{const t=e.target.closest("button");if(!t)return;const d=DATA[state.at],q=r(d.id);
  if(t.dataset.r){q.r=t.dataset.r;if(q.r=="ok")q.why=[];save();render()}
  else if(t.dataset.w){q.why=q.why||[];const i=q.why.indexOf(t.dataset.w);i<0?q.why.push(t.dataset.w):q.why.splice(i,1);save();render()}
  else if(t.id=="prev"){state.at--;save();render();scrollTo(0,0)}
  else if(t.id=="next"){if(state.at<DATA.length-1){state.at++;save();render();scrollTo(0,0)}else summary()}
  else if(t.id=="finish")summary()});
function summary(){const tot={ok:0,minor:0,bad:0,n:0},why={},cat={};
  for(const d of DATA){const q=state.ratings[d.id];if(!q||!q.r)continue;tot[q.r]++;tot.n++;(q.why||[]).forEach(w=>why[w]=(why[w]||0)+1);cat[d.category]=cat[d.category]||{ok:0,minor:0,bad:0,n:0};cat[d.category][q.r]++;cat[d.category].n++}
  const pc=(v,n)=>n?Math.round(100*v/n)+"%":"-",wn=Object.fromEntries(WHY);
  $("#item").style.display="none";$("#result").style.display="block";
  $("#result").innerHTML=`<h2>Sonuç</h2><p>Puanlanan: <b>${tot.n}</b> · Düzgün: <b>${pc(tot.ok,tot.n)}</b> · Küçük sorun: <b>${pc(tot.minor,tot.n)}</b> · Ciddi hata: <b>${pc(tot.bad,tot.n)}</b></p>
  <p style="margin-top:10px">${Object.entries(why).sort((a,b)=>b[1]-a[1]).map(([w,c])=>`${wn[w]}: <b>${c}</b>`).join(" · ")}</p>
  <table><tr><th>Tür</th><th>Düzgün</th><th>Küçük sorun</th><th>Ciddi hata</th></tr>${Object.entries(cat).map(([c,v])=>`<tr><td>${c}</td><td>${pc(v.ok,v.n)}</td><td>${pc(v.minor,v.n)}</td><td>${pc(v.bad,v.n)}</td></tr>`).join("")}</table>
  <div class="nav"><button id="back">← Geri dön</button></div>`;
  $("#back").onclick=()=>{$("#result").style.display="none";$("#item").style.display="block";render()};scrollTo(0,0)}
load();
</script></body></html>"""


def build_final() -> int:
    """The final check: 200 fresh lines, one Dubzar translation each, rated by a native speaker."""
    from final_set import FINAL

    from dubzar.translate import OpusMtTranslator

    translator = OpusMtTranslator(threads=8)
    translator.load()
    data = [{"id": i, "category": c, "context": ctx, "en": en, "tr": translator.translate(en)}
            for i, (c, ctx, en) in enumerate(FINAL, 1)]
    (HERE / "final.html").write_text(SINGLE.replace("__DATA__", json.dumps(data, ensure_ascii=False)), encoding="utf-8")
    print(f"{len(data)} lines -> {HERE / 'final.html'}")
    return 0


def main() -> int:
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    if "--final" in sys.argv:
        return build_final()
    from dubzar.translate import OpusMtTranslator

    translator = OpusMtTranslator(threads=8)
    translator.load()
    rng = random.Random(20261122)
    data = []
    for i, (category, context, english, claude) in enumerate(SET, 1):
        dubzar = translator.translate(english)
        dubzar_first = rng.random() < 0.5
        a, b = (dubzar, claude) if dubzar_first else (claude, dubzar)
        data.append({"id": i, "category": category, "context": context, "en": english, "a": a, "b": b,
                     "a_is": "dubzar" if dubzar_first else "claude"})
    (HERE / "index.html").write_text(PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False)), encoding="utf-8")
    print(f"{len(data)} lines -> {HERE / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

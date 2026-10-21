"""
Generate the HTML reports from the scraped data.

  python report.py
    -> msca_report.html          (Tier 1: MSCA/COFUND + VHIO + la Caixa, + deadlines)
    -> netherlands_report.html   (Tier 2: AcademicTransfer life-science PhD)
"""
from __future__ import annotations

import csv
import datetime
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def esc(s):
    return html.escape(str(s if s is not None else ""))


def _days_left(deadline, today):
    try:
        return (datetime.datetime.fromisoformat(deadline).date() - today).days
    except (ValueError, TypeError):
        return None


def load_positions(json_file):
    path = os.path.join(DATA, json_file)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("positions", [])


def load_deadlines():
    path = os.path.join(DATA, "annual_deadlines.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


STYLE = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#15202b;--muted:#5b6b7b;--line:#e4e8ec;
--accent:#1f6feb;--green:#0b8457;--cofund:#8257e6;--vhio:#c026d3;--caixa:#0ea5e9;
--at:#d97706;--industry:#059669;--chip:#eef2f6;--soon:#c2410c;}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0e1116;
--card:#171b22;--ink:#e6edf3;--muted:#9aa7b4;--line:#262c36;--accent:#4e8cff;
--green:#3fb984;--cofund:#a983ff;--vhio:#e879f9;--caixa:#38bdf8;--at:#fbbf24;
--industry:#34d399;--chip:#1e242d;--soon:#ff8a4c;}}
:root[data-theme="dark"]{--bg:#0e1116;--card:#171b22;--ink:#e6edf3;--muted:#9aa7b4;
--line:#262c36;--accent:#4e8cff;--green:#3fb984;--cofund:#a983ff;--vhio:#e879f9;
--caixa:#38bdf8;--at:#fbbf24;--industry:#34d399;--chip:#1e242d;--soon:#ff8a4c;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:32px 16px 64px}
h1{margin:0 0 4px;font-size:25px;letter-spacing:-.02em}
header p{margin:0;color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:22px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.card .num{font-size:28px;font-weight:700;letter-spacing:-.02em}
.card .lbl{color:var(--muted);font-size:13px;margin-top:2px}
section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin:16px 0}
h2{font-size:16px;margin:0 0 14px}
.controls{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.controls input,.controls select{background:var(--bg);color:var(--ink);border:1px solid var(--line);
border-radius:8px;padding:8px 10px;font-size:14px}.controls input{flex:1;min-width:180px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600;cursor:pointer;white-space:nowrap;user-select:none}
th:hover{color:var(--ink)}td a{color:var(--accent);text-decoration:none}td a:hover{text-decoration:underline}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;white-space:nowrap}
.s-EURAXESS{background:color-mix(in srgb,var(--accent) 16%,transparent);color:var(--accent)}
.s-VHIO{background:color-mix(in srgb,var(--vhio) 18%,transparent);color:var(--vhio)}
.s-laCaixa{background:color-mix(in srgb,var(--caixa) 18%,transparent);color:var(--caixa)}
.s-AT{background:color-mix(in srgb,var(--at) 20%,transparent);color:var(--at)}
.s-Industry{background:color-mix(in srgb,var(--industry) 18%,transparent);color:var(--industry)}
.days{font-variant-numeric:tabular-nums;white-space:nowrap}.days.urgent{color:var(--soon);font-weight:700}
.muted{color:var(--muted)}.count{color:var(--muted);font-size:13px;margin-bottom:8px}
footer{color:var(--muted);font-size:12px;margin-top:24px;text-align:center}
"""


def source_class(src):
    s = (src or "").lower()
    if "euraxess" in s:
        return "s-EURAXESS"
    if "vhio" in s:
        return "s-VHIO"
    if "caixa" in s:
        return "s-laCaixa"
    if "academictransfer" in s:
        return "s-AT"
    if "industry" in s:
        return "s-Industry"
    return ""


def render(positions, title, subtitle, gen, deadlines=None, repo_url=""):
    today = datetime.date.today()
    positions = sorted(positions, key=lambda p: (not p.get("deadline"), p.get("deadline") or ""))
    n = len(positions)
    import collections
    countries = collections.Counter(p.get("country") for p in positions if p.get("country"))
    sources = collections.Counter(p.get("source") for p in positions)
    soon = sum(1 for p in positions
               if (_days_left(p.get("deadline"), today) or 999) >= 0
               and (_days_left(p.get("deadline"), today) or 999) <= 14)

    rows = []
    for p in positions:
        dl = _days_left(p.get("deadline"), today)
        rows.append({
            "title": p.get("title", ""), "url": p.get("url", ""),
            "org": p.get("organisation") or p.get("host_institution") or "",
            "field": p.get("research_field", ""), "source": p.get("source", ""),
            "country": p.get("country", ""), "open": p.get("open_date", ""),
            "deadline": (p.get("deadline") or "")[:10],
            "deadline_disp": p.get("deadline_display") or (p.get("deadline") or "")[:10],
            "days": dl,
        })

    cards = [(n, "open positions"), (len(sources), "sources"),
             (len(countries), "countries"), (soon, "close ≤14 days")]
    cards_html = "".join(
        f'<div class="card"><div class="num">{v}</div><div class="lbl">{esc(l)}</div></div>'
        for v, l in cards)

    dl_section = ""
    if deadlines:
        drows = "".join(
            f'<tr><td><a href="{esc(d["url"])}" target="_blank" rel="noopener">{esc(d["scheme"])}</a>'
            f'<div class="muted">{esc(d["organisation"])} · {esc(d["field"])}</div></td>'
            f'<td>{esc(d["countries"])}</td><td>{esc(d["frequency"])}</td>'
            f'<td>{esc(d["typical_opens"])}</td><td>{esc(d["typical_deadline"])}</td></tr>'
            for d in deadlines)
        dl_section = f"""<section><h2>Expected annual deadlines (recurring schemes)</h2>
        <div class="muted" style="margin-bottom:10px">Dates are typical windows from past cycles — verify on each official page.</div>
        <table><thead><tr><th>Scheme</th><th>Countries</th><th>Frequency</th><th>Opens</th><th>Deadline</th></tr></thead>
        <tbody>{drows}</tbody></table></section>"""

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)}</title>
<style>{STYLE}</style></head><body><div class="wrap">
<header><h1>{esc(title)}</h1><p>{esc(subtitle)} · generated {esc(gen)}</p></header>
<div class="cards">{cards_html}</div>
<section><h2>Open positions</h2>
<div class="controls"><input id="q" type="search" placeholder="Search title, country, organisation, source…">
<select id="src"><option value="">All sources</option>{"".join(f'<option>{esc(s)}</option>' for s in sources)}</select></div>
<div class="count" id="count"></div>
<table id="tbl"><thead><tr><th data-k="title">Position</th><th data-k="source">Source</th>
<th data-k="country">Country</th><th data-k="open">Opened</th><th data-k="deadline">Deadline</th>
<th data-k="days">Days left</th></tr></thead><tbody id="tb"></tbody></table></section>
{dl_section}
<footer>Auto-updated weekly · <a href="{esc(repo_url)}">{esc(repo_url)}</a></footer>
</div><script>
const DATA={json.dumps(rows, ensure_ascii=False)};
const SC={json.dumps({'EURAXESS':'s-EURAXESS','VHIO':'s-VHIO','la Caixa':'s-laCaixa','AcademicTransfer (NL)':'s-AT','Industry (EURAXESS)':'s-Industry'})};
const tb=document.getElementById('tb'),q=document.getElementById('q'),src=document.getElementById('src'),cnt=document.getElementById('count');
let sortK='deadline',dir=1;
function esc(s){{const d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML;}}
function render(){{const t=q.value.toLowerCase(),sf=src.value;
let rows=DATA.filter(r=>{{if(sf&&r.source!==sf)return false;if(!t)return true;
return (r.title+' '+r.country+' '+r.org+' '+r.source+' '+r.field).toLowerCase().includes(t);}});
rows.sort((a,b)=>{{let x=a[sortK],y=b[sortK];if(sortK==='days'){{x=x==null?1e9:x;y=y==null?1e9:y;return (x-y)*dir;}}
x=(x||'').toString().toLowerCase();y=(y||'').toString().toLowerCase();return x<y?-dir:x>y?dir:0;}});
cnt.textContent=rows.length+' shown';
tb.innerHTML=rows.map(r=>{{const u=(r.days!=null&&r.days<=14&&r.days>=0)?' urgent':'';
const dl=r.days==null?'—':(r.days<0?'closed':r.days+'d');const cls=SC[r.source]||'';
return `<tr><td><a href="${{r.url}}" target="_blank" rel="noopener">${{esc(r.title)}}</a>
<div class="muted">${{esc(r.org)}} · ${{esc(r.field)}}</div></td>
<td><span class="pill ${{cls}}">${{esc(r.source)}}</span></td><td>${{esc(r.country)}}</td>
<td class="muted">${{esc(r.open)}}</td><td>${{esc(r.deadline_disp)}}</td>
<td class="days${{u}}">${{dl}}</td></tr>`;}}).join('');}}
document.querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{{const k=th.dataset.k;
if(k===sortK)dir*=-1;else{{sortK=k;dir=1;}}render();}});
q.oninput=render;src.onchange=render;render();
</script></body></html>"""


def main():
    repo = "https://github.com/jgand3107/msca-doctoral-index"
    gen = datetime.date.today().isoformat()

    t1 = load_positions("msca_doctoral_positions.json")
    html1 = render(t1, "Doctoral Scholarships — Life Sciences",
                   "MSCA/COFUND + VHIO + la Caixa · R1 · 7 countries",
                   gen, deadlines=load_deadlines(), repo_url=repo)
    open(os.path.join(HERE, "msca_report.html"), "w", encoding="utf-8").write(html1)
    print("wrote msca_report.html", len(t1), "positions")

    t2 = load_positions("netherlands_phd.json")
    html2 = render(t2, "Netherlands PhD — Life Sciences (Tier 2)",
                   "AcademicTransfer · life-science PhD vacancies in the Netherlands",
                   gen, repo_url=repo)
    open(os.path.join(HERE, "netherlands_report.html"), "w", encoding="utf-8").write(html2)
    print("wrote netherlands_report.html", len(t2), "positions")

    t3 = load_positions("industry_phd.json")
    html3 = render(t3, "Industry PhD — Life Sciences (Tier 3)",
                   "EURAXESS · PhD positions at companies (Large Enterprise / SME) "
                   "in the 7 countries", gen, repo_url=repo)
    open(os.path.join(HERE, "industry_report.html"), "w", encoding="utf-8").write(html3)
    print("wrote industry_report.html", len(t3), "positions")


if __name__ == "__main__":
    main()

"""
Generate the HTML reports from the scraped data.

  python report.py
    -> msca_report.html / industry_report.html / france_report.html /
       cancer_radar_report.html, and scholarships_report.html (combined, tabbed).
"""
from __future__ import annotations

import csv
import datetime
import html
import json
import os

from sources import deadlines as deadlines_mod

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
--at:#d97706;--industry:#059669;--linkedin:#0a66c2;--doctorat:#0f766e;--chip:#eef2f6;--soon:#c2410c;}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0e1116;
--card:#171b22;--ink:#e6edf3;--muted:#9aa7b4;--line:#262c36;--accent:#4e8cff;
--green:#3fb984;--cofund:#a983ff;--vhio:#e879f9;--caixa:#38bdf8;--at:#fbbf24;
--industry:#34d399;--linkedin:#539be8;--doctorat:#2dd4bf;--chip:#1e242d;--soon:#ff8a4c;}}
:root[data-theme="dark"]{--bg:#0e1116;--card:#171b22;--ink:#e6edf3;--muted:#9aa7b4;
--line:#262c36;--accent:#4e8cff;--green:#3fb984;--cofund:#a983ff;--vhio:#e879f9;
--caixa:#38bdf8;--at:#fbbf24;--industry:#34d399;--linkedin:#539be8;--doctorat:#2dd4bf;--chip:#1e242d;--soon:#ff8a4c;}
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
.st{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600}
.st-open{background:color-mix(in srgb,var(--green) 22%,transparent);color:var(--green)}
.st-rolling{background:color-mix(in srgb,var(--accent) 16%,transparent);color:var(--accent)}
.st-upcoming{background:color-mix(in srgb,var(--at) 20%,transparent);color:var(--at)}
.st-check{background:var(--chip);color:var(--muted)}
.s-LinkedIn{background:color-mix(in srgb,var(--linkedin) 18%,transparent);color:var(--linkedin)}
.s-Doctorat{background:color-mix(in srgb,var(--doctorat) 20%,transparent);color:var(--doctorat)}
.days{font-variant-numeric:tabular-nums;white-space:nowrap}.days.urgent{color:var(--soon);font-weight:700}
.muted{color:var(--muted)}.count{color:var(--muted);font-size:13px;margin-bottom:8px}
footer{color:var(--muted);font-size:12px;margin-top:24px;text-align:center}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:18px 0 4px;border-bottom:1px solid var(--line)}
.tab{background:none;border:0;border-bottom:2px solid transparent;color:var(--muted);
font:inherit;font-weight:600;font-size:14px;padding:9px 12px;cursor:pointer}
.tab:hover{color:var(--ink)}.tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.tab .b{display:inline-block;margin-left:6px;background:var(--chip);color:var(--muted);
border-radius:999px;padding:0 7px;font-size:11px}
.panel{display:none}.panel.active{display:block}
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
    if "linkedin" in s:
        return "s-LinkedIn"
    if "doctorat" in s:
        return "s-Doctorat"
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
            f'<tr><td><span class="st st-{esc(d.get("status","check"))}">{esc(d.get("status_label",""))}</span></td>'
            f'<td><a href="{esc(d["url"])}" target="_blank" rel="noopener">{esc(d["scheme"])}</a>'
            f'<div class="muted">{esc(d["organisation"])} · {esc(d["field"])}</div></td>'
            f'<td>{esc(d["countries"])}</td><td>{esc(d["typical_opens"])}</td>'
            f'<td>{esc(d["typical_deadline"])}</td></tr>'
            for d in deadlines)
        dl_section = f"""<section><h2>Recurring schemes — estimated status</h2>
        <div class="muted" style="margin-bottom:10px">Status is <b>estimated</b> from typical past windows (not a live check) — verify on each official page.</div>
        <table><thead><tr><th>Status (est.)</th><th>Scheme</th><th>Countries</th><th>Opens</th><th>Deadline</th></tr></thead>
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
const SC={json.dumps({'EURAXESS':'s-EURAXESS','VHIO':'s-VHIO','la Caixa':'s-laCaixa','AcademicTransfer (NL)':'s-AT','Industry (EURAXESS)':'s-Industry','LinkedIn':'s-LinkedIn','doctorat.gouv.fr':'s-Doctorat'})};
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


def _rows_for(positions, today):
    positions = sorted(positions, key=lambda p: (not p.get("deadline"), p.get("deadline") or ""))
    out = []
    for p in positions:
        out.append({
            "title": p.get("title", ""), "url": p.get("url", ""),
            "org": p.get("organisation") or p.get("host_institution") or "",
            "field": p.get("research_field", ""), "source": p.get("source", ""),
            "country": p.get("country", ""), "open": p.get("open_date", ""),
            "deadline": (p.get("deadline") or "")[:10],
            "deadline_disp": p.get("deadline_display") or (p.get("deadline") or "")[:10],
            "days": _days_left(p.get("deadline"), today),
        })
    return out


def _panel(pid, positions, subtitle):
    import collections
    today = datetime.date.today()
    rows = _rows_for(positions, today)
    sources = list(collections.Counter(r["source"] for r in rows))
    soon = sum(1 for r in rows if r["days"] is not None and 0 <= r["days"] <= 14)
    cards = [(len(rows), "open"), (len(sources), "sources"),
             (len({r["country"] for r in rows if r["country"]}), "countries"),
             (soon, "close ≤14 days")]
    cards_html = "".join(f'<div class="card"><div class="num">{v}</div>'
                         f'<div class="lbl">{esc(l)}</div></div>' for v, l in cards)
    src_opts = "".join(f"<option>{esc(s)}</option>" for s in sources)
    html = f"""<div class="panel" id="p-{pid}">
      <p class="muted" style="margin:4px 0 0">{esc(subtitle)}</p>
      <div class="cards">{cards_html}</div>
      <div class="controls"><input id="q-{pid}" type="search" placeholder="Search…">
      <select id="src-{pid}"><option value="">All sources</option>{src_opts}</select></div>
      <div class="count" id="cnt-{pid}"></div>
      <table id="t-{pid}"><thead><tr><th data-k="title">Position</th><th data-k="source">Source</th>
      <th data-k="country">Country</th><th data-k="open">Opened</th><th data-k="deadline">Deadline</th>
      <th data-k="days">Days left</th></tr></thead><tbody id="tb-{pid}"></tbody></table></div>"""
    return html, rows


def render_combined(sections, deadlines, gen, repo):
    """sections = list of (pid, label, subtitle, positions)."""
    panels, data = [], {}
    tabs = []
    for pid, label, subtitle, positions in sections:
        html, rows = _panel(pid, positions, subtitle)
        panels.append(html)
        data[pid] = rows
        tabs.append(f'<button class="tab" data-pid="{pid}">{esc(label)}'
                    f'<span class="b">{len(rows)}</span></button>')

    # Deadlines panel (static table with estimated status).
    open_now = sum(1 for d in deadlines if d.get("status") == "open")
    drows = "".join(
        f'<tr><td><span class="st st-{esc(d.get("status","check"))}">{esc(d.get("status_label",""))}</span></td>'
        f'<td><a href="{esc(d["url"])}" target="_blank" rel="noopener">{esc(d["scheme"])}</a>'
        f'<div class="muted">{esc(d["organisation"])} · {esc(d["field"])}</div></td>'
        f'<td>{esc(d["countries"])}</td><td>{esc(d["typical_opens"])}</td>'
        f'<td>{esc(d["typical_deadline"])}</td></tr>'
        for d in deadlines)
    panels.append(f"""<div class="panel" id="p-deadlines">
      <p class="muted" style="margin:4px 0 10px"><b>{open_now}</b> likely open now. Status is <b>estimated</b> from typical past windows (not a live check) — verify on each official page.</p>
      <table><thead><tr><th>Status (est.)</th><th>Scheme</th><th>Countries</th><th>Opens</th><th>Deadline</th></tr></thead>
      <tbody>{drows}</tbody></table></div>""")
    tabs.append(f'<button class="tab" data-pid="deadlines">Annual deadlines<span class="b">{len(deadlines)}</span></button>')

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>PhD Scholarships Tracker</title>
<style>{STYLE}</style></head><body><div class="wrap">
<header><h1>PhD Scholarships Tracker — Life Sciences</h1>
<p>All sources in one place · R1 doctoral · 7 countries (ES, FR, UK, DE, IT, NL, CH) · generated {esc(gen)}</p></header>
<div class="tabs">{"".join(tabs)}</div>
{"".join(panels)}
<footer>Auto-updated weekly · <a href="{esc(repo)}">{esc(repo)}</a></footer>
</div><script>
const PANELS={json.dumps(data, ensure_ascii=False)};
const SC={json.dumps({'EURAXESS':'s-EURAXESS','VHIO':'s-VHIO','la Caixa':'s-laCaixa','AcademicTransfer (NL)':'s-AT','Industry (EURAXESS)':'s-Industry','LinkedIn':'s-LinkedIn','doctorat.gouv.fr':'s-Doctorat'})};
const state={{}};
function esc(s){{const d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML;}}
function renderPanel(pid){{const q=document.getElementById('q-'+pid),src=document.getElementById('src-'+pid),
tb=document.getElementById('tb-'+pid),cnt=document.getElementById('cnt-'+pid);
const st=state[pid]||(state[pid]={{sortK:'deadline',dir:1}});
let rows=PANELS[pid].filter(r=>{{const t=(q.value||'').toLowerCase(),sf=src.value;
if(sf&&r.source!==sf)return false;if(!t)return true;
return (r.title+' '+r.country+' '+r.org+' '+r.source+' '+r.field).toLowerCase().includes(t);}});
rows.sort((a,b)=>{{let x=a[st.sortK],y=b[st.sortK];if(st.sortK==='days'){{x=x==null?1e9:x;y=y==null?1e9:y;return (x-y)*st.dir;}}
x=(x||'').toString().toLowerCase();y=(y||'').toString().toLowerCase();return x<y?-st.dir:x>y?st.dir:0;}});
cnt.textContent=rows.length+' shown';
tb.innerHTML=rows.map(r=>{{const u=(r.days!=null&&r.days<=14&&r.days>=0)?' urgent':'';
const dl=r.days==null?'—':(r.days<0?'closed':r.days+'d');const cls=SC[r.source]||'';
return `<tr><td><a href="${{r.url}}" target="_blank" rel="noopener">${{esc(r.title)}}</a>
<div class="muted">${{esc(r.org)}} · ${{esc(r.field)}}</div></td>
<td><span class="pill ${{cls}}">${{esc(r.source)}}</span></td><td>${{esc(r.country)}}</td>
<td class="muted">${{esc(r.open)}}</td><td>${{esc(r.deadline_disp)}}</td>
<td class="days${{u}}">${{dl}}</td></tr>`;}}).join('');}}
Object.keys(PANELS).forEach(pid=>{{const q=document.getElementById('q-'+pid),src=document.getElementById('src-'+pid);
q.oninput=()=>renderPanel(pid);src.onchange=()=>renderPanel(pid);
document.querySelectorAll('#p-'+pid+' th[data-k]').forEach(th=>th.onclick=()=>{{
const st=state[pid]||(state[pid]={{sortK:'deadline',dir:1}});const k=th.dataset.k;
if(k===st.sortK)st.dir*=-1;else{{st.sortK=k;st.dir=1;}}renderPanel(pid);}});renderPanel(pid);}});
const tabs=document.querySelectorAll('.tab'),pans=document.querySelectorAll('.panel');
tabs.forEach(t=>t.onclick=()=>{{tabs.forEach(x=>x.classList.remove('active'));
pans.forEach(x=>x.classList.remove('active'));t.classList.add('active');
document.getElementById('p-'+t.dataset.pid).classList.add('active');}});
tabs[0].classList.add('active');pans[0].classList.add('active');
</script></body></html>"""


def main():
    repo = "https://github.com/jgand3107/msca-doctoral-index"
    gen = datetime.date.today().isoformat()

    t1 = load_positions("msca_doctoral_positions.json")
    html1 = render(t1, "Doctoral Scholarships — Life Sciences",
                   "MSCA/COFUND + VHIO + la Caixa · R1 · 7 countries",
                   gen, deadlines=deadlines_mod.load(), repo_url=repo)
    open(os.path.join(HERE, "msca_report.html"), "w", encoding="utf-8").write(html1)
    print("wrote msca_report.html", len(t1), "positions")

    t3 = load_positions("industry_phd.json")
    html3 = render(t3, "Industry PhD — Life Sciences (Tier 3)",
                   "EURAXESS · PhD positions at companies (Large Enterprise / SME) "
                   "in the 7 countries", gen, repo_url=repo)
    open(os.path.join(HERE, "industry_report.html"), "w", encoding="utf-8").write(html3)
    print("wrote industry_report.html", len(t3), "positions")

    tfr = load_positions("france_biotech_phd.json")
    htmlfr = render(tfr, "France PhD — Montpellier & Lyon (biotech)",
                    "EURAXESS + LinkedIn + doctorat.gouv.fr · Montpellier & Lyon",
                    gen, repo_url=repo)
    open(os.path.join(HERE, "france_report.html"), "w", encoding="utf-8").write(htmlfr)
    print("wrote france_report.html", len(tfr), "positions")

    tcr = load_positions("cancer_centres_radar.json")
    htmlcr = render(tcr, "Cancer-Centre PhD Radar — Spain & France",
                    "Every PhD from the top cancer institutes · doctorat.gouv.fr + EURAXESS + VHIO",
                    gen, repo_url=repo)
    open(os.path.join(HERE, "cancer_radar_report.html"), "w", encoding="utf-8").write(htmlcr)
    print("wrote cancer_radar_report.html", len(tcr), "positions")

    # Combined: all tiers + deadlines in one tabbed document.
    combined = render_combined([
        ("t1", "Tier 1 · Main", "MSCA/COFUND + VHIO + la Caixa · R1 · 7 countries", t1),
        ("t3", "Tier 3 · Industry", "EURAXESS · company PhDs (Large Enterprise / SME)", t3),
        ("fr", "France · MTP/Lyon", "EURAXESS + LinkedIn + doctorat.gouv.fr · biotech PhD in Montpellier & Lyon", tfr),
        ("cr", "Cancer centres", "Every PhD from the top cancer institutes (Spain & France)", tcr),
    ], deadlines_mod.load(), gen, repo)
    open(os.path.join(HERE, "scholarships_report.html"), "w", encoding="utf-8").write(combined)
    print("wrote scholarships_report.html",
          len(t1) + len(t3) + len(tfr) + len(tcr), "positions (all tabs)")


if __name__ == "__main__":
    main()

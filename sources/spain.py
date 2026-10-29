"""
Spain tracker — ALL biotech/life-science PhD vacancies in Spain.

Sources: EURAXESS Spain (R1, life-science) + VHIO (Barcelona oncology, its own
board) + la Caixa INPhINIT tracked calls. `build()` takes pre-fetched data so
run.py can scrape EURAXESS/VHIO once and share.
"""
from __future__ import annotations

from sources import euraxess, lacaixa


def build(eur_records, vhio_records=None, verbose=True):
    out = []
    for r in (eur_records or []):
        if euraxess.is_life_science(r.get("research_field", "")):
            r["source"] = "EURAXESS"
            out.append(r)
    n_eur = len(out)

    v = list(vhio_records or [])
    for r in v:
        r.setdefault("city", "Barcelona")
    out += v

    lc = lacaixa.scrape(verbose=False)
    out += lc

    if verbose:
        print(f"  Spain: {len(out)} life-science PhD "
              f"(EURAXESS {n_eur} + VHIO {len(v)} + la Caixa {len(lc)})")
    return out

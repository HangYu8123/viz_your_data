#!/usr/bin/env python3
"""Render viz/statistics.json (from stats_helpers.write_json) into a self-contained
viz/statistics.html: one card per claim with verdict badge, effect size vs the
recommended minimal effect (forest plot), raw distributions per group, test
tables and assumption checks. Plotly is loaded from cdnjs (pinned); data is
embedded so the page works from disk.

    python build_stats_html.py viz/statistics.json viz/statistics.html
"""
from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path

PLOTLY = "https://cdnjs.cloudflare.com/ajax/libs/plotly.js/3.0.1/plotly.min.js"  # verified to exist on cdnjs
PALETTE = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9"]
BADGE = {"supported": "ok", "significant but below": "warn", "inconclusive": "muted"}


def esc(s) -> str:
    return html.escape(str(s))


def fnum(v, nd=2) -> str:
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "–"
        return f"{float(v):.{nd}f}"
    except Exception:
        return esc(v)


def fp(p) -> str:
    if p is None:
        return "–"
    return "&lt; .001" if p < 0.001 else f"{p:.3f}"


def badge_class(verdict: str) -> str:
    for k, v in BADGE.items():
        if verdict.startswith(k):
            return v
    return "bad"


def tests_table(c: dict) -> str:
    rows = []
    for t in c["tests"]:
        df = t.get("df")
        df = ", ".join(fnum(x, 0) for x in df) if isinstance(df, list) else (fnum(df, 0) if df is not None else "")
        extra = f" (GG ε={fnum(t['gg_epsilon'])}, p<sub>GG</sub>={fp(t['p_gg'])})" if "p_gg" in t else ""
        rows.append(f"<tr><td>{esc(t['name'])}</td><td>{fnum(t['statistic'])}</td><td>{df}</td><td>{fp(t['p'])}</td><td>{fp(t.get('p_adj')) if 'p_adj' in t else '–'}{extra}</td></tr>")
    return f"<table><thead><tr><th>test</th><th>statistic</th><th>df</th><th>p</th><th>p adj.</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"


def desc_table(c: dict) -> str:
    if "descriptives" not in c:
        return ""
    rows = "".join(f"<tr><td>{esc(d['group'])}</td><td>{d['n']}</td><td>{fnum(d['mean'])}</td><td>{fnum(d['sd'])}</td><td>{fnum(d['median'])}</td><td>[{fnum(d['ci95'][0])}, {fnum(d['ci95'][1])}]</td></tr>" for d in c["descriptives"])
    return f"<table><thead><tr><th>group</th><th>n</th><th>mean</th><th>sd</th><th>median</th><th>95% CI</th></tr></thead><tbody>{rows}</tbody></table>"


def assumptions(c: dict) -> str:
    chips = []
    for k, v in c.get("assumptions", {}).items():
        if v is None:
            continue
        if k.endswith("_p"):
            ok = v > 0.05
            chips.append(f"<span class='chip {'ok' if ok else 'warn'}'>{esc(k[:-2])} p={fp(v)} {'✓' if ok else '⚠ use non-parametric'}</span>")
        elif "epsilon" in k:
            chips.append(f"<span class='chip {'ok' if v > 0.75 else 'warn'}'>GG ε={fnum(v)} {'✓' if v > 0.75 else '⚠ sphericity violated; use p_GG'}</span>")
    return " ".join(chips)


def posthoc(c: dict) -> str:
    if not c.get("posthoc"):
        return ""
    rows = "".join(f"<tr><td>{esc(p['pair'][0])} vs {esc(p['pair'][1])}</td><td>{esc(p['test'])}</td><td>{fp(p['p'])}</td><td>{fp(p['p_adj'])}</td><td>{fnum(p['effect'])} ({esc(p['effect_type'])})</td></tr>" for p in c["posthoc"])
    return f"<h4>Post-hoc pairwise (Holm-adjusted)</h4><table><thead><tr><th>pair</th><th>test</th><th>p</th><th>p adj.</th><th>effect</th></tr></thead><tbody>{rows}</tbody></table>"


def sesoi_block(c: dict) -> str:
    s = c["sesoi"]
    raw = f"<br>Author's raw SESOI: {fnum(s['raw_sesoi'])} {esc(c.get('unit',''))} = {fnum(s['raw_sesoi_standardized'])} std" if "raw_sesoi" in s else ""
    return (f"<div class='sesoi'><b>Recommended minimal effect:</b> {fnum(s['recommended'])} ({esc(s['kind'])}, {esc(s['recommended_label'])})"
            f"<br><span class='muted'>basis: {esc(s['basis'])}; MDE at {int(c.get('power',0.8)*100)}% power, α={c.get('alpha',0.05)}: {fnum(s['mde'])} ({esc(s['mde_label'])}){raw}</span></div>")


def card(c: dict, i: int) -> str:
    v = c.get("verdict", "")
    apa_line = c.get("apa", "")
    plots = f"<div class='plots'><div id='eff{i}' class='plot'></div><div id='dist{i}' class='plot'></div></div>"
    return f"""<section class='card' id='{esc(c['id'])}'>
<div class='head'><span class='cid'>{esc(c['id'])}</span><h3>{esc(c['claim'])}</h3><span class='badge {badge_class(v)}'>{esc(v)}</span></div>
<div class='meta'>figure {esc(c.get('figure','–'))} · {esc(c['kind'])} · {esc(c.get('design',''))} · DV: {esc(c.get('dv', c.get('y','')))} {('['+esc(c['unit'])+']') if c.get('unit') else ''}</div>
{('<p class="apa">'+esc(apa_line)+'</p>') if apa_line else ''}
<p class='muted'>{esc(c.get('verdict_note',''))}</p>
{sesoi_block(c)}
{plots}
<div class='grid'><div><h4>Tests</h4>{tests_table(c)}</div><div><h4>Descriptives</h4>{desc_table(c)}</div></div>
{posthoc(c)}
<div class='assump'>{assumptions(c)}</div>
</section>"""


def build(doc: dict, inline_plotly: Path | None = None) -> str:
    claims = doc["claims"]
    for c in claims:
        if "apa" not in c:
            try:
                import stats_helpers as sh  # noqa
                c["apa"] = sh.apa(c)
            except Exception:
                pass
    summary_rows = "".join(
        f"<tr><td><a href='#{esc(c['id'])}'>{esc(c['id'])}</a></td><td>{esc(c['claim'])}</td><td>{esc(c['tests'][0]['name'])}</td>"
        f"<td>{fp(c['tests'][0].get('p_adj', c['tests'][0]['p']))}</td>"
        f"<td>{fnum(c['effect']['value'])} ({esc(c['effect']['type'])})</td><td>{fnum(c['sesoi']['recommended'])}</td>"
        f"<td><span class='badge {badge_class(c.get('verdict',''))}'>{esc(c.get('verdict',''))}</span></td></tr>" for c in claims)
    cards = "\n".join(card(c, i) for i, c in enumerate(claims))
    data = json.dumps(doc).replace("</", "<\\/")
    plotly_tag = (f"<script>{inline_plotly.read_text()}</script>" if inline_plotly else f"<script src='{PLOTLY}'></script>")
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Statistics — {esc(doc.get('study',''))}</title>
{plotly_tag}
<style>
:root{{--bg:#f6f7f9;--panel:#fff;--ink:#1c2330;--muted:#5d6675;--line:#dfe3e8;--ok:#009E73;--warn:#E69F00;--bad:#D55E00;--accent:#0072B2}}
@media(prefers-color-scheme:dark){{:root{{--bg:#14181f;--panel:#1c222b;--ink:#e8ecf1;--muted:#9aa5b3;--line:#2c3540}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:24px}}
h1{{font-size:20px;margin:0 0 4px}} h3{{margin:0;font-size:15px;flex:1}} h4{{margin:14px 0 6px;font-size:13px;color:var(--muted)}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 20px;margin:16px 0}}
.head{{display:flex;align-items:center;gap:10px}} .cid{{font-family:ui-monospace,Menlo,monospace;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:1px 7px}}
.meta{{color:var(--muted);font-size:12.5px;margin:4px 0 8px}} .muted{{color:var(--muted);font-size:12.5px}}
.apa{{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;background:var(--bg);padding:6px 8px;border-radius:6px}}
.badge{{border-radius:12px;padding:2px 10px;font-size:12px;color:#fff;background:var(--bad);white-space:nowrap}}
.badge.ok{{background:var(--ok)}} .badge.warn{{background:var(--warn)}} .badge.muted{{background:var(--muted)}}
.sesoi{{border-left:3px solid var(--accent);padding:6px 10px;margin:8px 0;background:var(--bg);border-radius:0 6px 6px 0}}
.plots{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:10px 0}} .plot{{min-height:240px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} @media(max-width:800px){{.plots,.grid{{grid-template-columns:1fr}}}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}} th,td{{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left}} th{{color:var(--muted);font-weight:600}}
.chip{{display:inline-block;border-radius:12px;padding:1px 8px;font-size:11.5px;margin:2px 4px 0 0;background:var(--bg);border:1px solid var(--line)}}
.chip.ok{{border-color:var(--ok)}} .chip.warn{{border-color:var(--warn)}}
.assump{{margin-top:10px}} a{{color:var(--accent)}}
</style></head><body><main>
<h1>Statistics — {esc(doc.get('study',''))}</h1>
<p class='muted'>α = {doc.get('alpha',0.05)}, target power = {doc.get('power',0.8)}, correction across confirmatory claims: {esc(doc.get('correction','holm'))}. Exploratory (E*) claims are not corrected. Verdicts compare the effect and its 95% CI with the recommended minimal effect (SESOI).</p>
<section class='card'><h4>Summary</h4><table><thead><tr><th>id</th><th>claim</th><th>primary test</th><th>p (adj.)</th><th>effect</th><th>SESOI</th><th>verdict</th></tr></thead><tbody>{summary_rows}</tbody></table>
<div id='forest' class='plot' style='min-height:{max(220, 60*len(claims)+80)}px'></div></section>
{cards}
</main>
<script>
const DOC = {data};
if (typeof Plotly === 'undefined') {{ document.querySelectorAll('.plot').forEach(d => d.innerHTML = "<p class='muted'>Plotly could not be loaded (offline?). Re-run build_stats_html.py with --inline-plotly to embed it.</p>"); throw new Error('Plotly missing'); }}
const PAL = {json.dumps(PALETTE)};
const dark = matchMedia('(prefers-color-scheme: dark)').matches;
const base = {{paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)', font:{{size:12, color: dark?'#e8ecf1':'#1c2330'}}, margin:{{l:50,r:20,t:30,b:40}}}};
// forest plot of standardized effects vs SESOI
(function(){{
  const cs = DOC.claims;
  const y = cs.map(c=>c.id), x = cs.map(c=>c.kind==='anova'? (c.effect.cohen_f||0) : c.effect.value);
  const lo = cs.map(c=>c.effect.ci? c.effect.value-c.effect.ci[0] : 0), hi = cs.map(c=>c.effect.ci? c.effect.ci[1]-c.effect.value : 0);
  const ses = cs.map(c=>c.sesoi.recommended);
  const tr = [{{type:'scatter', mode:'markers', x, y, error_x:{{type:'data', symmetric:false, array:hi, arrayminus:lo, color:'#5d6675'}}, marker:{{size:10, color:PAL[0]}}, name:'effect ± 95% CI', text:cs.map(c=>c.effect.type), hovertemplate:'%{{y}}: %{{x:.2f}} (%{{text}})<extra></extra>'}},
              {{type:'scatter', mode:'markers', x:ses, y, marker:{{symbol:'line-ns-open', size:18, color:PAL[3], line:{{width:2}}}}, name:'recommended minimal effect'}},
              {{type:'scatter', mode:'markers', x:ses.map(s=>-s), y, marker:{{symbol:'line-ns-open', size:18, color:PAL[3], line:{{width:2}}}}, showlegend:false}}];
  Plotly.newPlot('forest', tr, {{...base, title:'Standardized effects vs recommended minimal effect', xaxis:{{title:'d / g / r (pairs, correlations) · f (ANOVA)', zeroline:true}}, yaxis:{{autorange:'reversed'}}, legend:{{orientation:'h', y:-0.25}}}}, {{responsive:true, displaylogo:false}});
}})();
DOC.claims.forEach((c,i)=>{{
  // effect panel
  if (c.kind==='correlation') {{
    const xs=c.points.map(p=>p[0]), ys=c.points.map(p=>p[1]);
    const [mn,mx]=[Math.min(...xs),Math.max(...xs)];
    Plotly.newPlot('eff'+i, [
      {{type:'scatter', mode:'markers', x:xs, y:ys, text:c.points.map(p=>p[2]), marker:{{color:PAL[0], size:8}}, name:'observations', hovertemplate:'%{{text}}<br>%{{x:.2f}}, %{{y:.2f}}<extra></extra>'}},
      {{type:'scatter', mode:'lines', x:[mn,mx], y:[mn*c.effect.slope+c.effect.intercept, mx*c.effect.slope+c.effect.intercept], line:{{color:PAL[3]}}, name:'OLS fit'}}],
      {{...base, title:`r = ${{c.effect.value.toFixed(2)}} [${{c.effect.ci[0].toFixed(2)}}, ${{c.effect.ci[1].toFixed(2)}}]`, xaxis:{{title:c.x}}, yaxis:{{title:c.y}}, showlegend:false}}, {{responsive:true, displaylogo:false}});
    Plotly.newPlot('dist'+i, [{{type:'histogram', x:xs, name:c.x, opacity:.7, marker:{{color:PAL[0]}}}}, {{type:'histogram', x:ys, name:c.y, opacity:.7, marker:{{color:PAL[1]}}}}], {{...base, barmode:'overlay', title:'marginal distributions'}}, {{responsive:true, displaylogo:false}});
    return;
  }}
  const names = Object.keys(c.groups);
  const box = names.map((g,k)=>({{type:'box', y:c.groups[g], name:g, boxpoints:'all', jitter:.4, pointpos:0, marker:{{color:PAL[k%PAL.length], size:5}}, line:{{color:PAL[k%PAL.length]}}, text:(c.subjects||[]), hovertemplate:'%{{text}} %{{y:.2f}}<extra>'+g+'</extra>'}}));
  Plotly.newPlot('dist'+i, box, {{...base, title:`${{c.dv}} by group`, yaxis:{{title:c.unit||c.dv}}, showlegend:false}}, {{responsive:true, displaylogo:false}});
  if (c.kind==='pair' && c.subjects) {{
    const [a,b]=names; const tr=[];
    c.groups[a].forEach((v,k)=>tr.push({{type:'scatter', mode:'lines+markers', x:[a,b], y:[v,c.groups[b][k]], line:{{color:'rgba(93,102,117,.45)', width:1}}, marker:{{size:5, color:PAL[0]}}, hovertext:c.subjects[k], showlegend:false}}));
    Plotly.newPlot('eff'+i, tr, {{...base, title:`paired change, dz = ${{c.effect.value.toFixed(2)}} [${{c.effect.ci[0].toFixed(2)}}, ${{c.effect.ci[1].toFixed(2)}}]`, yaxis:{{title:c.unit||c.dv}}}}, {{responsive:true, displaylogo:false}});
  }} else {{
    const d=c.descriptives;
    Plotly.newPlot('eff'+i, [{{type:'scatter', mode:'markers', x:d.map(r=>r.group), y:d.map(r=>r.mean), error_y:{{type:'data', symmetric:false, array:d.map(r=>r.ci95[1]-r.mean), arrayminus:d.map(r=>r.mean-r.ci95[0])}}, marker:{{size:10, color:PAL[0]}}}}], {{...base, title:'means ± 95% CI', yaxis:{{title:c.unit||c.dv}}}}, {{responsive:true, displaylogo:false}});
  }}
}});
</script></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--inline-plotly", type=Path, help="path to plotly.min.js to embed (self-contained, ~4 MB)")
    a = ap.parse_args()
    doc = json.loads(a.src.read_text())
    a.out.write_text(build(doc, a.inline_plotly))
    print(f"wrote {a.out} ({len(doc['claims'])} claims)")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()

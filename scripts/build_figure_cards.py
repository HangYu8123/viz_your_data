#!/usr/bin/env python3
"""Write viz/figures.md — one card per figure explaining its axes, values, the
claim it supports and why — from the JSON sidecars that ieee_style.save()
writes next to each figure, plus statistics.json when present.

    python build_figure_cards.py viz/figures viz/figures.md [--stats viz/statistics.json] [--chat]

--chat also prints a compact per-figure summary (≤5 lines each) to paste into
the message to the user. Fields the agent must supply through save(meta=...):
claim / hypothesis / reading / values / source / significance; everything about
axes is read from the figure itself so the card cannot drift from the PDF.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_stats(path: Path | None) -> dict:
    if not path or not path.exists():
        return {}
    doc = json.loads(path.read_text())
    return {c["id"]: c for c in doc.get("claims", [])}


def axis_line(a: dict, name: str) -> str:
    lab = a["label"] or "(no label)"
    unit = f" — unit: {a['unit']}" if a["unit"] else ""
    ticks = ", ".join(a["ticks"][:8]) + (" …" if len(a["ticks"]) > 8 else "")
    rng = f"{a['lim'][0]:.3g} to {a['lim'][1]:.3g}"
    scale = f", {a['scale']} scale" if a.get("scale") not in (None, "linear") else ""
    return f"- **{name}:** {lab}{unit}; range {rng}{scale}" + (f"; ticks: {ticks}" if ticks else "")


def sig_line(fig: dict, stats: dict) -> str:
    cid = fig.get("claim")
    c = stats.get(cid) if cid else None
    shown = fig.get("significance", "")
    if not c:
        return f"- **Significance shown:** {shown}" if shown else "- **Significance shown:** none (no statistics for this figure)"
    t = c["tests"][0]
    p = t.get("p_adj", t["p"])
    e = c.get("effect", {})
    ci = e.get("ci")
    eff = f"{e.get('type', 'effect')} = {e.get('value', float('nan')):.2f}" + (f" [{ci[0]:.2f}, {ci[1]:.2f}]" if ci else "")
    ptxt = "p < .001" if p < 0.001 else f"p = {p:.3f}"
    return (f"- **Significance shown:** {shown or 'see statistics.md'} — {t['name']}, {ptxt}"
            f"{' (Holm-adjusted)' if 'p_adj' in t else ''}, {eff}; verdict: {c.get('verdict', '')}")


def card(fig: dict, stats: dict) -> str:
    name = fig["name"]
    cid = fig.get("claim", "")
    hyp = fig.get("hypothesis", "")
    lines = [f"## {name}" + (f" — {cid}" if cid else ""), ""]
    files = [Path(f).name for f in fig.get("files", [])]
    lines.append(f"**File:** `{files[0] if files else name + '.pdf'}` · **width:** {fig.get('kind', '?')} ({fig.get('width_in')} × {fig.get('height_in')} in)")
    if hyp:
        lines.append(f"**Claim ({cid}):** {hyp}")
    lines.append("")
    lines.append("**What the axes mean**")
    for i, a in enumerate(fig.get("axes", [])):
        panel = f" (panel {i + 1}{': ' + a['title'] if a.get('title') else ''})" if len(fig["axes"]) > 1 else ""
        lines.append(f"- Panel{panel}:" if panel else "- Single panel:")
        lines.append("  " + axis_line(a["x"], "x"))
        lines.append("  " + axis_line(a["y"], "y"))
        if a.get("legend"):
            lines.append(f"  - legend / series: {', '.join(a['legend'])}")
        if a.get("annotations"):
            ann = [t for t in a["annotations"] if not t.replace('.', '', 1).replace('-', '', 1).isdigit()]
            if ann:
                lines.append(f"  - annotations: {'; '.join(ann[:6])}")
    lines.append("")
    lines.append("**What the values are**")
    lines.append(f"- {fig.get('values', '(fill in: aggregation level, error bar type, n)')}")
    if fig.get("source"):
        lines.append(f"- source: {fig['source']}")
    lines.append(sig_line(fig, stats))
    lines.append("")
    lines.append("**How to read it / why it supports the claim**")
    lines.append(f"- {fig.get('reading', '(fill in: what the reader should conclude and which visual feature shows it)')}")
    if fig.get("caveats"):
        lines.append(f"- caveats: {fig['caveats']}")
    lines.append("")
    return "\n".join(lines)


def chat_summary(fig: dict, stats: dict) -> str:
    ax = fig["axes"][0] if fig.get("axes") else {"x": {"label": "?"}, "y": {"label": "?"}}
    cid = fig.get("claim", "")
    c = stats.get(cid) if cid else None
    sig = ""
    if c:
        t = c["tests"][0]; p = t.get("p_adj", t["p"]); e = c.get("effect", {})
        sig = f"; {t['name']} {'p < .001' if p < 0.001 else f'p = {p:.3f}'}, {e.get('type','')} = {e.get('value', 0):.2f} → {c.get('verdict','')}"
    return "\n".join([
        f"**{fig['name']}** ({fig.get('kind', '?')} width){' — ' + cid if cid else ''}",
        f"- x: {ax['x']['label'] or '?'}; y: {ax['y']['label'] or '?'}",
        f"- values: {fig.get('values', '?')}{sig}",
        f"- supports {cid or 'no claim'}: {fig.get('reading', '?')}",
    ])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("figdir", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--stats", type=Path)
    ap.add_argument("--chat", action="store_true")
    a = ap.parse_args()
    stats = load_stats(a.stats)
    figs = [json.loads(p.read_text()) for p in sorted(a.figdir.glob("*.json"))]
    if not figs:
        raise SystemExit(f"no figure sidecars (*.json) in {a.figdir}; save figures with ieee_style.save(..., meta=...)")
    head = ["# Figures — axes, values and claims", "",
            "Each card documents what x and y are (with units and ranges, read from the figure itself), what the plotted values are, "
            "which claim the figure supports and why, and which significance result is shown. Regenerate with build_figure_cards.py after any change.", "",
            "| figure | claim | width | x | y | verdict |", "|---|---|---|---|---|---|"]
    for f in figs:
        ax = f["axes"][0] if f.get("axes") else {"x": {"label": ""}, "y": {"label": ""}}
        c = stats.get(f.get("claim", ""), {})
        head.append(f"| {f['name']} | {f.get('claim', '')} | {f.get('kind', '')} | {ax['x']['label']} | {ax['y']['label']} | {c.get('verdict', '')} |")
    body = "\n".join(head) + "\n\n" + "\n".join(card(f, stats) for f in figs)
    a.out.write_text(body)
    print(f"wrote {a.out} ({len(figs)} figures)")
    if a.chat:
        print("\n--- chat summary ---\n")
        print("\n\n".join(chat_summary(f, stats) for f in figs))


if __name__ == "__main__":
    main()

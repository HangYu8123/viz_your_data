"""IEEE-sized matplotlib figures that drop straight into a two-column paper.

Usage (inside the notebook, after copying this file next to it):

    import ieee_style as st
    f, ax = st.fig("single")            # 3.5 in wide, default height
    ax.bar(...)
    st.save(f, "F1_interventions")      # -> figures/F1_interventions.pdf + .png

    f, axes = st.fig("double", height=2.4, ncols=3, sharey=True)

Widths are IEEE's official column widths, so in LaTeX
    \\includegraphics[width=\\columnwidth]{F1_interventions.pdf}   (single)
    \\includegraphics[width=\\textwidth]{F2_timeline.pdf}          (double)
render at exactly the size they were designed at, with 8 pt text.
"""
from __future__ import annotations

import os
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

# ---- widths (inches) -------------------------------------------------------
SINGLE = 3.5     # IEEE one-column (\columnwidth = 3.5 in = 21.2 pc)
DOUBLE = 7.16    # IEEE two-column (\textwidth = 7.16 in)
WIDTHS = {"single": SINGLE, "double": DOUBLE}

# Default heights as a fraction of width; override with height=... in fig().
DEFAULT_ASPECT = {"single": 0.66, "double": 0.38}

# ---- Okabe–Ito colorblind-safe palette ------------------------------------
PALETTE = [
    "#0072B2",  # blue
    "#E69F00",  # orange
    "#009E73",  # green
    "#D55E00",  # vermillion
    "#CC79A7",  # purple
    "#56B4E9",  # sky blue
    "#F0E442",  # yellow
    "#000000",  # black
]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
LINESTYLES = ["-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1))]
HATCHES = ["", "//", "..", "xx", "\\\\", "++"]

# ---- reference palettes (see references/styles/README.md) ----------------
PALETTES = {
    "okabe_ito": PALETTE,
    # ROSETTA Fig. 4: pastel fills with black edges; first = method of interest
    "rosetta": ["#77aadd", "#ef8866", "#eddd87", "#fda9ba", "#9dc0e4", "#c6a599"],
    # ROSETTA Fig. 5: two attribute families on a light-gray absent cell
    "rosetta_binary": ["#ef9373", "#83b1e0", "#ebeff0"],
    # DeepSeek-V3 Fig. 1: royal-blue hero (hatch it), own-previous tint, open (grays), closed (beiges)
    "deepseek": ["#4b69fe", "#abc0ff", "#b9bab9", "#d0d0d0", "#e8d2a0", "#f3e6c8"],
    # DeepSeek-R1 Fig. 2 pipeline roles: models, prompts, rewards, training algo, prompts+responses, post-processing
    "deepseek_roles": ["#c2a5f7", "#b3c6e7", "#8da8db", "#4572c4", "#aeb8c6", "#6c6c6d"],
    # Cambrian-S Fig. 2: neutral raw, positive, negative
    "cambrian_s": ["#dddedd", "#bbd7f1", "#feaf6d"],
    # Cosmos 3 Fig. 6 modality label colors (language, video, audio, action); use tint() for fills
    "cosmos3_modality": ["#1a1a8c", "#bb694a", "#6e2c6b", "#2e6b3a"],
    # Cosmos 3 Fig. 7 donut categories
    "cosmos3_categorical": ["#6ca066", "#257fae", "#e4b027", "#946ea3", "#498e97", "#c36868", "#d48532"],
    # Memory Anchors: teal (new / proposed), orange (old / baseline), then gray ramp for ablation strength
    "memory_anchors": ["#5a8e7d", "#f4a258", "#8db0a5", "#6c7b77", "#545556", "#fad0a9"],
    # Memory Anchors Fig. 7 success-count sequential map (dark -> light)
    "memory_anchors_seq": ["#222c5d", "#2267a9", "#95c4d6", "#e0dcb5", "#fbf9d0"],
}

# rc tweaks that reproduce the typographic / grid conventions of a reference paper
PRESETS = {
    "deepseek": {"font.family": "serif", "font.weight": "bold", "axes.labelweight": "bold",
                 "axes.grid": True, "axes.grid.axis": "y", "grid.linestyle": "--", "grid.alpha": 0.5,
                 "legend.loc": "upper center", "hatch.linewidth": 0.6},
    "rosetta": {"font.family": "serif", "axes.grid": True, "axes.grid.axis": "y", "grid.linestyle": ":",
                "grid.alpha": 0.6, "axes.spines.top": True, "axes.spines.right": True, "legend.frameon": True},
    "cambrian_s": {"font.family": "sans-serif", "axes.grid": False, "axes.titlelocation": "left",
                   "axes.titleweight": "normal"},
    "cosmos3": {"font.family": "serif", "axes.grid": False},
    "memory_anchors": {"font.family": "sans-serif", "axes.grid": False, "axes.titleweight": "bold",
                       "errorbar.capsize": 2},
}


def use_palette(name: str) -> list[str]:
    """Set the color cycle to a reference palette (see PALETTES) and return it."""
    cols = PALETTES[name]
    mpl.rcParams["axes.prop_cycle"] = mpl.cycler(color=cols)
    return cols


def apply_preset(name: str, font_size: float = 8.0) -> None:
    """Re-apply base rc params then overlay a reference paper's conventions."""
    apply_rc(font_size)
    mpl.rcParams.update(PRESETS[name])


def tint(color: str, amount: float = 0.2) -> str:
    """Mix `color` with white: amount=0.2 keeps 20% of the color (Cosmos-3-style fills)."""
    r, g, b = mpl.colors.to_rgb(color)
    return mpl.colors.to_hex((1 - amount + amount * r, 1 - amount + amount * g, 1 - amount + amount * b))


def ramp(color: str, n: int = 3, lo: float = 0.35, hi: float = 1.0) -> list[str]:
    """n tints of one hue from light to full (Memory-Anchors-style ablation strength)."""
    import numpy as _np
    return [tint(color, a) for a in _np.linspace(lo, hi, n)]


OUT_DIR = Path(os.environ.get("VIZ_FIG_DIR", "figures"))
PNG_DPI = 200


def apply_rc(font_size: float = 8.0) -> None:
    """Publication rc params. 8 pt matches IEEE caption size; ticks slightly smaller."""
    mpl.rcParams.update({
        "figure.dpi": 110,                 # on-screen only; PDF is vector
        "savefig.dpi": PNG_DPI,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": font_size,
        "axes.titlesize": font_size,
        "axes.labelsize": font_size,
        "xtick.labelsize": font_size - 1,
        "ytick.labelsize": font_size - 1,
        "legend.fontsize": font_size - 1,
        "legend.title_fontsize": font_size - 1,
        "legend.frameon": False,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "lines.linewidth": 1.0,
        "lines.markersize": 3.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": mpl.cycler(color=PALETTE),
        "pdf.fonttype": 42,                # TrueType: text stays editable/searchable
        "ps.fonttype": 42,
        "figure.constrained_layout.use": True,
        "axes.grid": False,
    })


apply_rc()


def fig(kind: str = "single", height: float | None = None, **subplots_kw):
    """Create a figure at an IEEE width. `kind` is 'single' or 'double'.

    Extra kwargs go to plt.subplots (nrows, ncols, sharex, sharey, gridspec_kw...).
    """
    if kind not in WIDTHS:
        raise ValueError(f"kind must be one of {list(WIDTHS)}, got {kind!r}")
    w = WIDTHS[kind]
    h = height if height is not None else w * DEFAULT_ASPECT[kind]
    return plt.subplots(figsize=(w, h), **subplots_kw)


def save(figure, name: str, out_dir: Path | str | None = None, png: bool = True,
         formats=("pdf",), meta: dict | None = None, check: bool = True) -> list[Path]:
    """Save `figure` as PDF (+ PNG preview) without changing its size, plus a JSON
    sidecar (`<name>.json`) describing every axes (labels, units, limits, ticks,
    legend) merged with `meta` — the input for build_figure_cards.py.

    `meta` should carry what cannot be read from the axes: {"claim": "H1",
    "hypothesis": "...", "reading": "why this figure supports/refutes the claim",
    "values": "per-participant means, 95% CI, n=12", "source": "trials.parquet: condition, interventions",
    "significance": "paired t, Holm p shown as stars"}.

    bbox_inches is deliberately *not* 'tight': tight cropping changes the final
    width, which defeats the purpose of designing at column width. Use
    constrained_layout (enabled by default) to keep labels inside the canvas.
    """
    import json
    out = Path(out_dir) if out_dir is not None else OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    if check:
        for w in check_axes(figure, name):
            print(f"  WARNING {w}")
    paths = []
    for ext in formats:
        p = out / f"{name}.{ext}"
        figure.savefig(p, format=ext)
        paths.append(p)
    if png:
        p = out / f"{name}.png"
        figure.savefig(p, dpi=PNG_DPI)
        paths.append(p)
    w, h = figure.get_size_inches()
    side = {"name": name, "width_in": round(float(w), 2), "height_in": round(float(h), 2),
            "kind": "single" if abs(w - SINGLE) < 0.02 else "double" if abs(w - DOUBLE) < 0.02 else "custom",
            "files": [str(p) for p in paths], "axes": describe_axes(figure), **(meta or {})}
    (out / f"{name}.json").write_text(json.dumps(side, indent=1, default=str))
    print(f"saved {name}: {w:.2f} x {h:.2f} in -> {', '.join(str(p) for p in paths)}")
    return paths


def describe_axes(figure) -> list[dict]:
    """Machine-readable description of each axes: what x and y are, their units,
    ranges, tick labels and legend entries (used for figures.md and for checks)."""
    out = []
    for i, ax in enumerate(figure.get_axes()):
        if not ax.get_visible() or getattr(ax, "_colorbar", None) is not None or ax.get_label() == "<colorbar>":
            continue
        handles, labels = ax.get_legend_handles_labels()
        out.append({
            "index": i, "title": ax.get_title(),
            "x": {"label": ax.get_xlabel(), "unit": _unit(ax.get_xlabel()), "lim": [float(v) for v in ax.get_xlim()],
                  "ticks": [t.get_text() for t in ax.get_xticklabels() if t.get_text()][:20], "scale": ax.get_xscale()},
            "y": {"label": ax.get_ylabel(), "unit": _unit(ax.get_ylabel()), "lim": [float(v) for v in ax.get_ylim()],
                  "ticks": [t.get_text() for t in ax.get_yticklabels() if t.get_text()][:20], "scale": ax.get_yscale()},
            "legend": labels[:12], "n_bars": len(ax.patches), "n_lines": len(ax.lines),
            "annotations": [t.get_text() for t in ax.texts if t.get_text()][:30],
        })
    return out


def _unit(label: str) -> str:
    import re
    m = re.search(r"\[([^\]]+)\]", label or "")  # the [bracketed] part is the unit; "(lower is better)" is not
    return m.group(1) if m else ""


def check_axes(figure, name: str = "") -> list[str]:
    """Return warnings for axes with missing labels or units. Every axes should
    say what x and y are and in which unit — a reader must never guess."""
    warns = []
    axes = [a for a in figure.get_axes() if a.get_visible() and a.get_label() != "<colorbar>"]
    for i, ax in enumerate(axes):
        tag = f"{name} axes[{i}]"
        xl, yl = ax.get_xlabel(), ax.get_ylabel()
        shared_x = len(axes) > 1 and any(a is not ax and a.get_xlabel() for a in axes) and ax.get_subplotspec() is not None and not ax.get_subplotspec().is_last_row()
        shared_y = len(axes) > 1 and any(a is not ax and a.get_ylabel() for a in axes) and ax.get_subplotspec() is not None and not ax.get_subplotspec().is_first_col()
        if not xl and not shared_x:
            warns.append(f"{tag}: no x-axis label")
        if not yl and not shared_y:
            warns.append(f"{tag}: no y-axis label")
        if yl and not _unit(yl) and not any(k in yl.lower() for k in ("count", "rate", "%", "score", "ratio", "n ", "number", "accuracy", "index")):
            warns.append(f"{tag}: y label '{yl}' has no unit in [] — add one or state it is unitless")
        if ax.patches and len(ax.patches) <= 30 and not any(t.get_text().replace('.', '', 1).replace('-', '', 1).isdigit() for t in ax.texts):
            warns.append(f"{tag}: bars without value labels — add st.value_labels(ax, rects) if the numbers matter")
    return warns


def label_axes(ax, x: str | None = None, y: str | None = None, xunit: str = "", yunit: str = "",
               direction: str = "") -> None:
    """Set axis labels in the house format 'Quantity [unit]' (+ optional
    '(lower is better)'), so units are never forgotten."""
    if x is not None:
        ax.set_xlabel(f"{x} [{xunit}]" if xunit else x)
    if y is not None:
        lab = f"{y} [{yunit}]" if yunit else y
        if direction:
            lab += f" ({direction})"
        ax.set_ylabel(lab)


def value_labels(ax, rects, fmt: str = "%.2f", fontsize: float | None = None, **kw) -> None:
    """Print the value on top of each bar (DeepSeek / Memory Anchors convention)."""
    ax.bar_label(rects, fmt=fmt, fontsize=fontsize or mpl.rcParams["font.size"] - 2, padding=1.5, **kw)


# ---- significance annotations --------------------------------------------

def p_to_stars(p: float, ns: str = "n.s.") -> str:
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ns


def fmt_p(p: float) -> str:
    return "p < .001" if p < 0.001 else f"p = {p:.3f}".replace("0.", ".", 1)


def sig_text(claim: dict, mode: str = "stars+effect") -> str:
    """Text for a bracket from a stats_helpers claim block: uses the adjusted p
    when present. mode: 'stars' | 'p' | 'stars+effect' | 'p+effect' | 'full'."""
    t = claim["tests"][0]
    p = t.get("p_adj", t["p"])
    e = claim.get("effect", {})
    sym = {"cohen_dz": "d", "hedges_g": "g", "eta2": "η²", "partial_eta2": "ηp²", "r": "r"}.get(e.get("type"), "")
    eff = f"{sym} = {e['value']:.2f}" if sym and "value" in e else ""
    if mode == "stars":
        return p_to_stars(p)
    if mode == "p":
        return fmt_p(p)
    if mode == "stars+effect":
        return f"{p_to_stars(p)}  {eff}".strip()
    if mode == "p+effect":
        return f"{fmt_p(p)}, {eff}".strip(", ")
    return f"{t['name']}: {fmt_p(p)}, {eff}".strip(", ")


def sig_bracket(ax, x1: float, x2: float, y: float | None = None, text: str = "", h: float | None = None,
                lw: float = 0.6, color: str = "k", fontsize: float | None = None) -> float:
    """Draw a significance bracket between x1 and x2 at height y (data units)
    with `text` above it. Returns the top y so brackets can be stacked."""
    ylo, yhi = ax.get_ylim()
    rng = yhi - ylo
    if y is None:
        y = ax.dataLim.y1 + 0.06 * rng
    h = h if h is not None else 0.025 * rng
    ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], lw=lw, color=color, clip_on=False, solid_capstyle="butt")
    ax.text((x1 + x2) / 2, y + h + 0.01 * rng, text, ha="center", va="bottom",
            fontsize=fontsize or mpl.rcParams["font.size"] - 1, color=color)
    top = y + h + 0.09 * rng
    if top > yhi:
        ax.set_ylim(ylo, top)
    return y + h + 0.06 * rng


def annotate_sig(ax, claim: dict, x1: float, x2: float, y: float | None = None,
                 mode: str = "stars+effect", **kw) -> float:
    """One call to show a test result on the plot: bracket between the two
    compared positions with stars / p and the effect size. For ANOVA claims use
    claim['posthoc'] entries (each has 'pair', 'p_adj', 'effect') via annotate_posthoc."""
    return sig_bracket(ax, x1, x2, y, sig_text(claim, mode), **kw)


def annotate_posthoc(ax, claim: dict, positions: dict, mode: str = "stars", only_sig: bool = True, **kw) -> None:
    """Stack brackets for every post-hoc pair of an ANOVA claim. `positions`
    maps level name -> x position. Non-significant pairs are skipped unless only_sig=False."""
    y = None
    pairs = sorted(claim.get("posthoc", []), key=lambda p: abs(positions[p["pair"][0]] - positions[p["pair"][1]]))
    for ph in pairs:
        if only_sig and ph["p_adj"] >= 0.05:
            continue
        sym = "d" if ph.get("effect_type") == "cohen_dz" else "g"
        txt = p_to_stars(ph["p_adj"]) if mode == "stars" else fmt_p(ph["p_adj"])
        if mode.endswith("+effect"):
            txt = f"{p_to_stars(ph['p_adj'])}  {sym} = {ph['effect']:.2f}"
        y = sig_bracket(ax, positions[ph["pair"][0]], positions[ph["pair"][1]], y, txt, **kw)


def stats_footer(ax, claim: dict, loc: str = "upper left") -> None:
    """Small text box with the full test line (for figures where a bracket
    does not fit, e.g. correlations): 'Pearson r = .62 [.08, .88], p = .031'."""
    t = claim["tests"][0]; e = claim.get("effect", {})
    ci = e.get("ci")
    sym = {"cohen_dz": "d", "hedges_g": "g", "r": "r", "eta2": "η²", "partial_eta2": "ηp²"}.get(e.get("type"), "effect")
    txt = f"{t['name']}: {fmt_p(t.get('p_adj', t['p']))}; {sym} = {e.get('value', float('nan')):.2f}"
    if ci:
        txt += f" [{ci[0]:.2f}, {ci[1]:.2f}]"
    x, ha = (0.02, "left") if "left" in loc else (0.98, "right")
    y, va = (0.98, "top") if "upper" in loc else (0.02, "bottom")
    ax.text(x, y, txt, transform=ax.transAxes, ha=ha, va=va, fontsize=mpl.rcParams["font.size"] - 1.5,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#cccccc", lw=0.5))


def check_widths(out_dir: Path | str | None = None) -> None:
    """Print every PDF in the figure dir with its width, flagging non-IEEE sizes."""
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover
        print("pip install pypdf to verify PDF widths")
        return
    out = Path(out_dir) if out_dir is not None else OUT_DIR
    for p in sorted(out.glob("*.pdf")):
        box = PdfReader(str(p)).pages[0].mediabox
        w_in, h_in = float(box.width) / 72, float(box.height) / 72
        ok = any(abs(w_in - w) < 0.02 for w in WIDTHS.values())
        print(f"{'OK ' if ok else 'BAD'} {p.name}: {w_in:.2f} x {h_in:.2f} in")


def style_for(i: int) -> dict:
    """Consistent color+marker+linestyle for series index i (so conditions look
    the same across every figure and survive grayscale printing)."""
    return {
        "color": PALETTE[i % len(PALETTE)],
        "marker": MARKERS[i % len(MARKERS)],
        "linestyle": LINESTYLES[i % len(LINESTYLES)],
    }

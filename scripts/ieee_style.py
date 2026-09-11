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
         formats=("pdf",)) -> list[Path]:
    """Save `figure` as PDF (+ PNG preview) without changing its size.

    bbox_inches is deliberately *not* 'tight': tight cropping changes the final
    width, which defeats the purpose of designing at column width. Use
    constrained_layout (enabled by default) to keep labels inside the canvas.
    """
    out = Path(out_dir) if out_dir is not None else OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
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
    print(f"saved {name}: {w:.2f} x {h:.2f} in -> {', '.join(str(p) for p in paths)}")
    return paths


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

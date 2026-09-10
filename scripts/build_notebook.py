#!/usr/bin/env python3
"""Build a .ipynb from a simple Python spec so you never hand-edit notebook JSON.

Spec file: a Python module defining `CELLS`, a list of ("markdown"|"code", source)
tuples, e.g.

    CELLS = [
        ("markdown", "# Study X — figures\\n\\n| id | hypothesis |..."),
        ("code", "import ieee_style as st\\nfrom parse import load_all\\ndf = load_all()"),
        ("markdown", "## F1 — H1: interventions by condition"),
        ("code", "f, ax = st.fig('single')\\n...\\nst.save(f, 'F1_interventions')"),
    ]

Usage:
    python build_notebook.py spec.py viz/figures.ipynb [--execute]

--execute runs the notebook in place (needs nbconvert + ipykernel); if they are not
installed it falls back to executing the code cells sequentially with exec() in a
shared namespace, which is enough to generate the figure files but does not embed
outputs in the notebook.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook


def load_spec(path: Path):
    spec = importlib.util.spec_from_file_location("nb_spec", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    cells = getattr(mod, "CELLS", None)
    if not cells:
        sys.exit(f"{path} must define a non-empty CELLS list")
    return cells


def build(cells, out: Path) -> None:
    nb = new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    for kind, src in cells:
        if kind == "markdown":
            nb.cells.append(new_markdown_cell(src))
        elif kind == "code":
            nb.cells.append(new_code_cell(src))
        else:
            sys.exit(f"unknown cell kind {kind!r}")
    out.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, out)
    print(f"wrote {out} ({len(nb.cells)} cells)")


def execute(out: Path) -> None:
    try:
        import nbconvert  # noqa: F401
        subprocess.run(
            [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook",
             "--execute", "--inplace", str(out)],
            check=True, cwd=out.parent,
        )
        print(f"executed {out} in place")
        return
    except (ImportError, subprocess.CalledProcessError) as e:
        print(f"nbconvert unavailable or failed ({e}); falling back to exec()")
    nb = nbformat.read(out, as_version=4)
    ns: dict = {"__name__": "__main__"}
    cwd = os.getcwd()
    os.chdir(out.parent)
    sys.path.insert(0, str(out.parent))
    try:
        for i, cell in enumerate(nb.cells):
            if cell.cell_type != "code":
                continue
            print(f"--- cell {i} ---")
            exec(compile(cell.source, f"<cell {i}>", "exec"), ns)
    finally:
        os.chdir(cwd)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path, help="python file defining CELLS")
    ap.add_argument("out", type=Path, help="output .ipynb path")
    ap.add_argument("--execute", action="store_true", help="run the notebook after writing it")
    a = ap.parse_args()
    build(load_spec(a.spec), a.out)
    if a.execute:
        execute(a.out)


if __name__ == "__main__":
    main()

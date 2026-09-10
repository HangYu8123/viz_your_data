#!/usr/bin/env python3
"""Install or upgrade every library the viz_results workflow needs.

    python setup_env.py            # install missing, upgrade outdated
    python setup_env.py --check    # report only, change nothing
    python setup_env.py --no-upgrade   # install missing only

Uses the *current* interpreter's pip so the notebook kernel and the parsers see
the same packages. Registers an ipykernel named "viz_results" so Jupyter / VS
Code can pick it.
"""
from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys

# (pip name, import name, why)
PACKAGES = [
    ("matplotlib", "matplotlib", "figures"),
    ("seaborn", "seaborn", "box/violin/strip helpers"),
    ("numpy", "numpy", "arrays"),
    ("pandas", "pandas", "tidy tables"),
    ("scipy", "scipy", "stats tests / CIs"),
    ("pyarrow", "pyarrow", "parquet cache for parsed data"),
    ("nbformat", "nbformat", "build notebooks"),
    ("nbconvert", "nbconvert", "execute notebooks headlessly"),
    ("ipykernel", "ipykernel", "notebook kernel"),
    ("jupyter", "jupyter", "jupyter CLI"),
    ("pypdf", "pypdf", "verify exported PDF widths"),
    ("plotly", "plotly", "interactive HTML report"),
    ("statsmodels", "statsmodels", "mixed models / extra tests (optional; helpers are scipy-only)"),
]


def installed_version(mod: str) -> str | None:
    try:
        m = importlib.import_module(mod)
    except Exception:
        return None
    return getattr(m, "__version__", "?")


def outdated() -> set[str]:
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
            capture_output=True, text=True, check=True, timeout=180,
        ).stdout
        return {p["name"].lower() for p in json.loads(out)}
    except Exception as e:  # pip index unreachable etc.
        print(f"(could not query outdated packages: {e})")
        return set()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-upgrade", action="store_true")
    a = ap.parse_args()

    print(f"python: {sys.executable} ({sys.version.split()[0]})")
    missing, present = [], []
    for pip_name, mod, why in PACKAGES:
        v = installed_version(mod)
        (present if v else missing).append(pip_name)
        print(f"  {'ok     ' if v else 'MISSING'} {pip_name:<12} {v or '':<10} {why}")

    stale = set() if a.no_upgrade else outdated() & {p.lower() for p in present}
    if stale:
        print(f"outdated: {', '.join(sorted(stale))}")

    if a.check:
        return
    to_install = missing + sorted(stale)
    if not to_install:
        print("nothing to install")
    else:
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", *to_install]
        print("running:", " ".join(cmd))
        subprocess.run(cmd, check=True)

    # kernel registration is idempotent
    try:
        subprocess.run([sys.executable, "-m", "ipykernel", "install", "--user",
                        "--name", "viz_results", "--display-name", "Python (viz_results)"],
                       check=True, capture_output=True)
        print("kernel 'viz_results' registered")
    except Exception as e:
        print(f"(kernel registration skipped: {e})")


if __name__ == "__main__":
    main()

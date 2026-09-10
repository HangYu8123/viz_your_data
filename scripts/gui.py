#!/usr/bin/env python3
"""Local web GUI that writes viz/goal.md, viz/data.md and viz/config.json.

    python gui.py --project /path/to/study        # opens http://127.0.0.1:8765
    python gui.py --project . --port 9000 --no-browser

Stdlib only. The page lets the user (1) describe file types to parse and pick
one example file per type from a directory browser, (2) fill goal.md fields or
paste text from their paper, (3) toggle the researcher / diversifier agents and
choose backend (claude / codex), model and effort. Save writes the three files
into <project>/viz/. All paths are confined to the project directory.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import threading
import webbrowser
from collections import Counter, defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
INDEX = HERE.parent / "gui" / "index.html"
TEMPLATES = HERE.parent / "templates"
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".claude", ".codex", "viz"}
TEXT_EXT = {".csv", ".tsv", ".txt", ".json", ".yaml", ".yml", ".md", ".log", ".py", ".jsonl"}

PROJECT = Path(".").resolve()
VIZ_DIRNAME = "viz"


def safe(rel: str) -> Path:
    p = (PROJECT / rel).resolve() if rel else PROJECT
    if PROJECT != p and PROJECT not in p.parents:
        raise PermissionError(f"path outside project: {rel}")
    return p


def api_ls(rel: str):
    p = safe(rel)
    entries = []
    for c in sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower())):
        if c.name.startswith(".") and c.is_dir():
            continue
        try:
            size = c.stat().st_size if c.is_file() else None
        except OSError:
            size = None
        entries.append({"name": c.name, "dir": c.is_dir(), "size": size,
                        "rel": str(c.relative_to(PROJECT))})
    return {"rel": str(p.relative_to(PROJECT)) if p != PROJECT else "", "entries": entries[:2000]}


def api_preview(rel: str):
    p = safe(rel)
    size = p.stat().st_size
    if p.suffix.lower() in TEXT_EXT and size < 5_000_000:
        with p.open("r", errors="replace") as f:
            head = "".join([next(f, "") for _ in range(40)])
        return {"kind": "text", "size": size, "head": head[:6000]}
    if p.is_dir():
        return {"kind": "dir", "entries": [c.name for c in list(p.iterdir())[:50]]}
    return {"kind": "binary", "size": size}


def api_detect():
    """Summarize file types under the project: ext -> count, example, dir depth pattern."""
    counts: Counter = Counter()
    example: dict[str, str] = {}
    dirs: dict[str, Counter] = defaultdict(Counter)
    for root, dnames, fnames in os.walk(PROJECT):
        dnames[:] = [d for d in dnames if d not in SKIP_DIRS and not d.startswith(".")]
        rroot = Path(root).relative_to(PROJECT)
        for f in fnames:
            if f.startswith("."):
                continue
            ext = Path(f).suffix.lower() or "(no ext)"
            counts[ext] += 1
            example.setdefault(ext, str(rroot / f))
            # generalize numeric / timestamp path parts to a pattern
            pat = re.sub(r"\d{8}_\d{6}", "<YYYYMMDD_HHMMSS>", str(rroot / f))
            pat = re.sub(r"(?<![A-Za-z])\d+(?![A-Za-z])", "<n>", pat)
            dirs[ext][pat] += 1
    types = []
    for ext, n in counts.most_common():
        pat, _ = dirs[ext].most_common(1)[0]
        types.append({"ext": ext, "count": n, "example": example[ext], "pattern": pat})
    return {"types": types, "project": str(PROJECT)}


def api_state():
    viz = PROJECT / VIZ_DIRNAME
    def rd(name, tmpl):
        p = viz / name
        return {"exists": p.exists(), "text": p.read_text() if p.exists() else (TEMPLATES / tmpl).read_text()}
    return {"project": str(PROJECT), "viz_dir": str(viz),
            "goal": rd("goal.md", "goal.md"), "data": rd("data.md", "data.md"),
            "config": rd("config.json", "config.json")}


def api_save(body: dict):
    viz = PROJECT / VIZ_DIRNAME
    viz.mkdir(parents=True, exist_ok=True)
    written = []
    for name in ("goal.md", "data.md", "config.json"):
        key = name.split(".")[0]
        if key in body and body[key] is not None:
            (viz / name).write_text(body[key])
            written.append(str(viz / name))
    return {"written": written}


class H(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                data = INDEX.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif u.path == "/api/state":
                self._json(api_state())
            elif u.path == "/api/ls":
                self._json(api_ls(q.get("path", "")))
            elif u.path == "/api/preview":
                self._json(api_preview(q["path"]))
            elif u.path == "/api/detect":
                self._json(api_detect())
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:  # noqa: BLE001
            self._json({"error": str(e)}, 400)

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        try:
            if u.path == "/api/save":
                self._json(api_save(body))
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:  # noqa: BLE001
            self._json({"error": str(e)}, 400)

    def log_message(self, fmt, *args):  # quieter
        if "/api/" not in (args[0] if args else ""):
            return


def main() -> None:
    global PROJECT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="study root (data lives under it; viz/ is written here)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    PROJECT = Path(a.project).resolve()
    if not PROJECT.is_dir():
        raise SystemExit(f"not a directory: {PROJECT}")
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    url = f"http://127.0.0.1:{a.port}/"
    print(f"viz_results GUI for {PROJECT}\n  {url}\n  writes -> {PROJECT / VIZ_DIRNAME}/  (Ctrl-C to stop)")
    if not a.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

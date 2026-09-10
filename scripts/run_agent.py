#!/usr/bin/env python3
"""Run the optional 'researcher' or 'diversifier' agent with the Claude or Codex CLI.

    python run_agent.py --role researcher  --config viz/config.json \
        --context viz/plan.md viz/goal.md --out viz/research/researcher.md
    python run_agent.py --role diversifier ...

The role prompt comes from references/<role>.md (next to this script's parent
dir); the context files are appended verbatim. Backend, model and effort come
from config.json:

    {"researcher":  {"enabled": true, "backend": "claude", "model": "claude-sonnet-4-6", "effort": "high"},
     "diversifier": {"enabled": true, "backend": "codex",  "model": "gpt-5.6-luna",     "effort": "high"}}

CLI mapping
  claude -> claude -p --model M --effort E --allowedTools WebSearch WebFetch Read Glob Grep
  codex  -> codex exec -c web_search="live" -m M -c model_reasoning_effort=E -s read-only --skip-git-repo-check -o OUT

Both are run with web search on and file writes off: the agents only produce a
markdown report, the main session decides what to adopt.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
DEFAULTS = {
    "claude": {"model": "claude-sonnet-4-6", "effort": "high"},
    "codex": {"model": "gpt-5.6-luna", "effort": "high"},
}


def build_prompt(role: str, context: list[Path]) -> str:
    role_md = (SKILL / "references" / f"{role}.md").read_text()
    parts = [role_md, "\n\n---\n# Context files\n"]
    for p in context:
        parts.append(f"\n\n## {p}\n\n```\n{p.read_text()}\n```")
    return "".join(parts)


def run_claude(prompt: str, model: str, effort: str, out: Path) -> int:
    exe = shutil.which("claude")
    if not exe:
        sys.exit("claude CLI not found on PATH")
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}  # allow nesting
    cmd = [exe, "-p", "--model", model, "--effort", effort, "--output-format", "text",
           "--allowedTools", "WebSearch", "WebFetch", "Read", "Glob", "Grep"]
    print("running:", " ".join(cmd))
    r = subprocess.run(cmd, input=prompt, text=True, capture_output=True, env=env)
    out.write_text(r.stdout)
    if r.returncode:
        print(r.stderr, file=sys.stderr)
    return r.returncode


def run_codex(prompt: str, model: str, effort: str, out: Path) -> int:
    exe = shutil.which("codex")
    if not exe:
        sys.exit("codex CLI not found on PATH")
    cmd = [exe, "exec", "--skip-git-repo-check", "-s", "read-only", "-c", 'web_search="live"',
           "-m", model, "-c", f"model_reasoning_effort={effort}", "-o", str(out), "-"]
    print("running:", " ".join(cmd))
    r = subprocess.run(cmd, input=prompt, text=True)
    return r.returncode


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--role", required=True, choices=["researcher", "diversifier"])
    ap.add_argument("--config", type=Path, default=Path("viz/config.json"))
    ap.add_argument("--context", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--backend", choices=["claude", "codex"], help="override config")
    ap.add_argument("--model", help="override config")
    ap.add_argument("--effort", help="override config")
    a = ap.parse_args()

    cfg = {}
    if a.config.exists():
        cfg = json.loads(a.config.read_text()).get(a.role, {})
    if not a.backend and cfg and not cfg.get("enabled", True):
        sys.exit(f"{a.role} is disabled in {a.config}; pass --backend to force")
    backend = a.backend or cfg.get("backend", "claude")
    model = a.model or cfg.get("model") or DEFAULTS[backend]["model"]
    effort = a.effort or cfg.get("effort") or DEFAULTS[backend]["effort"]

    prompt = build_prompt(a.role, a.context)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    rc = (run_claude if backend == "claude" else run_codex)(prompt, model, effort, a.out)
    print(f"{a.role} ({backend} {model} {effort}) -> {a.out}  rc={rc}")
    sys.exit(rc)


if __name__ == "__main__":
    main()

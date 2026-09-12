#!/usr/bin/env python3
"""Raw layer of the WikiSkill loop: append-only trajectory of one figure-making run.

Every decision that led to a figure is logged as one JSON line in
<project>/viz/trajectory/run_<id>.jsonl (immutable: only appends). On close the
run is rendered to run_<id>.md and copied to $VIZ_RESULTS_HOME/raw/ so the wiki
maintainer can read traces across projects.

    trajectory.py start   --project . --study "Explainability study"
    trajectory.py log     --stage plan     --hyp H1 --figure F1 --note "3 candidates; #1 box+points (score 9)" --data '{"candidates":3}'
    trajectory.py log     --stage answer   --note "user: per-participant means, 95% CI, stars yes"
    trajectory.py log     --stage build    --figure F1 --file viz/figures/F1_interventions.pdf --note "single, 3.5x2.3in"
    trajectory.py log     --stage verify   --figure F1 --note "legend overlapped bars -> moved to upper left"
    trajectory.py feedback --figure F1 --rating 4 --action revise --comment "use paired lines instead of box"
    trajectory.py log     --stage reaction --figure F1 --note "user accepted revision v2"
    trajectory.py close   --summary "5 figures accepted, 1 revised twice"
    trajectory.py render | list | current

Stages (free text, but use these so the wiki maintainer can group them):
  prep goal data parse plan question answer research diversify build verify
  revise export stats feedback reaction note
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("VIZ_RESULTS_HOME", Path.home() / ".viz_results"))


def traj_dir(project: Path) -> Path:
    d = project / "viz" / "trajectory"
    d.mkdir(parents=True, exist_ok=True)
    return d


def current_run(project: Path) -> Path | None:
    p = traj_dir(project) / "CURRENT"
    if not p.exists():
        return None
    f = traj_dir(project) / p.read_text().strip()
    return f if f.exists() else None


def append(project: Path, event: dict) -> Path:
    run = current_run(project)
    if run is None:
        sys.exit("no active run: trajectory.py start first")
    event = {"t": datetime.now().isoformat(timespec="seconds"), **event}
    with run.open("a") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    return run


def read(run: Path) -> list[dict]:
    return [json.loads(l) for l in run.read_text().splitlines() if l.strip()]


def cmd_start(a):
    d = traj_dir(a.project)
    rid = datetime.now().strftime("%Y%m%d_%H%M%S")
    run = d / f"run_{rid}.jsonl"
    (d / "CURRENT").write_text(run.name)
    run.write_text(json.dumps({"t": datetime.now().isoformat(timespec="seconds"), "type": "run_start", "run": rid,
                               "study": a.study, "project": str(a.project.resolve()), "skill_version": skill_version()}) + "\n")
    print(f"started run {rid} -> {run}")


def skill_version() -> str:
    try:
        import subprocess
        root = Path(__file__).resolve().parent.parent
        return subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def cmd_log(a):
    ev = {"type": "log", "stage": a.stage, "note": a.note}
    for k in ("hyp", "figure", "file"):
        if getattr(a, k):
            ev[k] = getattr(a, k)
    if a.data:
        ev["data"] = json.loads(a.data)
    run = append(a.project, ev)
    print(f"logged [{a.stage}] -> {run.name}")


def cmd_feedback(a):
    ev = {"type": "feedback", "stage": "feedback", "figure": a.figure, "rating": a.rating, "action": a.action, "comment": a.comment}
    run = append(a.project, ev)
    print(f"feedback {a.figure}: {a.rating}/5 {a.action} -> {run.name}")


def cmd_close(a):
    run = append(a.project, {"type": "run_end", "summary": a.summary})
    md = render(run)
    out = run.with_suffix(".md")
    out.write_text(md)
    raw = HOME / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    name = f"{a.project.resolve().name.replace(' ', '_')}__{run.stem}"
    shutil.copy(run, raw / f"{name}.jsonl")
    shutil.copy(out, raw / f"{name}.md")
    (traj_dir(a.project) / "CURRENT").unlink(missing_ok=True)
    print(f"closed {run.name}; rendered {out.name}; copied to {raw}")


def render(run: Path) -> str:
    ev = read(run)
    head = ev[0] if ev else {}
    lines = [f"# Run {head.get('run', run.stem)} — {head.get('study', '')}", "",
             f"project: `{head.get('project', '')}` · skill version: `{head.get('skill_version', '?')}` · started {head.get('t', '')}", ""]
    end = next((e for e in ev if e.get("type") == "run_end"), None)
    if end:
        lines += [f"**Summary:** {end.get('summary', '')}", ""]
    by_fig: dict[str, list[dict]] = defaultdict(list)
    general = []
    for e in ev[1:]:
        if e.get("type") == "run_end":
            continue
        (by_fig[e["figure"]] if e.get("figure") else general).append(e)
    if general:
        lines += ["## Run-level events", ""]
        lines += [f"- `{e['t'][11:]}` **{e.get('stage', e['type'])}**{(' [' + e['hyp'] + ']') if e.get('hyp') else ''}: {e.get('note', e.get('comment', ''))}" for e in general]
        lines.append("")
    for fig, evs in sorted(by_fig.items()):
        fb = [e for e in evs if e["type"] == "feedback"]
        fb_txt = ", ".join(f"{e['rating']}/5 {e['action']}" for e in fb)
        rating = f" · feedback {fb_txt}" if fb else ""
        lines += [f"## {fig}{rating}", ""]
        for e in evs:
            if e["type"] == "feedback":
                lines.append(f"- `{e['t'][11:]}` **feedback** {e['rating']}/5, {e['action']}: {e['comment']}")
            else:
                extra = f" ({e['file']})" if e.get("file") else ""
                lines.append(f"- `{e['t'][11:]}` **{e['stage']}**{(' [' + e['hyp'] + ']') if e.get('hyp') else ''}: {e['note']}{extra}")
        lines.append("")
    return "\n".join(lines)


def cmd_render(a):
    run = (traj_dir(a.project) / f"run_{a.run}.jsonl") if a.run else current_run(a.project)
    if not run:
        sys.exit("no run")
    print(render(run))


def cmd_list(a):
    for f in sorted(traj_dir(a.project).glob("run_*.jsonl")):
        ev = read(f)
        fb = [e for e in ev if e.get("type") == "feedback"]
        closed = any(e.get("type") == "run_end" for e in ev)
        print(f"{f.stem}  events={len(ev)}  feedback={len(fb)}  {'closed' if closed else 'OPEN'}  {ev[0].get('study', '')}")


def cmd_current(a):
    run = current_run(a.project)
    print(run.stem if run else "none")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", type=Path, default=Path("."))
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("--study", default=""); s.set_defaults(fn=cmd_start)
    s = sub.add_parser("log"); s.add_argument("--stage", required=True); s.add_argument("--note", required=True)
    s.add_argument("--hyp"); s.add_argument("--figure"); s.add_argument("--file"); s.add_argument("--data", help="JSON string"); s.set_defaults(fn=cmd_log)
    s = sub.add_parser("feedback"); s.add_argument("--figure", required=True); s.add_argument("--rating", type=int, required=True, choices=range(1, 6))
    s.add_argument("--action", choices=["accept", "revise", "reject"], required=True); s.add_argument("--comment", default=""); s.set_defaults(fn=cmd_feedback)
    s = sub.add_parser("close"); s.add_argument("--summary", default=""); s.set_defaults(fn=cmd_close)
    s = sub.add_parser("render"); s.add_argument("--run"); s.set_defaults(fn=cmd_render)
    s = sub.add_parser("list"); s.set_defaults(fn=cmd_list)
    s = sub.add_parser("current"); s.set_defaults(fn=cmd_current)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

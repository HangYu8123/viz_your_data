#!/usr/bin/env python3
"""Wiki layer of the WikiSkill loop: persistent patterns distilled from runs, plus
the evolution log and the skill-impact audit trail. Lives outside the skill
install so re-installing never erases it:

    $VIZ_RESULTS_HOME (default ~/.viz_results)/
      raw/                copies of closed trajectories (from trajectory.py close)
      wiki/
        index.md          catalog of patterns (rebuilt by `index`)
        logs.md           evolution log, one entry per maintenance pass
        skill-impact.md   proposals to change the skill, with status and evidence
        patterns/P-*.md   one page per pattern (success strategy or failure mode)

    wiki.py init
    wiki.py show                                   # index + last log entries (read this before planning)
    wiki.py pattern --id P-paired-lines-over-bars --kind success --title "Within-subject data: paired lines beat bars" \\
        --applies "2-3 conditions, same participants" --evidence "study__run_20260912_101500:F1" \\
        --body "Users rated paired-line plots 5/5 twice where box/bar got 3/5 ..."
    wiki.py pattern --id P-... --append "New evidence: ..."          # patch: append to an existing page
    wiki.py log --note "Maintenance after run 20260912_101500: +1 pattern, 1 updated"
    wiki.py impact --proposal "Rank paired-line plot first for within-subject 2-condition claims" \\
        --target SKILL.md --status proposed --evidence P-paired-lines-over-bars
    wiki.py impact --id 3 --status accepted --note "user approved; applied in commit abc123"
    wiki.py raw                                    # list raw traces available to the maintainer

Gating (adapted from WikiSkill): the wiki is never rolled back; a skill change
is applied only after the user approves the proposal, and its status is
revisited after the next run's feedback (kept if feedback did not get worse,
otherwise reverted and logged as rejected).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

HOME = Path(os.environ.get("VIZ_RESULTS_HOME", Path.home() / ".viz_results"))
WIKI = HOME / "wiki"
PATTERNS = WIKI / "patterns"
TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "wiki"


def init(quiet=False) -> None:
    PATTERNS.mkdir(parents=True, exist_ok=True)
    (HOME / "raw").mkdir(parents=True, exist_ok=True)
    for name in ("index.md", "logs.md", "skill-impact.md"):
        p = WIKI / name
        if not p.exists():
            src = TEMPLATES / name
            p.write_text(src.read_text() if src.exists() else f"# {name}\n")
    if not quiet:
        print(f"wiki at {WIKI}")


def frontmatter(text: str) -> dict:
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    out = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out[k.strip()] = v.strip()
    return out


def cmd_pattern(a):
    init(quiet=True)
    p = PATTERNS / f"{a.id}.md"
    today = date.today().isoformat()
    if p.exists():
        text = p.read_text()
        if a.append:
            text = text.rstrip() + f"\n\n### Update {today}\n{a.append}\n"
        if a.evidence:
            text = text.rstrip() + f"\n- evidence ({today}): {a.evidence}\n"
        if a.body:
            text = re.sub(r"(## Pattern\n)(.*?)(\n## )", lambda m: f"{m.group(1)}{a.body}\n{m.group(3)}", text, count=1, flags=re.S)
        fm = frontmatter(text)
        text = re.sub(r"(updated:)[^\n]*", rf"\1 {today}", text, count=1) if "updated" in fm else text
        p.write_text(text)
        print(f"updated {p.name}")
    else:
        if not (a.title and a.kind and a.body):
            sys.exit("new pattern needs --title, --kind and --body")
        text = (f"---\nid: {a.id}\ntitle: {a.title}\nkind: {a.kind}\napplies: {a.applies or ''}\n"
                f"created: {today}\nupdated: {today}\nconfidence: {a.confidence}\n---\n\n"
                f"# {a.title}\n\n## Pattern\n{a.body}\n\n## When it applies\n{a.applies or '(fill in)'}\n\n"
                f"## Evidence\n- evidence ({today}): {a.evidence or '(none yet)'}\n\n## Counter-evidence\n- (none yet)\n")
        p.write_text(text)
        print(f"created {p.name}")
    rebuild_index()


def rebuild_index() -> None:
    rows = []
    for p in sorted(PATTERNS.glob("P-*.md")):
        fm = frontmatter(p.read_text())
        rows.append(f"| [{fm.get('id', p.stem)}](patterns/{p.name}) | {fm.get('kind', '')} | {fm.get('title', '')} | {fm.get('applies', '')} | {fm.get('confidence', '')} | {fm.get('updated', '')} |")
    head = (WIKI / "index.md").read_text().split("## Patterns")[0] if (WIKI / "index.md").exists() else "# viz_results wiki index\n\n"
    body = "## Patterns\n\n| id | kind | title | applies when | confidence | updated |\n|---|---|---|---|---|---|\n" + ("\n".join(rows) if rows else "| – | | no patterns yet | | | |") + "\n"
    (WIKI / "index.md").write_text(head.rstrip() + "\n\n" + body)


def cmd_index(a):
    init(quiet=True); rebuild_index(); print((WIKI / "index.md").read_text())


def cmd_log(a):
    init(quiet=True)
    with (WIKI / "logs.md").open("a") as fh:
        fh.write(f"\n## {date.today().isoformat()}\n{a.note}\n")
    print("logged")


def cmd_impact(a):
    init(quiet=True)
    p = WIKI / "skill-impact.md"
    text = p.read_text()
    if a.id is not None:
        # update status of an existing entry
        pat = re.compile(rf"(### #{a.id} .*?\n)(.*?)(?=\n### #|\Z)", re.S)
        m = pat.search(text)
        if not m:
            sys.exit(f"proposal #{a.id} not found")
        block = m.group(2)
        block = re.sub(r"- status: .*", f"- status: {a.status}", block, count=1) if a.status else block
        if a.note:
            block = block.rstrip() + f"\n- {date.today().isoformat()}: {a.note}\n"
        text = text[:m.start(2)] + block + text[m.end(2):]
        p.write_text(text)
        print(f"updated #{a.id} -> {a.status or ''}")
        return
    ids = [int(x) for x in re.findall(r"^### #(\d+) ", text, re.M)]
    nid = (max(ids) + 1) if ids else 1
    entry = (f"\n### #{nid} {date.today().isoformat()} — {a.proposal}\n"
             f"- target: {a.target}\n- status: {a.status}\n- evidence: {a.evidence or ''}\n"
             f"- rationale: {a.rationale or ''}\n- validation: user approval, then feedback of the next run must not drop\n")
    if a.diff_file:
        entry += f"- diff:\n```diff\n{Path(a.diff_file).read_text().strip()}\n```\n"
    p.write_text(text.rstrip() + "\n" + entry)
    print(f"proposal #{nid} recorded ({a.status})")


def cmd_show(a):
    init(quiet=True)
    print((WIKI / "index.md").read_text())
    logs = (WIKI / "logs.md").read_text().strip().split("\n## ")
    print("\n## Recent log entries\n")
    for chunk in logs[-3:]:
        print(("## " if not chunk.startswith("#") else "") + chunk.strip() + "\n")
    imp = (WIKI / "skill-impact.md").read_text()
    open_ = re.findall(r"### #(\d+) [^\n]*\n(?:.*?\n)*?- status: proposed", imp)
    if open_:
        print(f"open proposals in skill-impact.md: {', '.join('#' + i for i in open_)}")
    if a.patterns:
        for p in sorted(PATTERNS.glob("P-*.md")):
            print("\n---\n" + p.read_text())


def cmd_raw(a):
    init(quiet=True)
    for p in sorted((HOME / "raw").glob("*.md")):
        print(p.name)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(fn=lambda a: init())
    s = sub.add_parser("show"); s.add_argument("--patterns", action="store_true", help="also print every pattern page"); s.set_defaults(fn=cmd_show)
    s = sub.add_parser("index"); s.set_defaults(fn=cmd_index)
    s = sub.add_parser("pattern"); s.add_argument("--id", required=True); s.add_argument("--title"); s.add_argument("--kind", choices=["success", "failure", "preference"])
    s.add_argument("--applies"); s.add_argument("--body"); s.add_argument("--append"); s.add_argument("--evidence"); s.add_argument("--confidence", default="low"); s.set_defaults(fn=cmd_pattern)
    s = sub.add_parser("log"); s.add_argument("--note", required=True); s.set_defaults(fn=cmd_log)
    s = sub.add_parser("impact"); s.add_argument("--id", type=int); s.add_argument("--proposal"); s.add_argument("--target", default="SKILL.md")
    s.add_argument("--status", choices=["proposed", "accepted", "rejected", "reverted"], default="proposed"); s.add_argument("--evidence"); s.add_argument("--rationale"); s.add_argument("--note"); s.add_argument("--diff-file"); s.set_defaults(fn=cmd_impact)
    s = sub.add_parser("raw"); s.set_defaults(fn=cmd_raw)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

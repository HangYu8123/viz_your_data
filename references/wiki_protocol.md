# Recording, feedback and evolution (WikiSkill-style)

Adapted from *WikiSkill: Compiling Agent Experience into Persistent Knowledge
for Skill Evolution* (arXiv 2608.27454). Three layers:

| layer | where | who writes | mutability |
|---|---|---|---|
| raw traces | `<project>/viz/trajectory/run_*.jsonl` (+ copy in `~/.viz_results/raw/`) | `scripts/trajectory.py` during the run | append-only |
| wiki | `~/.viz_results/wiki/` (`index.md`, `patterns/`, `logs.md`, `skill-impact.md`) | maintenance pass after a run | never rolled back |
| skill | this skill (SKILL.md, templates, palettes) | only via an accepted proposal in `skill-impact.md` | gated |

`VIZ_RESULTS_HOME` overrides `~/.viz_results`. It sits outside the install
directory so `install.sh` never erases accumulated knowledge.

## 1. What to log during a run (raw layer)

Start the run right after Step 0 and log **decisions, not chatter**. One
line per event; name the figure / hypothesis whenever it applies.

| stage | log this |
|---|---|
| `data` / `parse` | sessions found vs expected, dropped files and why, parser mismatches |
| `plan` | per hypothesis: number of candidates, the #1 with its score and style ref, wiki patterns applied |
| `question` / `answer` | the three questions and the user's answers (verbatim, short) |
| `research` / `diversify` | which suggestions were adopted or rejected and why |
| `build` | figure id, width, height, file; palette / preset |
| `verify` | what you saw in the PNG and what you fixed (clipped labels, legend overlap) |
| `revise` | what changed after feedback, version number |
| `stats` | verdicts per claim |
| `feedback` | rating, action, comment (via `trajectory.py feedback` or the `/feedback` page) |
| `reaction` | how the user responded to a revision: accepted / asked again / abandoned |

Use `--data` for machine-readable facts (scores, sizes). Close the run with a
one-sentence summary; `close` renders `run_*.md` and copies both to `raw/`.

## 2. Collecting feedback (Step 6)

After the figures exist:

1. Start the GUI if it is not running and point the user at
   `http://127.0.0.1:8765/feedback` — it lists every PNG in `viz/figures/` with
   a 1–5 rating, an action (accept / revise / reject) and a comment box, and
   writes straight into the trajectory. Without the GUI, ask per figure with
   AskUserQuestion (rating + action) and log with `trajectory.py feedback`.
2. For every `revise`, go back to Step 3 for that figure, log a `revise`
   event with a version number, show the new PNG, and log the `reaction`.
3. For every `reject`, ask one question: which candidate from plan.md should
   replace it, or what was wrong with the framing — then log and rebuild.
4. Record overall comments as a run-level `feedback` event.

Feedback is data about the *user and their venue*, not a verdict on the skill.
A 2/5 with "too busy for a single column" is a pattern candidate; a 2/5 with
"wrong metric" is a parser or goal.md issue.

## 3. Maintenance pass after `close` (wiki layer)

Read the rendered run (`trajectory.py render`), earlier raw traces
(`wiki.py raw`) when relevant, and the current index (`wiki.py show`). Then:

1. **Distil patterns.** A pattern is a reusable statement with evidence:
   *success strategy* ("within-subject 2-condition claims: paired-line plot
   rated ≥4/5 in 3 runs, box+points ≤3/5"), *failure mode* ("legend inside
   axes at single width overlapped bars in 4/6 figures → place below"), or
   *preference* ("this user wants significance stars only in the hero
   figure"). Create with `wiki.py pattern --kind …`, or patch an existing
   page with `--append` / `--evidence`. Cite raw trace ids and figure ids.
   Raise `confidence` (low → medium → high) only when evidence spans ≥2 runs.
2. **Log the pass** with `wiki.py log`: traces read, pages touched.
3. **Propose at most one atomic skill change** with `wiki.py impact`: a
   ranking rule, a template field, a palette, a default in ieee_style, a
   question to add to the three. State the evidence pattern ids and the
   expected effect. Do not apply it yet.

## 4. Gating a skill change (skill layer)

- Present the proposal to the user in one short block (what, why, evidence).
  Apply only on approval; then `wiki.py impact --id N --status accepted
  --note "commit …"` and commit the skill change separately from data.
- After the **next** run closes, compare that run's mean rating and revise
  count for the affected figure type with the run before. Kept if not worse
  (`--status accepted`, add a note); otherwise revert the change and mark
  `reverted`, keeping the wiki pages (they are evidence either way).
- Rejected or reverted proposals stay in `skill-impact.md` so the proposer
  does not repeat them.

## 5. Using the wiki when planning (Step 2)

Run `wiki.py show` before writing `plan.md`. Apply matching patterns to the
ranking and note them (`wiki: P-paired-lines-over-bars`). Patterns are
guidance with stated confidence, not rules: a `low` confidence pattern can be
outranked by the venue or the user's answers.

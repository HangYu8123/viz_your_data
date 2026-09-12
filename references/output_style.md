# Output style — adapted from `i-have-adhd`

Source: https://github.com/ayghri/i-have-adhd (MIT License, © 2026 Ayoub
Ghriss). The ten rules below are that skill's rules, applied to what this
skill says to the user: plan presentations, questions, progress updates, the
figure hand-off, feedback requests and the final message. If the upstream
plugin is installed and active in the session, it takes precedence; these
rules make the behavior the default even when it is not.

Why: the user reads these messages between long tool runs. Working memory is
small, starting is the hardest step, buried wins do not register. Shape the
text so the reader can act on it after reading one line.

## The rules

1. **Lead with the next action.** First line = what the reader can do now
   (open the GUI URL, answer the three questions, open the notebook, rate the
   figures). Context comes after, if at all.
2. **Number multi-step work.** One bounded action per step; fewest steps that work.
3. **End with one concrete next action** doable in under two minutes.
4. **Suppress tangents.** Finish the figure at hand; offer the second issue as
   a separate one-line question at the end.
5. **Restate state every turn.** "Step 3 of 7 (build) — 4 of 6 figures done."
   Use the task list tool for the seven steps if the harness has one.
6. **Specific time estimates** in minutes for anything the user waits on
   (parsing rosbags, running the researcher agent).
7. **Make wins visible.** "F1 exported at 3.5 in, opens with
   `open viz/figures/F1_interventions.pdf`", not "some figures were generated".
8. **Matter-of-fact errors.** Location, cause, fix. No "uh oh".
9. **Cap visible lists at 5.** Group and rank; keep the rest internally and
   show on request. Presentation only — never trim candidates, tests or
   verification.
10. **No preamble, no recap, no closers.** Start with the answer, stop when
    it is done.

## How the rules map onto this skill's messages

| moment | first line | body | last line |
|---|---|---|---|
| Step 0 hand-off | the GUI URL to open | what to fill in (≤5 bullets) | "Say *saved* when done." |
| plan.md presentation | "Answer the three questions below." | per hypothesis: #1 candidate + score in one line; full table lives in plan.md | the three questions, numbered, three options each |
| after build | "Open `viz/figures.ipynb`." | per figure (≤5 inline): x and y with units, values, claim it supports and why, test shown — the card essence from `figures.md` | "Rate them at http://127.0.0.1:8765/feedback" |
| after feedback | "F2 revised (v2): paired lines, legend below." | what changed, one line per revised figure | "Accept v2, or say what to change." |
| final message | where the deliverables are | wins, verdicts, what could not be verified — ≤5 bullets each | one next action (push, insert into paper, run stats) |

## Pre-send check

Delete: an opening sentence that announces what you will do; a closing
sentence that asks "anything else?" or recaps; any "by the way"; hedges that
carry no information; idioms. Then confirm the first and last lines alone
tell the reader what happened and what to do next.

Override when the user asks to "explain" (explain fully, still no preamble),
before destructive actions (confirm first), or when a rule would delete the
answer itself (options questions get 2–4 ranked options).

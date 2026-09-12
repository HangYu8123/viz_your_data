---
name: viz_results
description: End-to-end workflow for turning experiment / user-study data into paper-ready figures. Use this skill whenever the user wants to visualize, plot, chart, or analyze experimental results, study logs, rosbags, CSV/JSON metrics, questionnaire data, or wants figures for an IEEE / conference paper — even if they only say "make a plot", "show me the results", "compare conditions", or "which figure should I use". It prepares the plotting environment, collects goals (goal.md), data descriptions (data.md) and agent settings (config.json) from the user via a local GUI or templates, writes separate data-parsing modules, proposes ranked visualization candidates per hypothesis with clarifying questions, optionally runs an online researcher and a diversifier agent (Claude or Codex CLI) to refine the plan, then builds a single Jupyter notebook that exports PDF figures at exact IEEE column widths, optionally an interactive HTML report, and optionally a statistics stage (minimal effect size per claim, ANOVA / t-test / correlation on the plotted data) written to statistics.md and statistics.html. It records the whole trajectory of every figure, collects the user's ratings and reactions after the figures exist, and distils them into a persistent wiki that proposes gated improvements to the skill itself (WikiSkill-style); all messages to the user follow an ADHD-friendly, action-first output style.
---

# viz_results — from raw experiment data to paper-ready figures

The point of this skill is to avoid two common failures: (1) plots that answer no
question, and (2) plots that look fine on screen but have to be rescaled, re-fonted,
and re-exported before they fit a two-column paper. So the workflow is deliberately
"goal first, data second, plot last", and every figure is born at its final size.

Skill root = the directory containing this file. Paths below like `scripts/…`
are relative to it. Project-side artifacts all live in `<project>/viz/`.

## Conventions (apply throughout)

- **One notebook for all figures.** Visualization code lives in a single
  `viz/figures.ipynb` — one figure per cell (or per small group of cells) so the
  user can run, inspect, and debug every figure in one place. Data loading / parsing
  lives in importable `.py` modules (`viz/parse/*.py`) so the notebook stays thin
  and the parsers can be reused or unit-tested. Build the notebook with
  `scripts/build_notebook.py` rather than hand-writing ipynb JSON.
- **Two figure widths only.** Every figure is one of:
  - `single` = IEEE one-column width, **3.5 in** (half page)
  - `double` = IEEE two-column width, **7.16 in** (full page)
  Pick the height yourself (roughly 0.5–0.75 × width for single, 0.3–0.45 × width
  for double is a sane default; taller for stacked subplots). Never rely on the user
  resizing in LaTeX — `\includegraphics[width=\columnwidth]` should be a no-op.
  `scripts/ieee_style.py` provides `fig(kind, height=...)` and `save(fig, name)`
  that enforce this and set publication rc params (8 pt fonts, thin spines,
  `pdf.fonttype=42` so text stays editable in Illustrator/Inkscape).
- **Export PDF by default** (vector). Also write a PNG preview at 200 dpi next to
  it so the notebook / chat can show it inline; the PDF is what goes in the paper.
- **Colorblind-safe, print-safe palettes.** Use the `dataviz` skill's guidance if it
  is available; otherwise default to Okabe–Ito (set in `ieee_style.py`). Never
  encode a condition only by color — add markers, hatches, or line styles.
- Report only what you actually verified. If a parser could not read some files,
  say which ones and why; don't silently drop them.
- **Every figure explains itself.** x and y are named with units
  (`st.label_axes`), bars carry values when numbers matter (`st.value_labels`),
  the claim it supports is named in `st.save(meta={"claim": "H1", …})`, and
  when statistics ran, the test result is drawn on the figure
  (`st.annotate_sig` / `st.annotate_posthoc` / `st.stats_footer`). `st.save`
  warns about missing labels or units; treat warnings as build failures.
  `viz/figures.md` (from `scripts/build_figure_cards.py`) documents axes,
  values, claim and reading for every figure, and the chat message repeats the
  essentials — see `references/figure_cards.md`.
- **Record as you go.** From Step 1 on, every decision that shapes a figure is
  logged with `scripts/trajectory.py log` (stage, hypothesis, figure, note);
  see `references/wiki_protocol.md` §1 for what belongs at each stage. The
  trajectory is the raw layer of the evolution loop in Steps 6–7 — without it
  feedback cannot be traced back to the choice that caused it. Skip only if
  `record.trajectory` is false in config.json.
- **Talk to the user action-first.** Every message follows
  `references/output_style.md` (the `i-have-adhd` rules): first line is what
  the reader does now, numbered steps, state restated ("Step 3 of 7"), ≤5
  visible items per group, specific minutes for waits, wins stated concretely,
  no preamble and no closer. Documents (plan.md, statistics.md) keep their
  full tables; the rules shape chat messages.

## Workflow

### Step P — Prepare the environment

Run `python3 scripts/setup_env.py` first (or `--check` to only report). It
installs or upgrades matplotlib, seaborn, pandas, numpy, scipy, pyarrow,
nbformat, nbconvert, ipykernel, jupyter, pypdf and plotly with the *current*
interpreter and registers a `viz_results` kernel. Doing this up front avoids the
classic failure where the notebook runs but `nbconvert` is missing and the user
opens a notebook with no outputs. If pip cannot reach the index, say so and
continue with whatever is installed; only nbconvert / plotly are non-essential.

### Step 0 — Collect goal.md, data.md and config.json from the user

Before touching data, make sure these files exist in `<project>/viz/`:

- `goal.md` — experiment description (task, conditions, participants, metrics),
  the **hypotheses they want to prove** (H1, H2, …), **"fun" / exploratory
  results** they'd like to look at, and paper context (venue, figure budget).
- `data.md` — the **files / directories to parse**, one example file per type,
  their formats, what each field means, and preferably the **expected outcome**
  (e.g. "condition B should have fewer interventions") so parsers can be
  sanity-checked.
- `config.json` — whether the optional researcher / diversifier agents run, and
  with which backend (`claude` | `codex`), model and effort. Defaults: Claude
  `claude-sonnet-4-6` at `high`, Codex `gpt-5.6-luna` at `high`. Also
  `html_report: true|false` and `statistics: {enabled, alpha, power, correction, raw_sesoi}`.
  Template in `templates/config.json`.

Preferred way to get them: **launch the GUI** and ask the user to fill it in:

```bash
python3 <skill-root>/scripts/gui.py --project "<project>"
```

It opens `http://127.0.0.1:8765/`, can auto-detect file types in the project,
lets the user browse and pick one example file per type (with a head preview),
fill goal fields or paste sections of their paper, and toggle / configure the
agents. "Save" writes the three files into `viz/`. Run it in the background
(`run_in_background`) so the session stays responsive, tell the user the URL,
and end the turn — resume when they say they've saved. If the GUI cannot be
opened (headless, no browser), copy `templates/goal.md`, `templates/data.md`,
`templates/config.json` into `viz/` and ask the user to fill them in.

If the user has already described goals and data in the conversation, pre-fill
the files from that description, but still ask them to confirm / complete — the
act of writing them down usually surfaces missing conditions, exclusion
criteria, and metric definitions.

### Step 1 — Analyze goal.md + data.md, then write parsers

Start the record: `python3 <skill-root>/scripts/trajectory.py --project <project> start --study "<name>"`.
Read all three files. Then inspect the actual data (list directories, open the
example files, check schemas, count sessions per condition) before writing code —
data.md is what the user *thinks* is there; verify it.

Write one parser module per data source in `viz/parse/` (e.g. `rosbag_parser.py`,
`questionnaire.py`, `video_events.py`). Each module should expose a function that
returns a **tidy pandas DataFrame** (one row per observation, columns for
participant / condition / trial / metric). Add a `load_all()` in
`viz/parse/__init__.py` that assembles the per-source frames into the few tables
the notebook needs, and cache the result (`viz/cache/*.parquet`) because parsing
rosbags / videos is slow and the notebook will be re-run many times.

Run the parsers and print a short summary table (rows per condition, missing
values, ranges). Compare against the "expected outcome" notes in data.md and flag
discrepancies to the user right away — a plot built on a broken parser is worse
than no plot.

### Step 2 — Propose visualization plans (and grill the user a little)

Run `python3 <skill-root>/scripts/wiki.py show` first: it prints the patterns
distilled from earlier runs (what this user / venue rated well, what failed)
with their confidence. Apply the matching ones to your ranking and cite them
(`wiki: P-…`) in plan.md. Then write `viz/plan.md` following
`references/plan_template.md` and show it to the user. For **every** hypothesis, target, or fun result in goal.md:

- Propose **at least 3 candidate figures**, ranked from most to least recommended,
  each with a **recommendation score** (0–10) and one line on *why* it ranks there.
- For each candidate specify at minimum: **x axis**, **y axis**, **z / third
  encoding** if any (color, facet, size, or a real third axis), **plot type**
  (bar, box, violin, scatter, line, heatmap, …), **the purpose** (what a reader
  should conclude at a glance), **width** (`single`/`double`), and anything else
  that matters: error bars / CI type, statistical test annotation, per-participant
  overlay, log scale, normalization, what gets excluded.
- Name a **style reference** for each candidate when one fits
  (`style: memory_anchors/fig6`), taken from `references/styles/README.md` —
  a library of figures from recent papers with images, style analyses and
  ready palettes. Match the reference by purpose (grouped ablation bars, signed
  sorted diffs, presence matrix, pipeline diagram, donut, result matrix), not
  by topic.
- Then ask the user **three short questions** (one sentence each, three options
  each) to pin down preferences, clarify ambiguity, or set the analysis depth.
  Good targets: aggregation level (per trial vs per participant), error
  representation (SD / SEM / 95% CI / raw points), significance markers or not,
  which condition is the baseline, whether to normalize, how much stats rigor
  they want (descriptive → pairwise tests → mixed models). Ask the three questions
  once per plan, not per candidate — don't bury the user.

Use AskUserQuestion if it is available; otherwise list the questions in the
message. Wait for answers before building the notebook — they change axes,
error bars, and sometimes the whole plot type.

### Step 2b — Optional: online researcher and diversifier

Check `viz/config.json`. For each agent with `"enabled": true`, run it **after
plan.md exists and before the user answers the three questions** (so their
findings can be folded into the same round of questions), both in parallel:

```bash
python3 <skill-root>/scripts/run_agent.py --role researcher  --config viz/config.json \
    --context viz/plan.md viz/goal.md --out viz/research/researcher.md
python3 <skill-root>/scripts/run_agent.py --role diversifier --config viz/config.json \
    --context viz/plan.md viz/goal.md --out viz/research/diversifier.md
```

- **Researcher** (`references/researcher.md`): searches for top-venue papers
  (HRI, ICRA, RA-L, RSS, CHI, …) with comparable results, and extracts concrete
  style notes — plot type, encodings, error bars, significance annotation,
  layout, caption pattern — plus a verdict on plan.md's ranking.
- **Diversifier** (`references/diversifier.md`): searches for more diverse
  ways to express the same data and alternative derived quantities that support
  each claim, with risks.

The script maps `backend` to `claude -p --model … --effort …` (web search on,
read-only tools) or `codex exec -c web_search="live" -m … -c model_reasoning_effort=…`
(read-only sandbox). If you are inside Claude Code and the configured backend is
`claude` with a model the Agent tool can address, you may use the Agent tool
instead with the same role prompt — the CLI path exists so that specific model
ids (e.g. `claude-sonnet-4-6`) and the Codex backend work identically.

When the reports come back, **revise plan.md**: add a "Revisions from research"
subsection per hypothesis listing adopted style notes (with paper citations) and
any new or re-ranked candidates from the diversifier, marked `[R]` / `[D]`. Keep
the original ranking visible so the user can see what changed and why. Do not
adopt a suggestion just because an agent made it — say when you disagree.

### Step 3 — Build the notebook

If `statistics.enabled` is true, compute the statistics **before** the figure
cells (write `viz/statistics.py` as in Step 5 and load `statistics.json` in
the setup cell) so every figure can draw its test result. Generate
`viz/figures.ipynb` with `scripts/build_notebook.py`. Structure:

1. A markdown cell titled with the study name and a table of contents mapping
   figure ids → hypothesis.
2. A setup cell: `import ieee_style as st` (copy `scripts/ieee_style.py` into
   `viz/`), `from parse import load_all`, load the cached tables.
3. For each accepted candidate: a markdown header (`## F3 — H2: intervention count
   by condition`) stating purpose (and the reference paper if the style came
   from the researcher), then **one code cell** that builds the figure with
   `st.fig(...)`, plots, labels axes with units (`st.label_axes`), prints
   values on bars (`st.value_labels`), draws the significance result when
   available (`st.annotate_sig(ax, claims["H2"], x1, x2)` — stars plus effect
   size; `st.annotate_posthoc` for ANOVA pairs; `st.stats_footer` for
   correlations), and calls `st.save(f, "F3_interventions", meta={...})` with
   `claim`, `hypothesis`, `values` (aggregation, error bars, n), `source`,
   `significance`, and `reading` (which visual feature shows the claim and why).
   Keep helpers used by several figures in `viz/plot_helpers.py`, not in the notebook.
   Apply the chosen style reference with `st.use_palette("<name>")` /
   `st.apply_preset("<paper>")` (see `PALETTES` / `PRESETS` in `ieee_style.py`
   and the per-figure "Reproduce" notes in `references/styles/*/analysis.md`).
4. A final cell calling `st.check_widths()` and running
   `build_figure_cards.py viz/figures viz/figures.md --stats viz/statistics.json --chat`
   so the user can confirm every figure is 3.5 in or 7.16 in wide and gets
   `viz/figures.md` with one card per figure (axes with units and ranges,
   values, claim, significance shown, how to read it).

Execute the notebook (`build_notebook.py … --execute`; it uses nbconvert when
installed and otherwise runs the cells directly) so the user opens a notebook
that already shows every figure. Look at every PNG preview yourself before
reporting: check for clipped labels, overlapping ticks, unreadable legends, and
fonts that are visibly bigger or smaller than 8 pt at final size, axes without
units, bars without values, missing significance marks. Fix and re-run —
that's exactly why the figures are born at final width.

Then **explain every figure in chat** (`references/figure_cards.md`, "The chat
explanation"): what x and y are with units, what the values are (aggregation,
error bars, n), which claim it supports and why (the visual feature that shows
it), and the test result drawn on it. At most five figures inline; the rest are
in `viz/figures.md`.

### Step 4 — Optional HTML exploration report

If `html_report` is true in config.json, the user asks for it, or the data has
structure a static figure hides (time series per trial, many participants,
interactions worth hovering over), build `viz/report.html` — a self-contained
page with interactive charts (Plotly via cdnjs; embed data as JSON in the page).
Its job is insight and intuition, not the paper: linked brushing across metrics,
per-participant traces, filters by condition, hover with trial ids. Say clearly
in the message that it is exploratory and not a paper figure. See
`references/html_report.md`. Load the `dataviz` skill for color and mark
conventions if it is available.

### Step 5 — Optional statistics: minimal effects, ANOVA / t-tests / correlations

If `statistics.enabled` is true in config.json (or the user asks), run this
**after the figures exist**, on the same cached tables and the same
aggregation the figures use, so text and figures agree. Copy
`scripts/stats_helpers.py` into `viz/`, write `viz/statistics.py` that builds
one claim block per hypothesis / exploratory item (`claim_pair`, `claim_anova`,
`claim_corr`), calls `finalize(alpha, power, correction)` and `write_json`, and
call it from a final notebook cell. Read `references/statistics.md` for the
test-selection table, the SESOI logic and the exact statistics.md layout.

Deliverables:

1. **Recommended minimal effect size per claim** — the larger of the author's
   domain-meaningful raw effect (from `statistics.raw_sesoi` in config.json, or
   ask in the three questions) and the minimal detectable effect at the study's
   N and target power, with the basis stated in words.
2. **Tests** — paired / independent t-tests with non-parametric fallbacks,
   RM or one-way ANOVA with Greenhouse–Geisser and Holm post-hocs, Pearson +
   Spearman correlations; effect sizes with 95% CIs; assumption checks.
3. **`viz/statistics.md`** — summary table plus one section per claim with an
   APA line (`sh.apa(c)`), assumptions, recommended minimal effect, verdict.
4. **`viz/statistics.html`** — `python scripts/build_stats_html.py
   viz/statistics.json viz/statistics.html`: forest plot of effects vs minimal
   effect, per-claim paired-change / means panels, box + points, test tables.

When statistics are enabled the figures already carry the results (Step 3);
after any statistics change, re-run the notebook so figure annotations,
`figures.md` and `statistics.md` agree.

Be candid in verdicts: "significant but below minimal effect" and
"inconclusive (underpowered)" are legitimate outcomes and reviewers prefer them
to overclaiming.

### Step 6 — Collect feedback and react

Right after the figures (and statistics, if enabled) exist:

1. Point the user at `http://127.0.0.1:8765/feedback` (start `scripts/gui.py`
   if it is not running). The page shows every PNG in `viz/figures/` with a
   1–5 rating, accept / revise / reject, and a comment box, and writes into
   the active trajectory. Without a browser, ask per figure with
   AskUserQuestion and log with `trajectory.py feedback`.
2. For each **revise**: change exactly what was asked, bump the version
   (`F2_v2`), log `revise`, show the PNG, and log the user's `reaction`.
   For each **reject**: ask one question (which other plan candidate, or what
   was wrong with the framing), rebuild, log.
3. Stop when every figure is accepted or the user says stop. Log the
   run-level comments.

Ratings and comments are evidence about the user and the venue; treat "too
busy", "wrong metric", "needs stars" as different kinds of signal (style,
parser, question) — `references/wiki_protocol.md` §2.

### Step 7 — Close the run, maintain the wiki, propose one skill change

1. `trajectory.py close --summary "…"` renders `viz/trajectory/run_*.md` and
   copies it to `~/.viz_results/raw/`.
2. Maintenance pass (`references/wiki_protocol.md` §3): read the rendered run
   and `wiki.py show`; create or patch pattern pages (`wiki.py pattern`) with
   evidence ids; raise confidence only with evidence from ≥2 runs; `wiki.py
   log` the pass. The wiki is never rolled back.
3. Propose **at most one atomic change** to this skill (`wiki.py impact
   --status proposed`): a ranking rule, a template field, a palette default,
   a question. Show it to the user in ≤5 lines with the evidence. Apply only
   if they approve, mark `accepted`, and commit the skill change on its own.
   After the next run, keep it if that run's ratings for the affected figure
   type did not drop; otherwise revert and mark `reverted` (§4).

Then send the final message (format below).

## Bundled files

- `scripts/setup_env.py` — install / upgrade the plotting stack; `--check` only reports.
- `scripts/gui.py` + `gui/index.html` — local setup GUI that writes goal.md, data.md, config.json.
- `scripts/ieee_style.py` — figure width constants, rc params, `fig()`/`save()`/`check_widths()`. Copy into `viz/`.
- `scripts/build_notebook.py` — turns a python spec (list of cells) into a valid `.ipynb`; `--execute` runs it.
- `scripts/run_agent.py` — runs the researcher / diversifier via the Claude or Codex CLI per config.json.
- `templates/goal.md`, `templates/data.md`, `templates/config.json` — fallback when the GUI is not used.
- `references/plan_template.md` — exact layout for `plan.md` (candidates, scores, three questions).
- `references/researcher.md`, `references/diversifier.md` — role prompts for the optional agents.
- `references/html_report.md` — minimal pattern for the interactive HTML report.
- `references/styles/` — reference figure library: images + vector sources from ROSETTA, DeepSeek, Cambrian-S, Cosmos 3, Memory Anchors, with style analyses and palettes (`README.md` is the index; `palettes.png` the swatches).
- `scripts/stats_helpers.py` — scipy-only tests, effect sizes with CIs, MDE / SESOI recommendation, Holm, APA lines. Copy into `viz/`.
- `scripts/build_stats_html.py` — renders `statistics.json` into `statistics.html`.
- `scripts/build_figure_cards.py` — writes `viz/figures.md` (axes, values, claim, significance, reading per figure) from the JSON sidecars `st.save` writes; `--chat` prints the per-figure chat summary.
- `references/figure_cards.md` — what every figure must make explicit, the card template, the chat explanation shape.
- `references/statistics.md` — test-selection table, SESOI logic, statistics.md layout.
- `scripts/trajectory.py` — append-only run trajectory (raw layer): start / log / feedback / close / render.
- `scripts/wiki.py` — persistent wiki at `~/.viz_results/wiki` (patterns, logs, skill-impact): show / pattern / log / impact.
- `gui/feedback.html` — `/feedback` page served by `gui.py` for ratings, actions and comments per figure.
- `templates/wiki/` — seed pages for a fresh wiki.
- `references/wiki_protocol.md` — what to log, how to collect feedback, maintenance pass, gating of skill changes.
- `references/output_style.md` — the `i-have-adhd` output rules adapted to this skill's messages (MIT, ayghri/i-have-adhd).
- `install.sh` — installs this skill for Claude Code (`~/.claude/skills`) and Codex (`~/.codex/skills`); `--package` builds `dist/viz_results.skill`.

## Installing for CLI agents

```bash
<skill-root>/install.sh              # Claude Code + Codex, user level
<skill-root>/install.sh --project .  # also into this project's .claude/skills and .codex/skills
```

Both CLIs discover skills by scanning those folders; invoke with `/viz_results`
in Claude Code or `$viz_results` in Codex (or just describe the task).

## Final message to the user

Follow `references/output_style.md`: first line = the one thing to do now
(open the notebook, insert a figure, push). Then lead with what was produced and where (`viz/figures.ipynb`, `viz/figures/*.pdf`),
which hypotheses each figure addresses, which research / diversifier suggestions
were adopted, the per-figure explanation (axes, values, claim, significance —
≤5 figures inline, rest in `viz/figures.md`), the statistics verdicts per claim
if that stage ran, and anything you could not verify. Keep the list of figures as a
short table: id, hypothesis, plot type, width. Mention that re-running the
notebook regenerates all PDFs and that parsers are cached.

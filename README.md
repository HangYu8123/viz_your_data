# viz_your_data — `viz_results` skill

An agent skill (Claude Code / Codex CLI) that turns raw experiment or user-study
data into paper-ready figures and statistics:

- **Goal first.** You describe the study, hypotheses and data in `goal.md` /
  `data.md` (a local GUI helps you fill them in and pick example files).
- **Parsers as modules, figures in one notebook.** Data parsing lives in
  importable `viz/parse/*.py`; every figure is a cell in `viz/figures.ipynb`.
- **Born at final size.** Figures are exported as PDF at exact IEEE widths
  (3.5 in single column, 7.16 in double column) with 8 pt fonts, so
  `\includegraphics[width=\columnwidth]` needs no rescaling.
- **Self-explaining figures.** Axes named with units, values on bars, the
  claim each figure supports, and the significance test drawn on the figure;
  `viz/figures.md` documents all of it per figure.
- **Ranked plans.** For each hypothesis the agent proposes at least three
  candidate figures (axes, plot type, purpose, width, recommendation score) and
  asks three short questions before building anything.
- **Optional online agents.** A *researcher* finds how top venues present the
  same kind of result; a *diversifier* searches for alternative ways to express
  the data. Each can run on Claude or Codex with a chosen model and effort.
- **Optional statistics.** Recommended minimal effect size per claim, t-tests /
  ANOVA / correlations with effect sizes and CIs, written to `statistics.md`
  and an interactive `statistics.html`.
- **Optional HTML exploration report** for intuition beyond static figures.
- **Learns from you (WikiSkill-style).** Every figure's trajectory is recorded,
  you rate the figures on a `/feedback` page, and the run is distilled into a
  persistent wiki (`~/.viz_results/wiki`) that proposes one gated improvement
  to the skill per run.
- **ADHD-friendly output.** Messages follow the `i-have-adhd` rules (action
  first, numbered steps, state restated, no filler) — adapted from
  [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd) (MIT).

## Install

```bash
git clone https://github.com/HangYu8123/viz_your_data.git
cd viz_your_data
./install.sh            # copies into ~/.claude/skills and ~/.codex/skills
python3 scripts/setup_env.py   # install / upgrade the plotting stack
```

Or download `dist/viz_results.skill` and import it where `.skill` files are
supported.

## Use

```bash
# 1. describe your study and data (writes <project>/viz/goal.md, data.md, config.json)
python3 scripts/gui.py --project /path/to/your/study

# 2. in the study folder
claude   # then:  /viz_results
codex    # then:  $viz_results   (or just describe what you want plotted)
```

The agent then parses the data, proposes a plan, asks its questions, builds
`viz/figures.ipynb` and `viz/figures/*.pdf`, and — if enabled — the research
reports, statistics, and HTML report.

## Layout

```
SKILL.md              workflow the agent follows
scripts/              setup_env, gui, ieee_style, build_notebook, run_agent,
                      stats_helpers, build_stats_html
gui/index.html        setup GUI (served by scripts/gui.py)
templates/            goal.md, data.md, config.json fallbacks
references/           plan template, researcher / diversifier prompts,
                      statistics and HTML report guidance, style library,
                      wiki protocol, output style
scripts/trajectory.py, scripts/wiki.py   run records and the persistent wiki
install.sh            install for Claude Code and Codex; --package builds dist/viz_results.skill
dist/                 packaged skill
```

## Requirements

Python 3.10+, matplotlib, pandas, numpy, scipy (installed by `setup_env.py`;
nbconvert, plotly, pypdf, pyarrow optional but recommended). Web search for
the optional agents needs the `claude` or `codex` CLI logged in.

## License

MIT

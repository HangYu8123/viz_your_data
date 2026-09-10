# Statistics stage (Step 5) — how to produce statistics.md and statistics.html

Runs after the figures exist, on the **same tidy tables the figures were built
from** (the cached parse output), so numbers in the paper text and in the
figures cannot drift apart. Use `scripts/stats_helpers.py` (scipy only) — copy
it into `viz/` next to `ieee_style.py`. Write the driver as `viz/statistics.py`
(importable, re-runnable) and call it from a final notebook cell.

## 1. Map every claim to a test

For each hypothesis / exploratory item in goal.md, pick from:

| claim shape | helper | primary test | fallback | effect size |
|---|---|---|---|---|
| A vs B, same participants | `claim_pair(..., subject=)` | paired t | Wilcoxon signed-rank | Cohen's dz + bootstrap CI, raw Δ + CI |
| A vs B, different participants | `claim_pair` (no common subjects) | Welch / Student t (Levene decides) | Mann–Whitney U | Hedges' g + CI |
| k ≥ 3 conditions, within | `claim_anova(..., subject=)` | RM-ANOVA (+ Greenhouse–Geisser p) | Friedman | partial η², Cohen's f; Holm post-hoc pairs |
| k ≥ 3 conditions, between | `claim_anova` | one-way ANOVA | Kruskal–Wallis | η², ω², Cohen's f; Holm post-hoc |
| X relates to Y | `claim_corr` | Pearson r (Fisher-z CI) | Spearman ρ | r |

Aggregate to **one value per participant per condition** before testing unless
the design really has independent trials (repeated trials per participant are
not independent observations; say so in statistics.md if you deviate). Use the
same aggregation the figure uses.

Things the helpers do not cover (say so and either skip or hand-code): mixed
designs with two factors, Likert items (use ordinal tests / report distributions),
counts with many zeros (consider Poisson/negative-binomial GLM), time-to-event.

## 2. Recommend a minimal effect size per claim

Every claim gets a **recommended smallest effect size of interest (SESOI)**,
in standardized units, with its basis stated. `stats_helpers` computes:

- **MDE** — the minimal detectable effect at the study's N, α (default .05),
  target power (default .80), from the noncentral t / F distribution. Below this
  the study cannot reliably detect the effect regardless of whether it exists.
- **Author's raw SESOI** — pass `raw_sesoi=` (e.g. "one fewer takeover per
  trial", "5 s faster") and it is converted to standardized units using the
  relevant SD. Ask the user for this in the three questions if not obvious; a
  domain-meaningful number always beats a convention.
- **Recommended** = the larger of the two. Label with Cohen's benchmarks
  (d .2/.5/.8, f .1/.25/.4, r .1/.3/.5, η² .01/.06/.14) so readers can calibrate,
  but say explicitly that benchmarks are a fallback, not a justification.

Write one line per claim in statistics.md explaining the recommendation, e.g.
"H1: recommended minimal dz = 0.72 (medium–large). Basis: the author's SESOI of
1 takeover/trial is 0.55 SD, below the MDE for N = 12 at 80% power (0.87);
report as underpowered for smaller effects."

## 3. Verdicts

`finalize()` Holm-corrects the primary p across confirmatory claims (ids
starting with H; exploratory E* are uncorrected) and assigns:

- **supported** — p < α, effect ≥ SESOI, direction as hypothesized
- **significant but below minimal effect** — p < α but effect < SESOI (practical relevance doubtful)
- **not supported (effect within ±SESOI)** — CI entirely inside ±SESOI (equivalence-style)
- **not supported (wrong direction)**
- **inconclusive** — CI spans both 0 and the SESOI; underpowered

Never upgrade a verdict by switching tests after seeing the result; if the
parametric assumption chips fail, report the non-parametric fallback as primary
and say why.

## 4. statistics.md layout

```markdown
# Statistics — <study>
Data: <tables / cache files>, aggregation: <per participant × condition>, N = …
α = 0.05 (Holm across H1–Hk), target power = 0.80. Effect sizes with 95% CIs.

## Summary
| id | claim | figure | test | p (adj.) | effect [95% CI] | recommended min. effect | verdict |

## H1 — <claim>
- Descriptives: <table from `describe`>
- Test: <APA line from `sh.apa(c)`>; fallback: <Wilcoxon …>
- Assumptions: Shapiro p = …, Levene p = …, GG ε = … → <what was used>
- Recommended minimal effect: … (basis …); MDE = …
- Verdict: <verdict> — <verdict_note>
- Post-hoc (ANOVA only): pair, p_adj, effect
- Reading: one or two plain sentences a reviewer would accept.

## E1 — <exploratory>
(same, marked exploratory / uncorrected)

## Caveats
Multiple comparisons, dependence in trial-level data, exclusions, anything
hand-coded.
```

## 5. statistics.html

`python build_stats_html.py viz/statistics.json viz/statistics.html` renders:
a summary table, a forest plot of standardized effects with CIs against the
recommended minimal effect, and per claim a paired-change / means-with-CI
panel, box + points per group, test and descriptive tables, and assumption
chips. It is for the author and collaborators; the paper cites statistics.md.

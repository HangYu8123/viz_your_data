# plan.md layout

Write `viz/plan.md` in exactly this shape. One block per hypothesis / target /
fun result from goal.md, in the same order and with the same ids. Candidates are
ranked best-first; the score is your recommendation (10 = "this is the figure I
would put in the paper", 5 = "fine as a supplement", 2 = "only if the user has a
specific reason").

```markdown
# Visualization plan — <study name>

Data summary: <N participants, M sessions per condition, which sources parsed, any dropped sessions>.

## H1 — <hypothesis sentence copied from goal.md>

| rank | score | plot | x | y | z / extra encoding | width | purpose |
|---|---|---|---|---|---|---|---|
| 1 | 9 | box + jittered points | condition (C1–C3) | intervention_count per trial | color = condition; light lines connect the same participant across conditions | single | Show C3 < C1 with the raw spread visible, one glance |
| 2 | 7 | paired dot plot (per participant) | condition | intervention_count, participant mean | one line per participant | single | Emphasize within-subject consistency of the drop |
| 3 | 5 | grouped bar with 95% CI | condition | mean intervention_count | hue = task difficulty | single | Compact if space is tight; hides distribution |

Notes: error bars = 95% bootstrap CI; annotate Wilcoxon p between C1–C3 if the user wants stats markers; exclude P7 trial 2 (rosbag truncated).

## H2 — ...
(same table)

## E1 — <exploratory question>
(same table; scores are usually lower here — say if a static figure is a poor fit and the HTML report would serve better)

## Three questions before I build the notebook
1. <one sentence question>? (a) <option> (b) <option> (c) <option>
2. ...
3. ...
```

Guidance on filling it in:

- **x / y / z must be concrete column names or derived quantities**, with units,
  not "the metric". If a derived quantity needs computing, say how in the notes.
- **Purpose is the sentence the caption would end with.** If you can't write it,
  the plot isn't answering the hypothesis — pick another.
- Keep the ranking honest: a candidate that is prettier but hides the
  distribution (bars of means) should rank below one that shows it (box/violin +
  points), unless the user's venue or space constraints say otherwise.
- Prefer `single` width; use `double` for timelines, multi-panel comparisons, or
  anything with many x categories.
- The three questions should be the ones whose answers would change the figures
  most. Typical ones: per-trial vs per-participant aggregation; SD vs SEM vs 95% CI
  vs raw points; include significance stars or not; which condition is baseline;
  descriptive vs inferential depth; whether to normalize by trial length.

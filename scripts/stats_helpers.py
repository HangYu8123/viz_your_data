"""Statistics for the claims behind each figure — scipy-only, no statsmodels needed.

Typical use in viz/statistics.py (or a notebook cell):

    import stats_helpers as sh
    df = load_all()["trials"]           # tidy: participant, condition, trial, metrics...
    per_p = df.groupby(["participant", "condition"], as_index=False)["interventions"].mean()

    claims = [
        sh.claim_pair("H1", "Fewer takeovers with visual explanations (C3 < C1)",
                      per_p, dv="interventions", group="condition", a="C1", b="C3",
                      subject="participant", unit="count/trial", figure="F1",
                      raw_sesoi=1.0),                      # "1 fewer takeover per trial matters"
        sh.claim_anova("H2", "Completion time differs across conditions",
                       per_p, dv="time_s", group="condition", subject="participant",
                       unit="s", figure="F2"),
        sh.claim_corr("E1", "Trust correlates with completion time",
                      per_p, x="trust", y="time_s", subject="participant", figure="F4"),
    ]
    sh.finalize(claims, alpha=0.05, power=0.8, correction="holm")   # adds adjusted p and verdicts
    sh.write_json(claims, "viz/statistics.json", study="My study")

Every claim block is plain dicts/lists so it serialises to JSON for
build_stats_html.py and can be rendered into statistics.md.

Design notes
- Paired vs independent is decided by `subject`: if both groups have the same
  subjects we pair, otherwise we treat them as independent.
- Effect sizes: Cohen's dz (paired) / Hedges' g (independent) with bootstrap
  95% CI; eta² / partial eta² / omega² for ANOVA; r with Fisher-z CI.
- Minimal detectable effect (MDE) at the study's N is computed from the
  noncentral t / F distributions, so no external power package is needed.
- Recommended SESOI (smallest effect size of interest) = the larger of the
  domain-meaningful raw effect the author supplies (converted to standardized
  units) and the MDE. Reported with its basis so the reader can disagree.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import brentq

RNG = np.random.default_rng(0)
BOOT = 5000

# --------------------------------------------------------------------------- basics

def _clean(x) -> np.ndarray:
    return np.asarray(pd.Series(x).dropna(), dtype=float)


def describe(df: pd.DataFrame, dv: str, group: str) -> list[dict]:
    rows = []
    for g, s in df.groupby(group, sort=False)[dv]:
        x = _clean(s)
        n = len(x)
        sem = x.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
        tcrit = stats.t.ppf(0.975, n - 1) if n > 1 else float("nan")
        rows.append({"group": str(g), "n": int(n), "mean": float(x.mean()), "sd": float(x.std(ddof=1)) if n > 1 else float("nan"),
                     "median": float(np.median(x)), "q1": float(np.percentile(x, 25)), "q3": float(np.percentile(x, 75)),
                     "sem": float(sem), "ci95": [float(x.mean() - tcrit * sem), float(x.mean() + tcrit * sem)]})
    return rows


def shapiro_p(x) -> float | None:
    x = _clean(x)
    if len(x) < 3 or np.ptp(x) == 0:
        return None
    return float(stats.shapiro(x).pvalue)


def _boot_ci(fn, *arrays, n=BOOT) -> list[float]:
    vals = []
    idx = [np.arange(len(a)) for a in arrays]
    paired = len(set(len(a) for a in arrays)) == 1
    for _ in range(n):
        if paired:
            i = RNG.integers(0, len(arrays[0]), len(arrays[0]))
            samples = [a[i] for a in arrays]
        else:
            samples = [a[RNG.integers(0, len(a), len(a))] for a in arrays]
        try:
            vals.append(fn(*samples))
        except Exception:
            continue
    return [float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))]


def cohen_dz(a, b) -> float:
    d = np.asarray(a) - np.asarray(b)
    return float(d.mean() / d.std(ddof=1))


def hedges_g(a, b) -> float:
    a, b = np.asarray(a), np.asarray(b)
    n1, n2 = len(a), len(b)
    sp = math.sqrt(((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1)) / (n1 + n2 - 2))
    d = (a.mean() - b.mean()) / sp
    j = 1 - 3 / (4 * (n1 + n2) - 9)
    return float(d * j)


# --------------------------------------------------------------------------- power / MDE

def mde_d(n: int, design: str = "paired", alpha: float = 0.05, power: float = 0.8, n2: int | None = None) -> float:
    """Smallest Cohen's d detectable with given n at (alpha, power), two-sided.

    design='paired'  : n pairs, dz units.
    design='independent': n and n2 per group, d units.
    """
    if design == "paired":
        df = n - 1
        def pw(d):
            nc = d * math.sqrt(n)
            tc = stats.t.ppf(1 - alpha / 2, df)
            return 1 - stats.nct.cdf(tc, df, nc) + stats.nct.cdf(-tc, df, nc)
    else:
        n2 = n2 or n
        df = n + n2 - 2
        def pw(d):
            nc = d * math.sqrt(n * n2 / (n + n2))
            tc = stats.t.ppf(1 - alpha / 2, df)
            return 1 - stats.nct.cdf(tc, df, nc) + stats.nct.cdf(-tc, df, nc)
    if df < 1:
        return float("nan")
    return float(brentq(lambda d: pw(d) - power, 1e-4, 10))


def mde_f(k: int, n_per_group: int, alpha: float = 0.05, power: float = 0.8, within: bool = False) -> float:
    """Smallest Cohen's f detectable for a k-level factor (one-way between, or one within factor)."""
    if within:
        df1, df2 = k - 1, (k - 1) * (n_per_group - 1)
        ntot = n_per_group * k
    else:
        df1, df2 = k - 1, k * (n_per_group - 1)
        ntot = k * n_per_group
    if df2 < 1:
        return float("nan")
    fc = stats.f.ppf(1 - alpha, df1, df2)
    def pw(f):
        return 1 - stats.ncf.cdf(fc, df1, df2, f * f * ntot)
    return float(brentq(lambda f: pw(f) - power, 1e-4, 10))


def mde_r(n: int, alpha: float = 0.05, power: float = 0.8) -> float:
    """Smallest |r| detectable with n pairs (Fisher-z approximation)."""
    if n < 4:
        return float("nan")
    za, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    z = (za + zb) / math.sqrt(n - 3)
    return float(math.tanh(z))


def cohens_label(kind: str, v: float) -> str:
    v = abs(v)
    th = {"d": (0.2, 0.5, 0.8), "f": (0.1, 0.25, 0.4), "r": (0.1, 0.3, 0.5), "eta2": (0.01, 0.06, 0.14)}[kind]
    return "negligible" if v < th[0] else "small" if v < th[1] else "medium" if v < th[2] else "large"


# --------------------------------------------------------------------------- claims

def _pair_arrays(df, dv, group, a, b, subject):
    if subject and subject in df.columns:
        pa = df[df[group] == a].set_index(subject)[dv]
        pb = df[df[group] == b].set_index(subject)[dv]
        common = pa.index.intersection(pb.index)
        if len(common) >= 3 and len(common) >= 0.8 * min(len(pa), len(pb)):
            return _clean(pa.loc[common]), _clean(pb.loc[common]), True, [str(s) for s in common]
    return _clean(df[df[group] == a][dv]), _clean(df[df[group] == b][dv]), False, None


def claim_pair(cid: str, claim: str, df: pd.DataFrame, dv: str, group: str, a: str, b: str,
               subject: str | None = None, unit: str = "", figure: str = "",
               raw_sesoi: float | None = None, direction: str = "two-sided") -> dict:
    """Two-condition comparison (a vs b). direction: 'two-sided' | 'a>b' | 'a<b' (used for the verdict only)."""
    xa, xb, paired, subjects = _pair_arrays(df, dv, group, a, b, subject)
    n = len(xa)
    tests, assumptions = [], {}
    if paired:
        t = stats.ttest_rel(xa, xb)
        tests.append({"name": "paired t-test", "statistic": float(t.statistic), "df": n - 1, "p": float(t.pvalue)})
        try:
            w = stats.wilcoxon(xa, xb)
            tests.append({"name": "Wilcoxon signed-rank", "statistic": float(w.statistic), "p": float(w.pvalue)})
        except ValueError:
            pass
        eff = {"type": "cohen_dz", "value": cohen_dz(xa, xb), "ci": _boot_ci(cohen_dz, xa, xb)}
        diff = xa - xb
        eff.update({"raw_diff": float(diff.mean()), "raw_ci": list(map(float, stats.t.interval(0.95, n - 1, diff.mean(), stats.sem(diff))))})
        assumptions["shapiro_diff_p"] = shapiro_p(diff)
        mde = mde_d(n, "paired")
        sd_for_sesoi = float(diff.std(ddof=1))
    else:
        lev = stats.levene(xa, xb)
        equal = lev.pvalue > 0.05
        t = stats.ttest_ind(xa, xb, equal_var=equal)
        tests.append({"name": "independent t-test" if equal else "Welch t-test", "statistic": float(t.statistic),
                      "df": float(getattr(t, "df", len(xa) + len(xb) - 2)), "p": float(t.pvalue)})
        u = stats.mannwhitneyu(xa, xb, alternative="two-sided")
        tests.append({"name": "Mann-Whitney U", "statistic": float(u.statistic), "p": float(u.pvalue)})
        eff = {"type": "hedges_g", "value": hedges_g(xa, xb), "ci": _boot_ci(hedges_g, xa, xb)}
        eff.update({"raw_diff": float(xa.mean() - xb.mean()),
                    "raw_ci": list(map(float, _boot_ci(lambda p, q: p.mean() - q.mean(), xa, xb)))})
        assumptions.update({"shapiro_a_p": shapiro_p(xa), "shapiro_b_p": shapiro_p(xb), "levene_p": float(lev.pvalue)})
        mde = mde_d(len(xa), "independent", n2=len(xb))
        sd_for_sesoi = float(math.sqrt((xa.var(ddof=1) + xb.var(ddof=1)) / 2))
    sesoi = _sesoi(mde, raw_sesoi, sd_for_sesoi, "d")
    return {"id": cid, "claim": claim, "kind": "pair", "figure": figure, "dv": dv, "unit": unit,
            "design": "paired" if paired else "independent", "groups": {a: xa.tolist(), b: xb.tolist()},
            "subjects": subjects, "descriptives": describe(pd.DataFrame({group: [a] * len(xa) + [b] * len(xb), dv: np.r_[xa, xb]}), dv, group),
            "tests": tests, "effect": eff, "assumptions": assumptions, "sesoi": sesoi, "direction": direction}


def _gg_epsilon(wide: np.ndarray) -> float:
    """Greenhouse–Geisser epsilon from an n×k matrix of within-subject scores."""
    k = wide.shape[1]
    S = np.cov(wide, rowvar=False)
    C = np.eye(k) - np.ones((k, k)) / k
    D = C @ S @ C
    tr = np.trace(D)
    return float(tr ** 2 / ((k - 1) * np.sum(D * D)))


def claim_anova(cid: str, claim: str, df: pd.DataFrame, dv: str, group: str, subject: str | None = None,
                unit: str = "", figure: str = "", raw_sesoi: float | None = None) -> dict:
    """k-level factor. Repeated-measures if every subject has every level, else one-way between."""
    levels = list(pd.unique(df[group]))
    k = len(levels)
    groups = {str(g): _clean(df[df[group] == g][dv]).tolist() for g in levels}
    tests, assumptions = [], {}
    within = False
    if subject and subject in df.columns:
        wide = df.pivot_table(index=subject, columns=group, values=dv, aggfunc="mean").dropna()
        within = len(wide) >= 3 and wide.shape[1] == k
    if within:
        W = wide[levels].to_numpy()
        n = W.shape[0]
        gm = W.mean()
        ss_cond = n * ((W.mean(0) - gm) ** 2).sum()
        ss_subj = k * ((W.mean(1) - gm) ** 2).sum()
        ss_tot = ((W - gm) ** 2).sum()
        ss_err = ss_tot - ss_cond - ss_subj
        df1, df2 = k - 1, (k - 1) * (n - 1)
        F = (ss_cond / df1) / (ss_err / df2)
        eps = _gg_epsilon(W)
        p = float(stats.f.sf(F, df1, df2))
        p_gg = float(stats.f.sf(F, df1 * eps, df2 * eps))
        tests.append({"name": "repeated-measures ANOVA", "statistic": float(F), "df": [df1, df2], "p": p,
                      "p_gg": p_gg, "gg_epsilon": eps})
        fr = stats.friedmanchisquare(*[W[:, j] for j in range(k)])
        tests.append({"name": "Friedman", "statistic": float(fr.statistic), "p": float(fr.pvalue)})
        pes = float(ss_cond / (ss_cond + ss_err))
        eff = {"type": "partial_eta2", "value": pes, "cohen_f": float(math.sqrt(pes / (1 - pes))) if pes < 1 else float("nan")}
        assumptions.update({"sphericity_gg_epsilon": eps, "shapiro_resid_p": shapiro_p((W - W.mean(1, keepdims=True) - W.mean(0) + gm).ravel())})
        mde = mde_f(k, n, within=True)
        sd_for_sesoi = float(math.sqrt(ss_err / df2))
        n_report = n
        post = _posthoc_pairs(wide, levels, paired=True)
    else:
        arrs = [np.asarray(groups[str(g)]) for g in levels]
        F, p = stats.f_oneway(*arrs)
        gm = np.concatenate(arrs).mean()
        ss_b = sum(len(x) * (x.mean() - gm) ** 2 for x in arrs)
        ss_w = sum(((x - x.mean()) ** 2).sum() for x in arrs)
        N = sum(len(x) for x in arrs)
        df1, df2 = k - 1, N - k
        tests.append({"name": "one-way ANOVA", "statistic": float(F), "df": [df1, df2], "p": float(p)})
        kw = stats.kruskal(*arrs)
        tests.append({"name": "Kruskal-Wallis", "statistic": float(kw.statistic), "p": float(kw.pvalue)})
        eta2 = float(ss_b / (ss_b + ss_w))
        omega2 = float((ss_b - df1 * ss_w / df2) / (ss_b + ss_w + ss_w / df2))
        eff = {"type": "eta2", "value": eta2, "omega2": omega2, "cohen_f": float(math.sqrt(eta2 / (1 - eta2)))}
        assumptions.update({"levene_p": float(stats.levene(*arrs).pvalue), **{f"shapiro_{g}_p": shapiro_p(x) for g, x in zip(levels, arrs)}})
        mde = mde_f(k, int(np.mean([len(x) for x in arrs])), within=False)
        sd_for_sesoi = float(math.sqrt(ss_w / df2))
        n_report = N
        post = _posthoc_pairs(None, levels, paired=False, arrays=dict(zip(map(str, levels), arrs)))
    sesoi = _sesoi(mde, raw_sesoi, sd_for_sesoi, "f")
    return {"id": cid, "claim": claim, "kind": "anova", "figure": figure, "dv": dv, "unit": unit,
            "design": "within" if within else "between", "levels": list(map(str, levels)), "n": int(n_report),
            "groups": groups, "descriptives": describe(df, dv, group), "tests": tests, "effect": eff,
            "assumptions": assumptions, "posthoc": post, "sesoi": sesoi}


def _posthoc_pairs(wide, levels, paired: bool, arrays: dict | None = None) -> list[dict]:
    out = []
    for i in range(len(levels)):
        for j in range(i + 1, len(levels)):
            a, b = levels[i], levels[j]
            if paired:
                xa, xb = wide[a].to_numpy(), wide[b].to_numpy()
                t = stats.ttest_rel(xa, xb)
                out.append({"pair": [str(a), str(b)], "test": "paired t", "p": float(t.pvalue), "effect": cohen_dz(xa, xb), "effect_type": "cohen_dz"})
            else:
                xa, xb = arrays[str(a)], arrays[str(b)]
                t = stats.ttest_ind(xa, xb, equal_var=False)
                out.append({"pair": [str(a), str(b)], "test": "Welch t", "p": float(t.pvalue), "effect": hedges_g(xa, xb), "effect_type": "hedges_g"})
    padj = holm([o["p"] for o in out])
    for o, q in zip(out, padj):
        o["p_adj"] = q
    return out


def claim_corr(cid: str, claim: str, df: pd.DataFrame, x: str, y: str, subject: str | None = None,
               figure: str = "", raw_sesoi: float | None = None, unit_x: str = "", unit_y: str = "") -> dict:
    d = df[[x, y] + ([subject] if subject and subject in df.columns else [])].dropna()
    xs, ys = d[x].to_numpy(float), d[y].to_numpy(float)
    n = len(xs)
    pr = stats.pearsonr(xs, ys)
    sr = stats.spearmanr(xs, ys)
    z = np.arctanh(pr.statistic); se = 1 / math.sqrt(max(n - 3, 1))
    ci = [float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))]
    slope, intercept = np.polyfit(xs, ys, 1)
    mde = mde_r(n)
    sesoi = _sesoi(mde, raw_sesoi, None, "r")
    return {"id": cid, "claim": claim, "kind": "correlation", "figure": figure, "x": x, "y": y, "unit_x": unit_x, "unit_y": unit_y, "n": int(n),
            "points": [[float(a), float(b), str(s)] for a, b, s in zip(xs, ys, d[subject] if subject and subject in d.columns else [""] * n)],
            "tests": [{"name": "Pearson r", "statistic": float(pr.statistic), "p": float(pr.pvalue)},
                      {"name": "Spearman rho", "statistic": float(sr.statistic), "p": float(sr.pvalue)}],
            "effect": {"type": "r", "value": float(pr.statistic), "ci": ci, "slope": float(slope), "intercept": float(intercept)},
            "assumptions": {"shapiro_x_p": shapiro_p(xs), "shapiro_y_p": shapiro_p(ys)}, "sesoi": sesoi}


def _sesoi(mde: float, raw_sesoi: float | None, sd: float | None, kind: str) -> dict:
    """Recommended minimal effect: max(domain raw effect in standardized units, MDE)."""
    out = {"mde": float(mde), "mde_label": cohens_label(kind, mde) if not math.isnan(mde) else "n/a", "kind": kind}
    std_raw = None
    if raw_sesoi is not None and sd:
        std_raw = float(raw_sesoi / sd)
        out["raw_sesoi"] = float(raw_sesoi)
        out["raw_sesoi_standardized"] = std_raw
    if std_raw is not None and std_raw >= mde:
        out.update({"recommended": std_raw, "basis": "domain-meaningful raw effect supplied by the author (≥ MDE)"})
    elif std_raw is not None:
        out.update({"recommended": float(mde), "basis": f"MDE at 80% power; the author's raw SESOI ({std_raw:.2f} std) is below what this N can detect"})
    else:
        out.update({"recommended": float(mde), "basis": "MDE at 80% power for this N (no domain SESOI supplied)"})
    out["recommended_label"] = cohens_label(kind, out["recommended"])
    return out


# --------------------------------------------------------------------------- corrections / verdicts

def holm(p: Sequence[float]) -> list[float]:
    p = np.asarray(p, float)
    m = len(p)
    if m == 0:
        return []
    order = np.argsort(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj.tolist()


def finalize(claims: list[dict], alpha: float = 0.05, power: float = 0.8, correction: str = "holm") -> list[dict]:
    """Adjust primary p-values across confirmatory claims (ids starting with H) and attach verdicts."""
    conf = [c for c in claims if str(c["id"]).upper().startswith("H")]
    ps = [c["tests"][0]["p"] for c in conf]
    adj = holm(ps) if correction == "holm" else [min(1.0, p * len(ps)) for p in ps] if correction == "bonferroni" else ps
    for c, q in zip(conf, adj):
        c["tests"][0]["p_adj"] = float(q)
    for c in claims:
        c["alpha"], c["power"] = alpha, power
        c["verdict"], c["verdict_note"] = _verdict(c, alpha)
    return claims


def _verdict(c: dict, alpha: float) -> tuple[str, str]:
    p = c["tests"][0].get("p_adj", c["tests"][0]["p"])
    eff = c["effect"]; ses = c["sesoi"]["recommended"]
    v = abs(eff["value"]) if c["kind"] != "anova" else eff.get("cohen_f", float("nan"))
    ci = eff.get("ci")
    d = c.get("direction", "two-sided")
    sign_ok = True
    if c["kind"] == "pair" and d != "two-sided":
        sign_ok = (eff["raw_diff"] > 0) if d == "a>b" else (eff["raw_diff"] < 0)
    if p < alpha and v >= ses and sign_ok:
        return "supported", f"p={p:.3g} < α, effect {v:.2f} ≥ SESOI {ses:.2f}"
    if p < alpha and sign_ok:
        return "significant but below minimal effect", f"p={p:.3g} < α but effect {v:.2f} < SESOI {ses:.2f}; may not be practically meaningful"
    if ci and (abs(ci[0]) < ses and abs(ci[1]) < ses):
        return "not supported (effect within ±SESOI)", f"95% CI [{ci[0]:.2f}, {ci[1]:.2f}] lies inside ±SESOI {ses:.2f}"
    if not sign_ok:
        return "not supported (wrong direction)", f"observed effect goes against the hypothesized direction ({d})"
    return "inconclusive", f"p={p:.3g}; CI overlaps both 0 and SESOI — underpowered for this effect"


def write_json(claims: list[dict], path: str | Path, study: str = "", extra: dict | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"study": study, "claims": claims, **(extra or {})}
    path.write_text(json.dumps(doc, indent=1, default=_json_default))
    return path


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def fmt_p(p: float) -> str:
    return "< .001" if p < 0.001 else f"= {p:.3f}"


def apa(c: dict) -> str:
    """One APA-style sentence per claim for statistics.md."""
    t = c["tests"][0]; e = c["effect"]
    if c["kind"] == "pair":
        ci = e["ci"]
        return (f"{t['name']}: t({t['df']:.0f}) = {t['statistic']:.2f}, p {fmt_p(t.get('p_adj', t['p']))}, "
                f"{'dz' if e['type']=='cohen_dz' else 'g'} = {e['value']:.2f} [{ci[0]:.2f}, {ci[1]:.2f}], "
                f"Δ = {e['raw_diff']:.2f} {c['unit']} [{e['raw_ci'][0]:.2f}, {e['raw_ci'][1]:.2f}]")
    if c["kind"] == "anova":
        d1, d2 = t["df"]
        gg = f" (GG ε = {t['gg_epsilon']:.2f}, p_GG {fmt_p(t['p_gg'])})" if "p_gg" in t else ""
        return (f"{t['name']}: F({d1:.0f}, {d2:.0f}) = {t['statistic']:.2f}, p {fmt_p(t.get('p_adj', t['p']))}{gg}, "
                f"{'ηp²' if e['type']=='partial_eta2' else 'η²'} = {e['value']:.3f}, f = {e['cohen_f']:.2f}")
    ci = e["ci"]
    return f"Pearson r({c['n']-2}) = {e['value']:.2f} [{ci[0]:.2f}, {ci[1]:.2f}], p {fmt_p(t['p'])}; Spearman ρ = {c['tests'][1]['statistic']:.2f}, p {fmt_p(c['tests'][1]['p'])}"

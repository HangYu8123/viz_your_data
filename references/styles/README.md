# Reference visualization styles

A small knowledge base of figures from recent papers whose *look* is worth
borrowing, each with the actual image (PNG, plus the vector source PDF where
arXiv provided it), a style analysis, and a palette you can apply in one line:

```python
import ieee_style as st
st.use_palette("memory_anchors")      # colors + markers cycle
st.apply_preset("deepseek")           # optional: fonts / grid / hatch conventions of that paper
```

Consult this library in **Step 2** (planning): every candidate in `plan.md`
should name a style reference (`style: memory_anchors/fig6`) when one fits, and
in **Step 3** apply its palette / preset. The researcher agent also receives
this list as seeds. Match the *purpose* of the reference figure, not its topic:
a robot-learning bar chart and an HRI questionnaire bar chart want the same
treatment.

| id | paper | figures | best for | palette |
|---|---|---|---|---|
| `rosetta` | ROSETTA: Constructing Code-Based Reward from Unconstrained Language Preference (RSS 2025 workshop, best paper) | [Fig. 4](rosetta/analysis.md#fig-4), [Fig. 5](rosetta/analysis.md#fig-5) | grouped bars with error bars across categories × methods; binary presence matrix + annotated examples | `rosetta` (4 pastel hues, black edges) |
| `deepseek` | DeepSeek-V3 Technical Report (arXiv 2412.19437) · DeepSeek-R1 (arXiv 2501.12948) | [V3 Fig. 1](deepseek/analysis.md#v3-fig-1), [V3 Fig. 8](deepseek/analysis.md#v3-fig-8), [R1 Fig. 1](deepseek/analysis.md#r1-fig-1), [R1 Fig. 2](deepseek/analysis.md#r1-fig-2) | "ours vs baselines" benchmark bars with a hatched hero bar; training curves with raw+smoothed band; pipeline block diagrams | `deepseek` (royal-blue hero, blue tints, neutral competitors) |
| `cambrian_s` | Cambrian-S: Towards Spatial Supersensing in Video (arXiv 2511.04670) | [Fig. 2](cambrian_s/analysis.md#fig-2), [Fig. 7](cambrian_s/analysis.md#fig-7) | small-multiples diagnostics with signed, sorted difference bars; data-pipeline diagram with real thumbnails | `cambrian_s` (gray baseline, blue positive, orange negative) |
| `cosmos3` | Cosmos 3: Omnimodal World Models for Physical AI (NVIDIA, arXiv 2606.02800) | [Fig. 6](cosmos3/analysis.md#fig-6), [Fig. 7](cosmos3/analysis.md#fig-7) | token/sequence schematics with per-modality tints; donut composition charts with leader-line labels | `cosmos3_modality`, `cosmos3_categorical` |
| `memory_anchors` | Memory Anchors for Continual Robot Learning (arXiv 2608.26545) | [Fig. 5](memory_anchors/analysis.md#fig-5), [Fig. 6](memory_anchors/analysis.md#fig-6), [Fig. 7](memory_anchors/analysis.md#fig-7) | two-concept method diagrams (old vs new); grouped bars with ablation ramps and in-plot takeaway text; photo panels + result matrices | `memory_anchors` (teal vs orange + gray ramp), `memory_anchors_seq` (blue sequential) |

`palettes.png` shows all swatches side by side. `demo_memory_anchors.png` and
`demo_deepseek.png` are single-column matplotlib reproductions of two of the
reference treatments made with `ieee_style` only, to show what the presets give
you out of the box.

## Cross-cutting lessons (what these papers agree on)

1. **One hero color, everything else recedes.** DeepSeek's royal blue + hatching,
   Memory Anchors' teal, Cambrian-S's blue-vs-orange on a gray baseline. Baselines
   are grays or tints, never a second saturated hue competing for attention.
2. **Value labels on bars when the numbers matter** (DeepSeek V3 Fig. 1, Memory
   Anchors Fig. 6); the y axis then becomes secondary and can be lightly gridded.
3. **Say the takeaway inside the figure**: italic colored sentence (Memory
   Anchors), bold panel titles that are conclusions (Cambrian-S "diff(...)"),
   curved annotation arrows "Reduced Forgetting" / "Catastrophic Forgetting".
4. **Error bars are thin, black, capped**; bars have thin black or white edges so
   pastel fills stay crisp when printed.
5. **Sort where order is not semantic** (Cambrian-S sorts difference bars) so the
   eye reads a monotone shape, not a jumble.
6. **Tints of one hue encode ordinal strength** (RandER −1/−5/−10 %: light → dark
   gray; AnchorER 10/20 %: light → dark orange) instead of new hues.
7. **Diagrams reuse the plot palette**: the concept colors in a method figure
   (old = orange, new = teal) are the same colors in the results bars, so the
   reader carries the mapping across the paper.
8. **Text is large relative to marks** in all of them (≥ 8 pt at final size);
   axis labels carry units and direction ("NBT Average (Lower Better)").

## Attribution and licensing

The images in this folder are © their authors and are included solely as
style references for research use; cite the papers, not this folder. arXiv
papers are distributed under the authors' chosen license (check each abstract
page); the ROSETTA figures come from the OpenReview PDF. Do not reuse the images
themselves in publications.

- ROSETTA — Srivastava, Wang, Chan et al. https://openreview.net/forum?id=xuDPUN7Ud4
- DeepSeek-V3 — https://arxiv.org/abs/2412.19437 · DeepSeek-R1 — https://arxiv.org/abs/2501.12948
- Cambrian-S — Yang, Yang et al. https://arxiv.org/abs/2511.04670
- Cosmos 3 — NVIDIA. https://arxiv.org/abs/2606.02800
- Memory Anchors — Du, Sun, Xu, Shah, Itkina, Song. https://arxiv.org/abs/2608.26545

Figure numbers follow the PDF as published (Memory Anchors' PDF numbering differs
from its LaTeX source by one; the files here are the PDF's Figures 5–7).

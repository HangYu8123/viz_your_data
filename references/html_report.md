# Interactive HTML report pattern

Purpose: exploration and intuition for the user, not a paper figure. Build it
only when asked or when the data clearly benefits (per-trial time series, many
participants, interactions). Always say in the message that it is exploratory.

Keep it a single self-contained file `viz/report.html`:

- Load Plotly from cdnjs (pin a version that exists — 3.0.1 is verified; check
  `https://api.cdnjs.com/libraries/plotly.js` before pinning another), e.g.
  `<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/3.0.1/plotly.min.js"></script>`.
  Embed the data as a JSON literal in a `<script>` tag (write it from Python with
  `df.to_json(orient="records")`); no fetches, so the file works from disk.
- One section per hypothesis / exploratory question, same ids as `plan.md`, each
  with a one-line "what to look for" above the chart.
- Interactions that earn their place: hover showing participant / trial ids,
  legend-click to isolate a condition, a dropdown to switch metric, per-participant
  traces overlaid on the aggregate, range slider on time series.
- Use the same palette and condition ordering as the notebook so the two agree.
- Include a small "data quality" table at the top: sessions per condition,
  dropped sessions with reasons, parse warnings.

Generate it from a python script (`viz/make_report.py`) rather than by hand so
it can be regenerated after parser fixes. If the Artifact tool is available and
the user wants a shareable link, publish the same file as an artifact.

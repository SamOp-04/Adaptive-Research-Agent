# Skill: Chart Output

Inherits tokens from `../DESIGN.md`. Read that first.

## When this is used

Router picks `chart` when findings carry numeric/trend structure — time series, growth
rates, distributions, metric comparisons with extractable values. See `NUMERIC_RE` and
the late LLM check in `backend/nodes/output_router.py`. Rule of thumb: if the answer's
core content is "how has X changed" or "how do these numbers compare," it's a chart.

**Do not use chart for:** categorical comparisons with no shared numeric axis (that's
table) — e.g. "pros and cons of X vs Y" is table even though it's "comparative,"
because there's nothing to plot.

## Data contract

Currently (`_build_artifact`):
```json
{
  "type": "chart",
  "data": [{ "label": "...", "value": N, "credibility": 0.81 }]
}
```
Max 8 points (`findings[:8]`). If the synthesis node is ever extended to extract real
numeric series (e.g. actual year-over-year values instead of placeholder metrics), keep
this contract shape — just populate `value` with the real extracted number instead of a
placeholder.

## Structure rules

- **Chart type default:** bar chart (Recharts `BarChart`) unless the data is explicitly
  a time series (has a date/year dimension), in which case use a line chart instead —
  don't force trend data into bars.
- **Bar/line color:** `var(--app-accent)` (teal-700, `#0f766e`) — single-series charts
  use one color, not a rainbow palette. If a future multi-series chart is needed, use
  the accent plus two steps of the credibility scale (`--cred-medium`, `--cred-low`) as
  a 3-color max palette, in that order, so it stays inside the existing token set instead
  of introducing new colors.
- **Axis labels:** `text-xs`, `var(--app-text-secondary)`, never rotated — if labels
  don't fit horizontally, they're too long for a chart; that data belongs in a table
  instead.
- **Tooltip:** on hover, show the full finding text (title/snippet) that the bar/point
  represents, not just the numeric value — the chart is a summary, the tooltip is where
  the source context lives. Style: `var(--app-panel)` background, `var(--app-border)`
  border, `text-xs`, max-width so long snippets wrap instead of overflowing.
- **No 3D, no gradients, no drop shadows on bars** — flat fills only.
- **Empty/low-confidence state:** if fewer than 3 data points, don't render a chart at
  all — fall back to a one-line text summary. A 2-bar chart isn't a visualization, it's
  a sentence pretending to be a chart.

## Do / Don't

✅ A 6-point bar chart of "renewable capacity by year," teal bars, hover tooltip showing the source snippet behind each value.
❌ A pie chart (not in the token/pattern set — bar/line only, keeps every chart legible and consistent).
❌ Rotated axis labels to cram in long category names.
❌ Rendering a chart for 2 data points.

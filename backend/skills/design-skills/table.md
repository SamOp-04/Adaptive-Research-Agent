# Skill: Table Output

Inherits tokens from `../DESIGN.md`. Read that first.

## When this is used

Router picks `table` when findings are comparative — multiple items evaluated against
shared criteria (vendors, options, features, rankings). See
`backend/nodes/output_router.py`'s `COMPARATIVE_RE` gate and the late LLM check for the
exact trigger logic. Rule of thumb: if the answer could be read as "X has A, Y has B,
Z has C" across 3+ items, it's a table.

**Do not use table for:** a single item's attributes (that's short-text or a simple
list), or a narrative timeline (that's chart if numeric, long-text if not).

## Data contract

Backend (`_build_artifact` in `output_router.py`) sends:
```json
{
  "type": "table",
  "columns": ["title", "url", "credibility"],
  "rows": [{ "title": "...", "url": "...", "credibility": 0.81 }]
}
```

Frontend (`TableArtifact.tsx`, TanStack Table) renders it. If you extend `columns` beyond
the current three (e.g. adding extracted comparison fields like price/rating), keep the
row count capped — see Row Limits below.

## Structure rules

- **Header row:** `var(--app-text-secondary)`, `text-xs`, medium weight, left-aligned, bottom border `var(--app-border)` — never bold-black, headers should recede compared to data.
- **Row separator:** hairline `var(--app-border)`, not zebra-striping. Zebra striping reads as "spreadsheet," this is a research artifact.
- **Row height:** compact — `py-2`. This is a scan-and-compare tool, not a document to linger on.
- **Credibility column:** always rendered as the shared credibility badge (see DESIGN.md §4), never a raw number, never the last column — put it second, right after the title, so trust is visible before the user reads the URL.
- **URL column:** truncate to domain only in the cell (`example.com`, not the full path); full URL goes in `href`/tooltip.
- **Row limit:** 12 rows max (matches current backend cap `findings[:12]`). If more sources exist, show "+N more sources" as a final row, not a scroll — tables should fit in one view.
- **Sort:** rows arrive pre-sorted by credibility descending from the backend; don't re-sort client-side unless the user clicks a header.

## Do / Don't

✅ A 4-row vendor comparison with title, credibility badge, and truncated domain, sorted highest-credibility first.
❌ A 20-row unfiltered dump of every search result regardless of credibility score.
❌ Raw `0.734` shown in a cell instead of a "Medium" badge.
❌ Alternating row background colors.

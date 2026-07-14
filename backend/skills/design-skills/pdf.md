# Skill: PDF Output

Inherits tokens from `../DESIGN.md`. Read that first — this format renders the tokens
most literally since it's built from raw HTML/CSS via WeasyPrint.

## When this is used

Same rule as DOCX: **explicit user request only** ("pdf," "give me a pdf"), never
auto-inferred. See `output_router.py`'s explicit exclusion of docx/pdf from the late
refinement check.

**PDF vs DOCX — when a user asks for "a document" without naming a format:** default to
PDF. It's the more universally viewable format and doesn't imply the user wants to
*edit* it — Word implies editing, PDF implies reading/sharing. Only build DOCX when the
user's language suggests they intend to modify it further (e.g. "give me a doc I can
edit," "word doc").

## Structure rules

Built in `backend/files/pdf_generator.py` via WeasyPrint (HTML → PDF). Same section
order as DOCX for consistency between the two document types — a user who gets one of
each shouldn't be confused why they look organized differently:

1. Title (`<h1>`)
2. Summary (`<h2>` + prose)
3. Key Findings (`<h2>` + `<ul>`)
4. Sources (`<h2>` + `<ul>`, same credibility-tag-before-title convention as DOCX)

## Style rules — update `TEMPLATE` in `pdf_generator.py` to match these exactly

```css
body { font-family: 'Inter', 'Helvetica', sans-serif; margin: 40px; color: #1a1a1a; }
h1 { font-size: 22px; color: #0f766e; border-bottom: 2px solid #0f766e; padding-bottom: 8px; }
h2 { font-size: 16px; margin-top: 24px; color: #1a1a1a; border-bottom: 1px solid #e5e5e3; padding-bottom: 4px; }
li { margin-bottom: 6px; font-size: 13px; }
.source { font-size: 11px; color: #6b6b68; }
.cred-badge { font-size: 10px; font-weight: 600; margin-right: 6px; }
.cred-high { color: #0f766e; }
.cred-medium { color: #b45309; }
.cred-low { color: #9ca3af; }
```

(This is a direct translation of the current template plus the DESIGN.md token values —
the current implementation already matches most of this; the main gap is the missing
credibility badge classes, same gap as DOCX.)

- **Page size:** Letter/A4 default, no custom page dimensions.
- **No header/footer branding, no page numbers** unless the document exceeds 2 pages — for short single-query reports, chrome adds noise without adding usability.
- **Links:** source URLs should remain live/clickable in the PDF (WeasyPrint preserves `<a>` hrefs by default) — don't flatten them to plain text.

## Do / Don't

✅ Same visual language as the DOCX output — same heading color, same credibility convention — so the two document formats read as siblings, not unrelated tools.
❌ A different accent color or font between the DOCX and PDF outputs.
❌ Page numbers/headers on a one-page summary.

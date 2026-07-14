# Design System — Adaptive Research Agent

This is the shared token set every output-type skill file (`skills/*.md`) inherits from.
Skill files should never invent their own colors, spacing, or type sizes — they reference
these tokens and add only the structural/layout rules specific to their format.

Purpose of this split: the output router decides *which* skill applies (text/chart/table/
docx/pdf). Once decided, the builder for that type should be able to produce a correctly
styled artifact by reading only this file + its own skill file — no guessing, no drifting
from what other artifact types look like.

---

## 1. Color Tokens

Defined as CSS custom properties in `frontend/app/globals.css`, consumed everywhere —
never hardcode a hex value in a component; reference the variable.

```css
:root {
  --app-bg: #ffffff;
  --app-panel: #f7f7f6;
  --app-border: #e5e5e3;
  --app-text-primary: #1a1a1a;
  --app-text-secondary: #6b6b68;
  --app-accent: #0f766e;       /* teal-700 — primary accent, already in use */
  --app-accent-hover: #0d5f58;

  /* Credibility scale — maps to skills/source_evaluation.py score bands */
  --cred-high: #0f766e;        /* score >= 0.75 — same as accent, signals trust */
  --cred-medium: #b45309;      /* 0.5–0.74 — amber, caution not alarm */
  --cred-low: #9ca3af;         /* < 0.5 — neutral gray, not red (red = error, not distrust) */
}
```

**Rule:** credibility is never shown as red. Red is reserved for actual errors (failed
steps, failed searches). A low-credibility source is still a real result — gray signals
"weigh this less," not "something broke."

## 2. Typography

Font: Inter (already set in `tailwind.config.ts`). One scale, used everywhere:

| Token | Size | Use |
|---|---|---|
| `text-xs` (12px) | Metadata — timestamps, source domains, step trace |
| `text-sm` (14px) | Body copy in artifacts, table cells, chat bubbles |
| `text-base` (16px) | Primary chat input, short-text answers |
| `text-lg` (18px) | Section headers inside docx/pdf, long-text H2 |
| `text-xl` (20px) | Document titles (docx/pdf H1) |

Line height: `leading-relaxed` (1.625) for prose, `leading-normal` for table/chart labels.

## 3. Spacing

Tailwind default scale, base unit 4px. Two rules to keep consistency:
- Card/artifact padding: always `p-4` (16px)
- Gap between stacked elements inside an artifact: always `gap-2` (8px) or `gap-3` (12px), never mixed within the same component

## 4. Credibility Badge (shared component)

Every artifact type that surfaces sources (table, chart tooltips, docx, pdf) uses the
same three-state badge — same labels, same color mapping, same order of information:

```
[● High]   score >= 0.75   → var(--cred-high),   label "High"
[● Medium] 0.5 <= score < 0.75 → var(--cred-medium), label "Medium"
[● Low]    score < 0.5     → var(--cred-low),    label "Low"
```

Never show the raw float (`0.812`) to the end user in the primary view — the tier badge
is the interface. Raw score can appear in a tooltip/title attribute on hover only.

## 5. Which skill file to read

| `output_type` | Skill file |
|---|---|
| `text` (short, ≤ ~3 sentences) | `skills/text-short.md` |
| `text` (long, multi-paragraph) | `skills/text-long.md` |
| `chart` | `skills/chart.md` |
| `table` | `skills/table.md` |
| `docx` | `skills/docx.md` |
| `pdf` | `skills/pdf.md` |

The output router (`backend/nodes/output_router.py`) decides the type. The builder
(`_build_artifact` / `generate_docx` / `generate_pdf` / frontend artifact components)
is what actually needs to follow the matching skill file — that's the separation this
doc formalizes: routing decides *what*, skills decide *how it looks*.

# Skill: Long-Text Output

Inherits tokens from `../DESIGN.md`. Read that first.

## When this is used

`output_type: "text"` where the synthesized answer is exploratory/analytical and
genuinely multi-paragraph — explanatory content, "how does X work," "what's the history
of Y," where the value is in the reasoning/narrative, not a chart-able number or a
table-able comparison. This is the shape most likely to be under-served if the router
defaults everything non-triggering to the same flat "text" treatment as short-text —
worth explicitly branching on length in the frontend renderer.

## Structure rules

- **Headings allowed** (`##`/`###` via markdown) if the answer naturally has 2+ sections — don't force headings onto content that's really one continuous argument.
- **Paragraphs, not bullets, for reasoning.** Bullets are for enumerable facts (use table if there are 3+ comparable items); prose is for explanation and causality. Don't bullet-point an explanation just because it's long — that fragments reasoning that should read as connected.
- **Key Findings, if present, as a distinct closing block** — not interleaved mid-paragraph. A short bulleted "Key takeaways" section at the end is fine; scattering bullets throughout prose is not.
- **Source attribution:** end-of-paragraph inline citations, same convention as short-text, not footnote numbers (no footnote rendering exists in the chat UI yet).

## Style rules

- Rendered as its own block, not squeezed into a standard chat-bubble shape — `var(--app-bg)` background (not `--app-panel`), `var(--app-border)` for a subtle card outline, generous padding (`p-6`, more than the `p-4` default other artifacts use — long text needs breathing room).
- Body: `text-sm` or `text-base`, `leading-relaxed`, max-width capped (`max-w-2xl` equivalent) — don't let paragraphs stretch full chat-window width, long lines hurt readability.
- Headings inside: `text-lg` for H2 (matches DESIGN.md scale), `var(--app-accent)` color, same as docx/pdf H2 treatment — keeps in-chat long text visually related to the exported document formats.

## Do / Don't

✅ A 3-paragraph explanation of how transformer attention works, with an optional 3-bullet "Key takeaways" block at the end, capped line width, comfortable padding.
❌ The same content chopped into a bulleted list because it's long.
❌ Rendered identically to a short-text chat bubble (cramped, full-width, no breathing room).

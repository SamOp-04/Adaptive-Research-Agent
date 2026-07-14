# Skill: Short-Text Output

Inherits tokens from `../DESIGN.md`. Read that first.

## When this is used

Default fallback (`output_type: "text"`) when the query is a direct factual question
and the synthesized answer is naturally brief — 1-3 sentences, no internal structure.
This is distinct from `text-long.md`: same `output_type` value on the backend, but the
frontend/synthesis prompt should treat them differently based on length.

**Boundary rule:** if `synthesized_answer` exceeds ~500 characters or contains more than
one clear sub-topic, it's long-text, not short-text — see `text-long.md`.

## Structure rules

- **No heading.** A short answer doesn't need a title repeating the question back.
- **Single paragraph**, no bullet points — bullets imply enumerable structure a 2-sentence answer doesn't have.
- **Markdown allowed inline** (bold for the key fact, e.g. the actual number/date/name being asked for) but sparingly — one or two bolded terms max, not every noun.
- **Source attribution:** inline, not a separate section — e.g. "...founded in 1999 (per Reuters)." A short answer citing sources in a bulleted list below it undermines the "short" framing.

## Style rules

- Rendered in the chat bubble: `var(--app-panel)` background, `var(--app-text-primary)`, `text-base`, `leading-relaxed`.
- No card border, no padding beyond the standard chat bubble — this should feel like a chat message, not an artifact. If it starts looking like a bordered card, it's drifted toward long-text treatment.

## Do / Don't

✅ "The Eiffel Tower was completed in **1889**, built for that year's World's Fair (per Britannica)."
❌ A heading + bullet list for a one-fact answer.
❌ A full "Sources" section under a two-sentence answer.

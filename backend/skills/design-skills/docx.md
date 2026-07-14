# Skill: DOCX Output

Inherits tokens from `../DESIGN.md`. Read that first — translate hex colors to Word's
RGB color model in `python-docx`, same values, same meaning.

## When this is used

Router picks `docx` only on **explicit user request** ("write me a doc," "docx," "word
document") — this format is never auto-inferred from findings shape alone, per your
current `output_router.py` design (the late refinement check explicitly excludes
docx/pdf: *"Do not choose docx or pdf unless the user explicitly requested a document
format"*). This is the one skill file the router never reaches for on its own.

## Structure rules

Built in `backend/files/docx_generator.py` via `python-docx`. Fixed section order,
every document, no exceptions:

1. **Title** — `doc.add_heading(query, level=1)`. Font: Inter if embedded, else Calibri (Word default) — do not use Times New Roman, this is a generated research artifact, not a formal print document.
2. **Summary** — one heading ("Summary", level 2) + the synthesized answer as plain paragraphs. No bullet points here — that's what Key Findings is for.
3. **Key Findings** — heading, level 2, then a bulleted list (`style="List Bullet"`). Each bullet is one finding, plain sentence, no sub-bullets.
4. **Sources** — heading, level 2, then a bulleted list. Each entry: title + domain on one line (bold title, `Pt(10)` domain, per current implementation), full URL italicized on the line below. **Add here (currently missing): the credibility tier badge as bracketed text before the title** — e.g. `[High] Article Title — example.com` — so credibility survives into the exported document, not just the in-chat table.

## Style rules

- **Margins:** Word defaults (1 inch) — don't override, these get printed/shared externally and unusual margins look like a mistake.
- **Heading color:** level-1 heading uses `--app-accent` (teal-700) as the font color; level-2 headings use `--app-text-primary` (near-black) with the accent only as a thin bottom border rule, not colored text — one accent color per document is enough, don't tint every heading.
- **Body text:** 11pt, `--app-text-primary` equivalent (near-black, not pure `#000000`).
- **No cover page, no table of contents** — this is a working document, not a formal report deliverable. If a user wants that level of formatting they'll ask for something closer to `skills/pdf.md`'s report treatment, or this skill should gain a "formal" variant later.

## Do / Don't

✅ Title → Summary (prose) → Key Findings (bullets) → Sources (bullets with credibility tags), teal H1, black body text, Word default margins.
❌ A cover page or table of contents for a routine research query.
❌ Sources listed without any credibility indicator.
❌ Mixed fonts (e.g. Calibri body with a Times New Roman title).

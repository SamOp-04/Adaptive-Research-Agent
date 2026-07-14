from __future__ import annotations

from pathlib import Path

from backend.graph.state import SourceFinding


def write_docx(
    content: str,
    path: str | Path,
    *,
    title: str = "Adaptive Research Report",
    key_findings: list[str] | None = None,
    sources: list[SourceFinding] | None = None,
) -> Path:
    from docx import Document
    from docx.shared import Pt, RGBColor

    destination = Path(path)
    document = Document()
    document.styles["Normal"].font.size = Pt(11)
    document.styles["Normal"].font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)

    title_heading = document.add_heading(title, level=1)
    for run in title_heading.runs:
        run.font.color.rgb = RGBColor(0x0F, 0x76, 0x6E)

    document.add_heading("Summary", level=2)
    for paragraph in content.split("\n\n"):
        document.add_paragraph(paragraph)

    document.add_heading("Key Findings", level=2)
    if key_findings:
        for finding in key_findings:
            document.add_paragraph(finding, style="List Bullet")
    else:
        document.add_paragraph("None", style="List Bullet")

    document.add_heading("Sources", level=2)
    if sources:
        for source in sources[:12]:
            _add_source_paragraph(document, source)
    else:
        document.add_paragraph("None", style="List Bullet")

    document.save(destination)
    return destination


def _credibility_tier(source: SourceFinding) -> str:
    score = float(source.get("credibility", {}).get("score", 0) or 0)
    if score >= 0.75:
        return "High"
    if score >= 0.5:
        return "Medium"
    return "Low"


def _add_source_paragraph(document: object, source: SourceFinding) -> None:
    from docx.shared import Pt

    domain = source.get("credibility", {}).get("domain") or source.get("url", "")
    tier = _credibility_tier(source)
    paragraph = document.add_paragraph(style="List Bullet")
    tag_run = paragraph.add_run(f"[{tier}] ")
    tag_run.font.size = Pt(10)
    title_run = paragraph.add_run(source.get("title", "Untitled source"))
    title_run.bold = True
    title_run.font.size = Pt(10)
    domain_run = paragraph.add_run(f" - {domain}")
    domain_run.font.size = Pt(10)
    url_run = paragraph.add_run(f"\n{source.get('url', '')}")
    url_run.italic = True
    url_run.font.size = Pt(10)

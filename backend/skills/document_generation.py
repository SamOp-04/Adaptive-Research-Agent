from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.files.docx_generator import write_docx
from backend.files.pdf_generator import write_pdf
from backend.graph.state import OutputType, SourceFinding


GENERATED_FILES_DIR = Path(__file__).resolve().parents[1] / "generated_files"


def generate_document(
    content: str,
    *,
    output_type: OutputType,
    title: str = "Adaptive Research Report",
    key_findings: list[str] | None = None,
    sources: list[SourceFinding] | None = None,
    output_dir: str | Path = GENERATED_FILES_DIR,
) -> Path:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    stem = f"research-{uuid4().hex[:10]}"
    if output_type == "docx":
        path = destination / f"{stem}.docx"
        write_docx(content, path, title=title, key_findings=key_findings, sources=sources)
        return path
    if output_type == "pdf":
        path = destination / f"{stem}.pdf"
        write_pdf(content, path, title=title, key_findings=key_findings, sources=sources)
        return path

    raise ValueError(f"Unsupported document output type: {output_type}")

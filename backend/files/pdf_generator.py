from __future__ import annotations

from html import escape
import os
from pathlib import Path
import sys

from backend.graph.state import SourceFinding


_DLL_DIRECTORY_HANDLES: list[object] = []


def write_pdf(
    content: str,
    path: str | Path,
    *,
    title: str = "Adaptive Research Report",
    key_findings: list[str] | None = None,
    sources: list[SourceFinding] | None = None,
) -> Path:
    _configure_weasyprint_dlls()

    from weasyprint import HTML

    destination = Path(path)
    body = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in content.split("\n\n") if paragraph.strip())
    findings_html = "".join(f"<li>{escape(finding)}</li>" for finding in key_findings or [])
    sources_html = "".join(
        "<li>"
        f"<span class=\"cred-badge {_credibility_class(source)}\">[{_credibility_tier(source)}]</span>"
        f"{escape(source.get('title', 'Untitled source'))}"
        f" - {escape(source.get('credibility', {}).get('domain', ''))}"
        f"<br><span class=\"source\"><a href=\"{escape(source.get('url', ''), quote=True)}\">"
        f"{escape(source.get('url', ''))}</a></span>"
        "</li>"
        for source in (sources or [])[:12]
    )
    html = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          body {{ font-family: 'Inter', 'Helvetica', sans-serif; margin: 40px; color: #1a1a1a; }}
          h1 {{ font-size: 22px; color: #0f766e; border-bottom: 2px solid #0f766e; padding-bottom: 8px; }}
          h2 {{ font-size: 16px; margin-top: 24px; color: #1a1a1a; border-bottom: 1px solid #e5e5e3; padding-bottom: 4px; }}
          li {{ margin-bottom: 6px; font-size: 13px; }}
          .source {{ font-size: 11px; color: #6b6b68; }}
          .cred-badge {{ font-size: 10px; font-weight: 600; margin-right: 6px; }}
          .cred-high {{ color: #0f766e; }}
          .cred-medium {{ color: #b45309; }}
          .cred-low {{ color: #9ca3af; }}
        </style>
      </head>
      <body>
        <h1>{escape(title)}</h1>
        <h2>Summary</h2>
        {body or "<p>No content generated.</p>"}
        <h2>Key Findings</h2>
        <ul>{findings_html or "<li>None</li>"}</ul>
        <h2>Sources</h2>
        <ul>{sources_html or "<li>None</li>"}</ul>
      </body>
    </html>
    """
    HTML(string=html).write_pdf(destination)
    return destination


def _credibility_tier(source: SourceFinding) -> str:
    score = float(source.get("credibility", {}).get("score", 0) or 0)
    if score >= 0.75:
        return "High"
    if score >= 0.5:
        return "Medium"
    return "Low"


def _credibility_class(source: SourceFinding) -> str:
    return f"cred-{_credibility_tier(source).lower()}"


def _configure_weasyprint_dlls() -> None:
    if sys.platform != "win32":
        return

    candidates = [
        Path(r"C:\msys64\mingw64\bin"),
        Path(r"C:\msys64\ucrt64\bin"),
        Path(r"C:\Program Files\GTK3-Runtime Win64\bin"),
    ]
    dll_dirs = [path for path in candidates if (path / "libgobject-2.0-0.dll").exists()]
    if not dll_dirs:
        return

    current_dll_dirs = [
        item
        for item in os.environ.get("WEASYPRINT_DLL_DIRECTORIES", "").split(";")
        if item
    ]
    for dll_dir in dll_dirs:
        dll_dir_text = str(dll_dir)
        if dll_dir_text not in current_dll_dirs:
            current_dll_dirs.insert(0, dll_dir_text)
        path_entries = os.environ.get("PATH", "").split(os.pathsep)
        if dll_dir_text not in path_entries:
            os.environ["PATH"] = dll_dir_text + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            handle = os.add_dll_directory(dll_dir_text)
            _DLL_DIRECTORY_HANDLES.append(handle)

    os.environ["WEASYPRINT_DLL_DIRECTORIES"] = ";".join(current_dll_dirs)

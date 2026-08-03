from __future__ import annotations

from dataclasses import dataclass
from html import escape
import re
from typing import Literal


BlockType = Literal["heading", "paragraph", "bullet_list", "ordered_list", "table", "rule", "code"]


@dataclass(slots=True)
class InlineSegment:
    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False
    url: str | None = None


@dataclass(slots=True)
class MarkdownBlock:
    type: BlockType
    text: str = ""
    level: int = 0
    items: list[str] | None = None
    headers: list[str] | None = None
    rows: list[list[str]] | None = None


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
RULE_RE = re.compile(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$")
BULLET_RE = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
ORDERED_RE = re.compile(r"^\s*\d+[.)]\s+(.+?)\s*$")
TABLE_SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
INLINE_TOKEN_RE = re.compile(
    r"(`[^`]+`|!\[[^\]]*\]\([^)]+\)|\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|__[^_]+__|\*[^*\s][^*]*\*|_[^_\s][^_]*_)",
    flags=re.DOTALL,
)
LINK_RE = re.compile(r"!?\[([^\]]*)\]\(([^)]+)\)")


def parse_markdown_blocks(content: str) -> list[MarkdownBlock]:
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[MarkdownBlock] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        if line.strip().startswith("```"):
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            blocks.append(MarkdownBlock(type="code", text="\n".join(code_lines)))
            continue

        heading = HEADING_RE.match(line)
        if heading:
            blocks.append(
                MarkdownBlock(
                    type="heading",
                    level=len(heading.group(1)),
                    text=heading.group(2).strip(),
                )
            )
            index += 1
            continue

        if RULE_RE.match(line):
            blocks.append(MarkdownBlock(type="rule"))
            index += 1
            continue

        if _is_table_start(lines, index):
            headers = _split_table_row(lines[index])
            rows: list[list[str]] = []
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                if not _is_table_separator(lines[index]):
                    rows.append(_normalize_table_row(_split_table_row(lines[index]), len(headers)))
                index += 1
            blocks.append(MarkdownBlock(type="table", headers=headers, rows=rows))
            continue

        bullet = BULLET_RE.match(line)
        if bullet:
            items: list[str] = []
            while index < len(lines):
                match = BULLET_RE.match(lines[index])
                if not match:
                    break
                items.append(match.group(1).strip())
                index += 1
            blocks.append(MarkdownBlock(type="bullet_list", items=items))
            continue

        ordered = ORDERED_RE.match(line)
        if ordered:
            items = []
            while index < len(lines):
                match = ORDERED_RE.match(lines[index])
                if not match:
                    break
                items.append(match.group(1).strip())
                index += 1
            blocks.append(MarkdownBlock(type="ordered_list", items=items))
            continue

        paragraph_lines = [line.strip()]
        index += 1
        while index < len(lines) and lines[index].strip() and not _is_block_start(lines, index):
            paragraph_lines.append(lines[index].strip())
            index += 1
        blocks.append(MarkdownBlock(type="paragraph", text=" ".join(paragraph_lines)))

    return blocks


def markdown_to_html(content: str) -> str:
    return "".join(_block_to_html(block) for block in parse_markdown_blocks(content))


def inline_markdown_to_html(text: str) -> str:
    return "".join(_segment_to_html(segment) for segment in iter_inline_segments(text))


def plain_text_from_markdown(text: str) -> str:
    chunks: list[str] = []
    for segment in iter_inline_segments(text):
        chunks.append(segment.text)
        if segment.url:
            chunks.append(f" ({segment.url})")
    return "".join(chunks)


def iter_inline_segments(text: str) -> list[InlineSegment]:
    segments: list[InlineSegment] = []
    position = 0
    for match in INLINE_TOKEN_RE.finditer(text):
        if match.start() > position:
            segments.append(InlineSegment(text=text[position : match.start()]))

        token = match.group(0)
        segments.append(_segment_from_token(token))
        position = match.end()

    if position < len(text):
        segments.append(InlineSegment(text=text[position:]))
    return [segment for segment in segments if segment.text]


def _block_to_html(block: MarkdownBlock) -> str:
    if block.type == "heading":
        level = min(max(block.level, 2), 4)
        return f"<h{level}>{inline_markdown_to_html(block.text)}</h{level}>"
    if block.type == "paragraph":
        return f"<p>{inline_markdown_to_html(block.text)}</p>"
    if block.type == "bullet_list":
        items = "".join(f"<li>{inline_markdown_to_html(item)}</li>" for item in block.items or [])
        return f"<ul>{items}</ul>"
    if block.type == "ordered_list":
        items = "".join(f"<li>{inline_markdown_to_html(item)}</li>" for item in block.items or [])
        return f"<ol>{items}</ol>"
    if block.type == "table":
        headers = block.headers or []
        rows = block.rows or []
        header_html = "".join(f"<th>{inline_markdown_to_html(header)}</th>" for header in headers)
        row_html = "".join(
            "<tr>" + "".join(f"<td>{inline_markdown_to_html(cell)}</td>" for cell in row) + "</tr>"
            for row in rows
        )
        return f"<table><thead><tr>{header_html}</tr></thead><tbody>{row_html}</tbody></table>"
    if block.type == "rule":
        return "<hr>"
    if block.type == "code":
        return f"<pre><code>{escape(block.text)}</code></pre>"
    return ""


def _segment_to_html(segment: InlineSegment) -> str:
    text = escape(segment.text)
    if segment.code:
        text = f"<code>{text}</code>"
    if segment.bold:
        text = f"<strong>{text}</strong>"
    if segment.italic:
        text = f"<em>{text}</em>"
    if segment.url:
        href = escape(segment.url, quote=True)
        text = f"<a href=\"{href}\">{text}</a>"
    return text


def _segment_from_token(token: str) -> InlineSegment:
    if token.startswith("`") and token.endswith("`"):
        return InlineSegment(text=token[1:-1], code=True)

    link = LINK_RE.fullmatch(token)
    if link:
        label, url = link.groups()
        return InlineSegment(text=label, url=url.strip())

    if token.startswith(("**", "__")) and token.endswith(("**", "__")):
        return InlineSegment(text=token[2:-2], bold=True)

    if token.startswith(("*", "_")) and token.endswith(("*", "_")):
        return InlineSegment(text=token[1:-1], italic=True)

    return InlineSegment(text=token)


def _is_block_start(lines: list[str], index: int) -> bool:
    line = lines[index]
    return bool(
        HEADING_RE.match(line)
        or RULE_RE.match(line)
        or BULLET_RE.match(line)
        or ORDERED_RE.match(line)
        or line.strip().startswith("```")
        or _is_table_start(lines, index)
    )


def _is_table_start(lines: list[str], index: int) -> bool:
    return (
        index + 1 < len(lines)
        and "|" in lines[index]
        and _is_table_separator(lines[index + 1])
        and len(_split_table_row(lines[index])) >= 2
    )


def _is_table_separator(line: str) -> bool:
    cells = _split_table_row(line)
    return len(cells) >= 2 and all(TABLE_SEPARATOR_CELL_RE.fullmatch(cell.strip()) for cell in cells)


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _normalize_table_row(cells: list[str], width: int) -> list[str]:
    if len(cells) < width:
        return cells + [""] * (width - len(cells))
    return cells[:width]

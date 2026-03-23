"""
document_chunker.py — Text chunking utilities for the indexing pipeline.

Provides two public APIs:
  - chunk_text(text, use_code_chunker): Original flat chunking (kept for
    backward compatibility with connectors that bypass the section layer).
  - parse_markdown_into_sections(markdown): Parses a Markdown string into a
    flat, ordered list of ParsedSection objects.  Each ParsedSection carries
    its child ParsedChunk list.  Parent-child relationships are expressed via
    ``parent_temp_id`` using a stack-based algorithm that mirrors heading depth.
"""

import hashlib
import re
from uuid import UUID, uuid4

from app.config import config
from app.schemas.document_sections import ParsedChunk, ParsedSection


# ---------------------------------------------------------------------------
# Original flat chunker — unchanged, kept for backward compatibility
# ---------------------------------------------------------------------------

def chunk_text(text: str, use_code_chunker: bool = False) -> list[str]:
    """Chunk a text string using the configured chunker and return the chunk texts."""
    chunker = (
        config.code_chunker_instance if use_code_chunker else config.chunker_instance
    )
    return [c.text for c in chunker.chunk(text)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+)?\s*$", re.MULTILINE)


def _strip_markdown(text: str) -> str:
    """Very lightweight markdown-to-plaintext (heading markup, bold, italic, code)."""
    text = re.sub(r"#{1,6}\s+", "", text)       # headings
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)  # bold/italic
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)        # inline code / fenced
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links/images
    return text.strip()


def _infer_section_type(level: int, title: str) -> str:
    """Heuristic classification of a section based on heading level and title."""
    t = title.lower()
    if level == 1:
        return "title"
    if level == 2:
        return "chapter"
    if any(k in t for k in ("introduction", "overview", "background")):
        return "introduction"
    if any(k in t for k in ("conclusion", "summary", "abstract")):
        return "conclusion"
    if any(k in t for k in ("reference", "bibliography", "appendix")):
        return "reference"
    return "section"


def _make_parsed_chunks(body_markdown: str) -> list[ParsedChunk]:
    """Chunk the body text of a section and wrap in ParsedChunk DTOs."""
    texts = chunk_text(body_markdown) if body_markdown.strip() else []
    return [
        ParsedChunk(
            content=text,
            chunk_order_in_section=idx,
            chunk_type="text",
            content_hash=hashlib.sha256(text.encode()).hexdigest()[:16],
        )
        for idx, text in enumerate(texts)
    ]


def _make_default_section(markdown: str) -> ParsedSection:
    """Wrap an entire document (no headings) into a single root section."""
    sec = ParsedSection(
        heading_text="(Document Body)",
        heading_level=1,
        raw_markdown=markdown,
        plain_text=_strip_markdown(markdown),
        section_order=0,
        section_type="body",
        chunks=_make_parsed_chunks(markdown),
    )
    return sec


# ---------------------------------------------------------------------------
# Public API — Section-aware parser
# ---------------------------------------------------------------------------

def parse_markdown_into_sections(markdown: str) -> list[ParsedSection]:
    """
    Parse a Markdown string into an ordered, flat list of ParsedSection objects.

    Algorithm (stack-based):
      1. Find all ATX headings (``# … ######``) via regex.
      2. For each heading, maintain a *stack* of (level, temp_uuid) pairs
         representing the current ancestor chain.
      3. Pop the stack until the top entry has a *lower* level than the
         current heading → that top entry becomes the parent.
      4. The body of each section is the text between the current heading and
         the next heading (or end-of-document).
      5. Each section's chunks are produced by ``chunk_text(body)``.

    Parent-child linkage uses ``_temp_id`` / ``parent_temp_id`` UUIDs.  The
    persistence layer (``attach_sections_and_chunks``) resolves these into
    actual DB UUIDs after the first flush.

    Args:
        markdown: Full Markdown source of a document.

    Returns:
        Ordered list of ParsedSection (flat, depth-first order).
    """
    matches = list(_HEADING_RE.finditer(markdown))

    if not matches:
        return [_make_default_section(markdown)]

    sections: list[ParsedSection] = []
    # Stack items: (heading_level: int, temp_id: UUID)
    stack: list[tuple[int, UUID]] = []

    for i, match in enumerate(matches):
        level = len(match.group(1))       # number of '#' chars
        title = match.group(2).strip()

        # Body = text from end of this heading line to start of next heading
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body_markdown = markdown[body_start:body_end].strip()
        full_raw = match.group(0) + ("\n" + body_markdown if body_markdown else "")

        # --- Stack-based parent resolution ---
        # Pop until we find an ancestor with a strictly lower level
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent_temp_id: UUID | None = stack[-1][1] if stack else None

        # Create a fresh temp UUID for this section
        temp_id = uuid4()
        stack.append((level, temp_id))

        sec = ParsedSection(
            heading_text=title,
            heading_level=level,
            raw_markdown=full_raw,
            plain_text=_strip_markdown(body_markdown),
            section_order=len(sections),
            parent_temp_id=parent_temp_id,
            section_type=_infer_section_type(level, title),
            chunks=_make_parsed_chunks(body_markdown),
            temp_id=temp_id,
        )
        sections.append(sec)

    return sections

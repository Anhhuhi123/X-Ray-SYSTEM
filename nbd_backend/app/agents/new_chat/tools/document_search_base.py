"""Shared utilities for knowledge base and NFD docs search.

This module provides reusable components for document search across different
data sources (user knowledge base, NFD system documentation, etc.):
- Query validation (degenerate query detection)
- Context budget management based on model context windows
- Document formatting for LLM context
"""

import json
import os
import re
from typing import Any

# Patterns that indicate the query has no meaningful search signal.
# plainto_tsquery('english', '*') produces an empty tsquery and an embedding
# of '*' is random noise, so both keyword and semantic search degrade to
# arbitrary ordering — large documents (many chunks) dominate by chance.
_DEGENERATE_QUERY_RE = re.compile(
    r"^[\s*?_.#@!\-/\\]+$"  # only wildcards, punctuation, whitespace
)

# Max chunks per document when doing a recency-based browse instead of
# a real search.  We want breadth (many docs) over depth (many chunks).
_BROWSE_MAX_CHUNKS_PER_DOC = 5

# Live search connectors whose results should be cited by URL rather than
# a numeric chunk_id (the numeric IDs are meaningless auto-incremented counters).
# NOTE: All live search connectors have been decommissioned from the database.
# This set is now empty; local connectors fall back to recency-based browse.
_LIVE_SEARCH_CONNECTORS: set[str] = set()


def _is_degenerate_query(query: str) -> bool:
    """Return True when the query carries no meaningful search signal.

    Catches wildcard patterns (``*``, ``**``), empty / whitespace-only
    strings, and single-character non-word tokens.  These queries cause
    both keyword search (empty tsquery) and semantic search (meaningless
    embedding) to return effectively random results.
    """
    stripped = query.strip()
    if not stripped:
        return True
    return bool(_DEGENERATE_QUERY_RE.match(stripped))


# =============================================================================
# Document Formatting Constants
# =============================================================================

# Fraction of the model's context window (in characters) that a single tool
# result is allowed to occupy.  The remainder is reserved for system prompt,
# conversation history, and model output.  With ~4 chars/token this gives a
# tool result ≈ 25 % of the context budget in tokens.
_TOOL_OUTPUT_CONTEXT_FRACTION = float(os.getenv("SURFSENSE_TOOL_OUTPUT_CONTEXT_FRACTION", "0.25"))
_CHARS_PER_TOKEN = int(os.getenv("SURFSENSE_CHARS_PER_TOKEN", "4"))

# Hard-floor / ceiling so the budget is always sensible regardless of what
# the model reports. These may be overridden in runtime via environment
# variables to allow deploying with a larger/smaller output budget without
# changing source code or tests.
_MIN_TOOL_OUTPUT_CHARS = int(os.getenv("SURFSENSE_MIN_TOOL_OUTPUT_CHARS", "20000"))
_MAX_TOOL_OUTPUT_CHARS = int(os.getenv("SURFSENSE_MAX_TOOL_OUTPUT_CHARS", "200000"))
_MAX_CHUNK_CHARS = int(os.getenv("SURFSENSE_MAX_CHUNK_CHARS", "8000"))

# Rank-adaptive per-document budget allocation.
# Top-ranked (most relevant) documents get a larger share of the budget so
# we pack as much high-quality context as possible.
#
#   fraction(rank) = _TOP_DOC_BUDGET_FRACTION / (1 + rank * _RANK_DECAY)
#
# Examples (128K budget, 8K chunk cap):
#   rank 0 → 40% → 6 chunks   |  rank 3 → 19% → 3 chunks
#   rank 1 → 30% → 4 chunks   |  rank 10 → 10% → 3 chunks (floor)
#   rank 2 → 24% → 3 chunks   |
_TOP_DOC_BUDGET_FRACTION = 0.40
_RANK_DECAY = 0.35
_MIN_CHUNKS_PER_DOC = 3


def _compute_tool_output_budget(max_input_tokens: int | None) -> int:
    """Derive a character budget from the model's context window.

    Uses ``litellm.get_model_info`` via the value already resolved by
    ``ChatLiteLLMRouter`` / ``ChatLiteLLM`` and passed through the dependency
    chain as ``max_input_tokens``.  Falls back to a conservative default when
    the value is unavailable.
    """
    if max_input_tokens is None or max_input_tokens <= 0:
        return _MIN_TOOL_OUTPUT_CHARS  # conservative fallback

    budget = int(max_input_tokens * _CHARS_PER_TOKEN * _TOOL_OUTPUT_CONTEXT_FRACTION)
    return max(_MIN_TOOL_OUTPUT_CHARS, min(budget, _MAX_TOOL_OUTPUT_CHARS))


def format_documents_for_context(
    documents: list[dict[str, Any]],
    *,
    max_chars: int = _MAX_TOOL_OUTPUT_CHARS,
    max_chunk_chars: int = _MAX_CHUNK_CHARS,
    max_chunks_per_doc: int = 0,
) -> str:
    """
    Format retrieved documents into a readable context string for the LLM.

    Documents are added in order (highest relevance first) until the character
    budget is reached.  Individual chunks are capped at ``max_chunk_chars`` and
    each document is limited to a dynamically computed chunk cap so a single
    large document cannot monopolize the output while still maximising the use
    of available context space.

    Args:
        documents: List of document dictionaries from connector search
        max_chars: Approximate character budget for the entire output.
        max_chunk_chars: Per-chunk character cap (content is tail-truncated).
        max_chunks_per_doc: Maximum chunks per document.  ``0`` (default) means
            auto-compute per document using a rank-adaptive formula so
            higher-ranked documents receive more chunks.

    Returns:
        Formatted string with document contents and metadata
    """
    if not documents:
        return ""

    # Group chunks by document id (preferred) to produce the XML structure.
    #
    # IMPORTANT: Results are expected in this document-grouped form:
    #   {
    #     "document": {...},
    #     "chunks": [{"chunk_id": 123, "content": "..."}, ...],
    #     "source": "FILE" | "NOTE" | ...
    #   }
    #
    # We must preserve chunk_id so citations like [citation:123] are possible.
    grouped: dict[str, dict[str, Any]] = {}

    for doc in documents:
        document_info = (doc.get("document") or {}) if isinstance(doc, dict) else {}
        metadata = (
            (document_info.get("metadata") or {})
            if isinstance(document_info, dict)
            else {}
        )
        if not metadata and isinstance(doc, dict):
            # Some result shapes may place metadata at the top level.
            metadata = doc.get("metadata") or {}

        source = (
            (doc.get("source") if isinstance(doc, dict) else None)
            or document_info.get("document_type")
            or metadata.get("document_type")
            or "UNKNOWN"
        )

        # Document identity (prefer document_id; otherwise fall back to type+title+url)
        document_id_val = document_info.get("id")
        title = (
            document_info.get("title") or metadata.get("title") or "Untitled Document"
        )
        url = (
            metadata.get("url")
            or metadata.get("source")
            or metadata.get("page_url")
            or ""
        )

        doc_key = (
            str(document_id_val)
            if document_id_val is not None
            else f"{source}::{title}::{url}"
        )

        if doc_key not in grouped:
            grouped[doc_key] = {
                "document_id": document_id_val
                if document_id_val is not None
                else doc_key,
                "document_type": metadata.get("document_type") or source,
                "title": title,
                "url": url,
                "metadata": metadata,
                "chunks": [],
            }

        # Prefer document-grouped chunks if available
        chunks_list = doc.get("chunks") if isinstance(doc, dict) else None
        if isinstance(chunks_list, list) and chunks_list:
            for ch in chunks_list:
                if not isinstance(ch, dict):
                    continue
                chunk_id = ch.get("chunk_id") or ch.get("id")
                content = (ch.get("content") or "").strip()
                if not content:
                    continue
                grouped[doc_key]["chunks"].append(
                    {"chunk_id": chunk_id, "content": content}
                )
            continue

        # Fallback: treat this as a flat chunk-like object
        if not isinstance(doc, dict):
            continue
        chunk_id = doc.get("chunk_id") or doc.get("id")
        content = (doc.get("content") or "").strip()
        if not content:
            continue
        grouped[doc_key]["chunks"].append({"chunk_id": chunk_id, "content": content})

    # Render XML expected by citation instructions, respecting the char budget.
    parts: list[str] = []
    total_chars = 0
    total_docs = len(grouped)

    for doc_idx, g in enumerate(grouped.values()):
        metadata_json = json.dumps(g["metadata"], ensure_ascii=False)
        is_live_search = g["document_type"] in _LIVE_SEARCH_CONNECTORS

        doc_lines: list[str] = [
            "<document>",
            "<document_metadata>",
            f"  <document_id>{g['document_id']}</document_id>",
            f"  <document_type>{g['document_type']}</document_type>",
            f"  <title><![CDATA[{g['title']}]]></title>",
            f"  <url><![CDATA[{g['url']}]]></url>",
            f"  <metadata_json><![CDATA[{metadata_json}]]></metadata_json>",
            "</document_metadata>",
            "",
            "<document_content>",
        ]

        # Rank-adaptive per-document chunk cap: top results get more chunks.
        if max_chunks_per_doc > 0:
            chunks_allowed = max_chunks_per_doc
        else:
            doc_fraction = _TOP_DOC_BUDGET_FRACTION / (1 + doc_idx * _RANK_DECAY)
            max_doc_chars = int(max_chars * doc_fraction)
            xml_overhead = 500
            chunks_allowed = max(
                (max_doc_chars - xml_overhead) // max(max_chunk_chars, 1),
                _MIN_CHUNKS_PER_DOC,
            )

        chunks = g["chunks"]
        if len(chunks) > chunks_allowed:
            chunks = chunks[:chunks_allowed]

        for ch in chunks:
            ch_content = ch["content"]
            if max_chunk_chars and len(ch_content) > max_chunk_chars:
                ch_content = ch_content[:max_chunk_chars] + "\n...(truncated)"
            ch_id = g["url"] if (is_live_search and g["url"]) else ch["chunk_id"]
            if ch_id is None:
                doc_lines.append(f"  <chunk><![CDATA[{ch_content}]]></chunk>")
            else:
                doc_lines.append(
                    f"  <chunk id='{ch_id}'><![CDATA[{ch_content}]]></chunk>"
                )

        doc_lines.extend(["</document_content>", "</document>", ""])

        doc_xml = "\n".join(doc_lines)
        doc_len = len(doc_xml)

        if total_chars + doc_len > max_chars:
            remaining = total_docs - doc_idx
            if doc_idx == 0:
                parts.append(doc_xml)
                total_chars += doc_len
            parts.append(
                f"<!-- Output truncated: {remaining} more document(s) omitted "
                f"(budget {max_chars} chars). Refine your query or reduce top_k "
                f"to retrieve different results. -->"
            )
            break

        parts.append(doc_xml)
        total_chars += doc_len

    result = "\n".join(parts).strip()

    # Hard safety net: if the result is still over budget (e.g. a single massive
    # first document), forcibly truncate with a closing comment.
    if len(result) > max_chars:
        truncation_msg = "\n<!-- ...output forcibly truncated to fit context window -->"
        result = result[: max_chars - len(truncation_msg)] + truncation_msg

    return result

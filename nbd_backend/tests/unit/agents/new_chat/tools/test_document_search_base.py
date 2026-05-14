import pytest

from app.agents.new_chat.tools.document_search_base import (
    _compute_tool_output_budget,
    _is_degenerate_query,
    format_documents_for_context,
)

pytestmark = pytest.mark.unit


def test_is_degenerate_query_detects_empty_and_wildcards():
    assert _is_degenerate_query("") is True
    assert _is_degenerate_query("   ") is True
    assert _is_degenerate_query("*") is True
    assert _is_degenerate_query("**") is True
    assert _is_degenerate_query("normal search") is False


def test_compute_tool_output_budget_clamps_to_bounds():
    assert _compute_tool_output_budget(None) == 20_000
    assert _compute_tool_output_budget(1) == 20_000
    assert _compute_tool_output_budget(300_000) == 200_000


def test_format_documents_for_context_keeps_document_structure():
    result = format_documents_for_context(
        [
            {
                "document": {
                    "id": 1,
                    "title": "Doc One",
                    "document_type": "NOTE",
                    "metadata": {"source": "source-a"},
                },
                "chunks": [
                    {"chunk_id": "c1", "content": "alpha"},
                    {"chunk_id": "c2", "content": "beta"},
                ],
                "source": "NOTE",
            }
        ],
        max_chars=10_000,
    )

    assert "<document_id>1</document_id>" in result
    assert "<document_type>NOTE</document_type>" in result
    assert "id='c1'" in result
    assert "id='c2'" in result

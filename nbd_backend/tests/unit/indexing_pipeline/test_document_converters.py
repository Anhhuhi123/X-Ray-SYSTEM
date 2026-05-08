import pytest

from app.db import DocumentSection
from app.utils.document_converters import create_document_chunks

pytestmark = pytest.mark.unit


@pytest.mark.usefixtures("patched_embed_texts")
@pytest.mark.asyncio
async def test_create_document_chunks_links_parent_sections():
    content = "# Parent\n\nParent body.\n\n## Child\n\nChild body."

    chunks = await create_document_chunks(content)

    sections = []
    for chunk in chunks:
        assert chunk.section is not None
        if chunk.section not in sections:
            sections.append(chunk.section)

    parent_sections = [section for section in sections if section.parent is None]
    child_sections = [section for section in sections if section.parent is not None]

    assert len(parent_sections) == 1
    assert len(child_sections) == 1
    assert isinstance(parent_sections[0], DocumentSection)
    assert child_sections[0].parent is parent_sections[0]
    assert child_sections[0].parent_section_id == parent_sections[0].id

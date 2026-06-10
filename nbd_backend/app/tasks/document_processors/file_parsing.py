"""Shared file parsing helpers for document ingestion flows."""

from __future__ import annotations

import os
from pathlib import Path

from app.config import config as app_config
from app.services.docling_service import create_docling_service
from app.utils.document_converters import convert_document_to_markdown


async def _parse_with_llamacloud(file_path: str) -> str:
    # Reuse existing retry logic from upload pipeline.
    from app.tasks.document_processors.file_processors import (
        parse_with_llamacloud_retry,
    )

    file_size = os.path.getsize(file_path)
    estimated_pages = max(1, file_size // (80 * 1024))

    result = await parse_with_llamacloud_retry(
        file_path=file_path,
        estimated_pages=estimated_pages,
    )
    markdown_documents = await result.aget_markdown_documents(split_by_page=False)
    if not markdown_documents:
        raise RuntimeError("LlamaCloud parsing returned no documents")
    return "\n\n".join(doc.text for doc in markdown_documents if doc.text).strip()


async def _parse_with_docling(file_path: str) -> str:
    docling_service = create_docling_service()
    result = await docling_service.process_document(file_path, Path(file_path).name)
    content = result.get("content", "")
    if not content:
        raise RuntimeError("Docling parsing returned empty content")
    return content


async def parse_file_to_markdown(file_path: str, filename: str) -> tuple[str, str]:
    """Parse a file to markdown using the configured ETL service.

    Returns:
        Tuple of (markdown_content, parser_name)
    """
    lower_name = filename.lower()

    if lower_name.endswith((".md", ".markdown", ".txt", ".mdx")):
        return Path(file_path).read_text(encoding="utf-8"), "MARKDOWN"

    etl_service = (app_config.ETL_SERVICE or "").upper()
    if etl_service == "UNSTRUCTURED":
        raise RuntimeError("UNSTRUCTURED ETL service is no longer supported. Please use DOCLING or LLAMACLOUD.")

    if etl_service == "LLAMACLOUD":
        return await _parse_with_llamacloud(file_path), "LLAMACLOUD"

    if etl_service == "DOCLING":
        return await _parse_with_docling(file_path), "DOCLING"

    raise RuntimeError(
        "Unsupported or missing ETL_SERVICE. Set ETL_SERVICE to DOCLING or LLAMACLOUD."
    )

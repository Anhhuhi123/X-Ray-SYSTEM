"""
Document processors module for background tasks.

This module provides a collection of document processors for different content types
and sources. Each processor is responsible for handling a specific type of document
processing task in the background.

Available processors:
- Extension processor: Handle documents from browser extension
- Markdown processor: Process markdown files
- File processors: Handle files using different ETL services (Unstructured, LlamaCloud, Docling)
- YouTube processor: Process YouTube videos and extract transcripts
"""

# URL crawler
# Extension processor
from .extension_processor import add_extension_received_document

from .file_processors import (
    add_received_file_document_using_docling,
    add_received_file_document_using_llamacloud,
)

# Markdown processor
from .markdown_processor import add_received_markdown_file_document

__all__ = [
    # Extension processing
    "add_extension_received_document",
    "add_received_file_document_using_docling",
    "add_received_file_document_using_llamacloud",
    # Markdown file processing
    "add_received_markdown_file_document",
]

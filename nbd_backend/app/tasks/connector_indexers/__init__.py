"""
Connector indexers module for background tasks.

This module provides a collection of connector indexers for different platforms
and services. Each indexer is responsible for handling the indexing of content
from a specific connector type.

Available indexers:
- Obsidian: Index notes from Obsidian vaults
- Webcrawler: Index crawled URLs
"""

# Knowledge management
from .obsidian_indexer import index_obsidian_vault
from .webcrawler_indexer import index_crawled_urls

__all__ = [  # noqa: RUF022
    "index_obsidian_vault",
    "index_crawled_urls",
]

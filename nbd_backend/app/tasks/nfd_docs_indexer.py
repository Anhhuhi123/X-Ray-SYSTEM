"""
NFD documentation indexer.
Indexes documentation files at startup.
"""

import hashlib
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import config
from app.db import NFDDocsChunks, NFDDocsDocument, async_session_maker
from app.tasks.document_processors.file_parsing import parse_file_to_markdown
from app.utils.document_converters import embed_text

logger = logging.getLogger(__name__)

# Path to content root relative to project root
CONTENT_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "nbd_web" / "content"
)
LEGACY_DOCS_DIR = CONTENT_DIR / "docs"

SUPPORTED_EXTENSIONS = {".mdx", ".pdf", ".doc", ".docx"}


def parse_mdx_frontmatter(content: str) -> tuple[str, str]:
    """
    Parse MDX file to extract frontmatter title and content.

    Args:
        content: Raw MDX file content

    Returns:
        Tuple of (title, content_without_frontmatter)
    """
    # Match frontmatter between --- markers
    frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if match:
        frontmatter = match.group(1)
        content_without_frontmatter = content[match.end() :]

        # Extract title from frontmatter
        title_match = re.search(r"^title:\s*(.+)$", frontmatter, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else "Untitled"

        # Remove quotes if present
        title = title.strip("\"'")

        return title, content_without_frontmatter.strip()

    return "Untitled", content.strip()


def get_all_indexable_files() -> list[Path]:
    """
    Get all supported documentation files from the content directory.

    Returns:
        List of Path objects for each supported file
    """
    if not CONTENT_DIR.exists():
        logger.warning(f"Content directory not found: {CONTENT_DIR}")
        return []

    files: list[Path] = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(CONTENT_DIR.rglob(f"*{ext}"))

    return sorted(set(files))


def generate_nfd_docs_content_hash(content: bytes) -> str:
    """Generate SHA-256 hash for source file bytes."""
    return hashlib.sha256(content).hexdigest()


def get_title_from_path(file_path: Path) -> str:
    """Generate a readable title from filename for non-MDX files."""
    return file_path.stem.replace("_", " ").strip() or file_path.name


def get_source_key(file_path: Path) -> str:
    """Build a stable source key, preserving legacy docs/* relative paths."""
    if file_path.is_relative_to(LEGACY_DOCS_DIR):
        return str(file_path.relative_to(LEGACY_DOCS_DIR))
    return str(file_path.relative_to(CONTENT_DIR))


def create_nfd_docs_chunks(content: str) -> list[NFDDocsChunks]:
    """
    Create chunks from NFD documentation content.

    Args:
        content: Document content to chunk

    Returns:
        List of NFDDocsChunks objects with embeddings
    """
    return [
        NFDDocsChunks(
            content=chunk.text,
            embedding=embed_text(chunk.text),
        )
        for chunk in config.chunker_instance.chunk(content)
    ]


async def index_nfd_docs(session: AsyncSession) -> tuple[int, int, int, int]:
    """
    Index all NFD documentation files.

    Args:
        session: SQLAlchemy async session

    Returns:
        Tuple of (created, updated, skipped, deleted) counts
    """
    created = 0
    updated = 0
    skipped = 0
    deleted = 0

    # Get all existing docs from database
    existing_docs_result = await session.execute(
        select(NFDDocsDocument).options(selectinload(NFDDocsDocument.chunks))
    )
    existing_docs = {doc.source: doc for doc in existing_docs_result.scalars().all()}

    # Track which sources we've processed
    processed_sources = set()

    # Get all supported docs files
    docs_files = get_all_indexable_files()
    logger.info(f"Found {len(docs_files)} supported docs files to index")

    for docs_file in docs_files:
        try:
            source = get_source_key(docs_file)
            processed_sources.add(source)

            file_bytes = docs_file.read_bytes()
            content_hash = generate_nfd_docs_content_hash(file_bytes)

            if (
                source in existing_docs
                and existing_docs[source].content_hash == content_hash
            ):
                logger.debug(f"Skipping unchanged: {source}")
                skipped += 1
                continue

            if docs_file.suffix.lower() == ".mdx":
                raw_content = docs_file.read_text(encoding="utf-8")
                title, content = parse_mdx_frontmatter(raw_content)
            else:
                title = get_title_from_path(docs_file)
                content, parser_name = await parse_file_to_markdown(
                    str(docs_file),
                    docs_file.name,
                )
                content = content.strip()
                logger.info(
                    "Parsed %s with %s parser for NFD docs startup index",
                    source,
                    parser_name,
                )

            if not content:
                logger.warning(f"Skipping empty parsed content: {source}")
                skipped += 1
                continue

            if source in existing_docs:
                existing_doc = existing_docs[source]

                # Content changed - update document
                logger.info(f"Updating changed document: {source}")

                # Create new chunks
                chunks = create_nfd_docs_chunks(content)

                # Update document fields
                existing_doc.title = title
                existing_doc.content = content
                existing_doc.content_hash = content_hash
                existing_doc.embedding = embed_text(content)
                existing_doc.chunks = chunks
                existing_doc.updated_at = datetime.now(UTC)

                updated += 1
            else:
                # New document - create it
                logger.info(f"Creating new document: {source}")

                chunks = create_nfd_docs_chunks(content)

                document = NFDDocsDocument(
                    source=source,
                    title=title,
                    content=content,
                    content_hash=content_hash,
                    embedding=embed_text(content),
                    chunks=chunks,
                    updated_at=datetime.now(UTC),
                )

                session.add(document)
                created += 1

        except Exception as e:
            logger.error(f"Error processing {docs_file}: {e}", exc_info=True)
            continue

    # Delete documents for removed files
    for source, doc in existing_docs.items():
        if source not in processed_sources:
            logger.info(f"Deleting removed document: {source}")
            await session.delete(doc)
            deleted += 1

    # Commit all changes
    await session.commit()

    logger.info(
        f"Indexing complete: {created} created, {updated} updated, "
        f"{skipped} skipped, {deleted} deleted"
    )

    return created, updated, skipped, deleted


async def seed_nfd_docs() -> tuple[int, int, int, int]:
    """
    Seed NFD documentation into the database.

    This function indexes supported documentation files from nbd_web/content.
    It handles creating, updating, and deleting docs based on content changes.

    Returns:
        Tuple of (created, updated, skipped, deleted) counts
        Returns (0, 0, 0, 0) if an error occurs
    """
    logger.info("Starting NFD docs indexing...")

    try:
        async with async_session_maker() as session:
            created, updated, skipped, deleted = await index_nfd_docs(session)

        logger.info(
            f"NFD docs indexing complete: "
            f"created={created}, updated={updated}, skipped={skipped}, deleted={deleted}"
        )

        return created, updated, skipped, deleted

    except Exception as e:
        logger.error(f"Failed to seed NFD docs: {e}", exc_info=True)
        return 0, 0, 0, 0

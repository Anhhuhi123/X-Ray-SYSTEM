import asyncio
import time
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db import (
    Chunk,
    Document,
    SearchSourceConnector,
    SearchSourceConnectorType,
    async_session_maker,
)
from app.retriever.chunks_hybrid_search import ChucksHybridSearchRetriever
from app.retriever.documents_hybrid_search import DocumentHybridSearchRetriever
from app.utils.decommissioned_connectors import DECOMMISSIONED_CONNECTOR_TYPES
from app.utils.perf import get_perf_logger


class ConnectorService:
    def __init__(self, session: AsyncSession, search_space_id: int | None = None):
        self.session = session
        self.chunk_retriever = ChucksHybridSearchRetriever(session)
        self.document_retriever = DocumentHybridSearchRetriever(session)
        self.search_space_id = search_space_id
        self.source_id_counter = (
            100000  # High starting value to avoid collisions with existing IDs
        )
        self.counter_lock = (
            asyncio.Lock()
        )  # Lock to protect counter in multithreaded environments

    async def initialize_counter(self):
        """
        Initialize the source_id_counter based on the total number of chunks for the search space.
        This ensures unique IDs across different sessions.
        """
        if self.search_space_id:
            try:
                # Count total chunks for documents belonging to this search space

                result = await self.session.execute(
                    select(func.count(Chunk.id))
                    .join(Document)
                    .filter(Document.search_space_id == self.search_space_id)
                )
                chunk_count = result.scalar() or 0
                self.source_id_counter = chunk_count + 1
                print(
                    f"Initialized source_id_counter to {self.source_id_counter} for search space {self.search_space_id}"
                )
            except Exception as e:
                print(f"Error initializing source_id_counter: {e!s}")
                # Fallback to default value
                self.source_id_counter = 1


    async def search_files(
        self,
        user_query: str,
        search_space_id: int,
        top_k: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple:
        """
        Search for files and return both the source information and langchain documents.

        Uses combined chunk-level and document-level hybrid search with RRF fusion.

        Args:
            user_query: The user's query
            search_space_id: The search space ID to search in
            top_k: Maximum number of results to return
            start_date: Optional start date for filtering documents by updated_at
            end_date: Optional end date for filtering documents by updated_at

        Returns:
            tuple: (sources_info, langchain_documents)
        """
        files_docs = await self._combined_rrf_search(
            query_text=user_query,
            search_space_id=search_space_id,
            document_type="FILE",
            top_k=top_k,
            start_date=start_date,
            end_date=end_date,
        )

        # Early return if no results
        if not files_docs:
            return {
                "id": 2,
                "name": "Files",
                "type": "FILE",
                "sources": [],
            }, []

        def _description_fn(
            chunk: dict[str, Any], _doc_info: dict[str, Any], metadata: dict[str, Any]
        ) -> str:
            return (
                metadata.get("og:description")
                or metadata.get("ogDescription")
                or self._chunk_preview(chunk.get("content", ""))
            )

        sources_list = self._build_chunk_sources_from_documents(
            files_docs,
            description_fn=_description_fn,
            url_fn=lambda _doc_info, metadata: metadata.get("url", "") or "",
        )

        # Create result object
        result_object = {
            "id": 2,
            "name": "Files",
            "type": "FILE",
            "sources": sources_list,
        }

        return result_object, files_docs

    async def _combined_rrf_search(
        self,
        query_text: str,
        search_space_id: int,
        document_type: str,
        top_k: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        query_embedding: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform combined search using both chunk-based and document-based hybrid search,
        then merge results using Reciprocal Rank Fusion (RRF) **at the document level**.

        Returned results are **document-grouped** objects that contain a list of chunks
        with real chunk IDs (used for downstream `[citation:<chunk_id>]`).

        This method:
        1. Runs chunk-level hybrid search (vector + keyword on chunks)
        2. Runs document-level hybrid search (vector + keyword on documents, returns chunks)
        3. Combines results using RRF based on their ranks in each result set
        4. Returns top-k deduplicated results

        Args:
            query_text: The search query text
            search_space_id: The search space ID to search within
            document_type: Document type to filter (e.g., "FILE", "CRAWLED_URL")
            top_k: Number of results to return
            start_date: Optional start date for filtering documents by updated_at
            end_date: Optional end date for filtering documents by updated_at

        Returns:
            List of combined and deduplicated document results
        """
        from app.config import config

        perf = get_perf_logger()
        t0 = time.perf_counter()

        # RRF constant
        k = 60

        # Get more results from each retriever for better fusion
        retriever_top_k = top_k * 2

        # Reuse caller-provided embedding or compute once for both retrievers.
        if query_embedding is None:
            t_embed = time.perf_counter()
            query_embedding = await asyncio.to_thread(
                config.embedding_model_instance.embed, query_text
            )
            perf.info(
                "[connector_svc] _combined_rrf embedding in %.3fs type=%s",
                time.perf_counter() - t_embed,
                document_type,
            )

        search_kwargs = {
            "query_text": query_text,
            "top_k": retriever_top_k,
            "search_space_id": search_space_id,
            "document_type": document_type,
            "start_date": start_date,
            "end_date": end_date,
            "query_embedding": query_embedding,
        }

        # Run chunk and document retrievers in parallel using separate DB sessions
        # so they don't contend on a shared AsyncSession connection.
        async def _run_chunk_search() -> list[dict[str, Any]]:
            async with async_session_maker() as session:
                retriever = ChucksHybridSearchRetriever(session)
                return await retriever.hybrid_search(**search_kwargs)

        async def _run_doc_search() -> list[dict[str, Any]]:
            async with async_session_maker() as session:
                retriever = DocumentHybridSearchRetriever(session)
                return await retriever.hybrid_search(**search_kwargs)

        t_parallel = time.perf_counter()
        chunk_results, doc_results = await asyncio.gather(
            _run_chunk_search(), _run_doc_search()
        )
        perf.info(
            "[connector_svc] _combined_rrf parallel retrievers in %.3fs "
            "chunk_results=%d doc_results=%d type=%s",
            time.perf_counter() - t_parallel,
            len(chunk_results),
            len(doc_results),
            document_type,
        )

        if not chunk_results and not doc_results:
            return []

        # Helper to extract document_id from our doc-grouped result
        def _doc_id(item: dict[str, Any]) -> int | None:
            doc = item.get("document", {})
            did = doc.get("id")
            return int(did) if did is not None else None

        # Build rank maps for RRF calculation (document-level)
        chunk_ranks: dict[int, int] = {}
        for rank, result in enumerate(chunk_results, start=1):
            did = _doc_id(result)
            if did is not None and did not in chunk_ranks:
                chunk_ranks[did] = rank

        doc_ranks: dict[int, int] = {}
        for rank, result in enumerate(doc_results, start=1):
            did = _doc_id(result)
            if did is not None and did not in doc_ranks:
                doc_ranks[did] = rank

        all_doc_ids = set(chunk_ranks.keys()) | set(doc_ranks.keys())

        # Calculate RRF scores for each document
        rrf_scores: dict[int, float] = {}
        for did in all_doc_ids:
            chunk_rank = chunk_ranks.get(did)
            doc_rank = doc_ranks.get(did)
            score = 0.0
            if chunk_rank is not None:
                score += 1.0 / (k + chunk_rank)
            if doc_rank is not None:
                score += 1.0 / (k + doc_rank)
            rrf_scores[did] = score

        # Prefer chunk_results data, fallback to doc_results data
        doc_data: dict[int, dict[str, Any]] = {}
        for result in chunk_results:
            did = _doc_id(result)
            if did is not None and did not in doc_data:
                doc_data[did] = result
        for result in doc_results:
            did = _doc_id(result)
            if did is not None and did not in doc_data:
                doc_data[did] = result

        sorted_doc_ids = sorted(
            all_doc_ids, key=lambda did: rrf_scores[did], reverse=True
        )[:top_k]

        combined_results: list[dict[str, Any]] = []
        for did in sorted_doc_ids:
            if did in doc_data:
                result = doc_data[did].copy()
                result["document_id"] = did
                result["score"] = rrf_scores[did]
                # Preserve chunks list if present
                if "chunks" in doc_data[did]:
                    result["chunks"] = doc_data[did]["chunks"]
                combined_results.append(result)

        perf.info(
            "[connector_svc] _combined_rrf_search TOTAL in %.3fs results=%d type=%s space=%d",
            time.perf_counter() - t0,
            len(combined_results),
            document_type,
            search_space_id,
        )
        return combined_results

    def _get_doc_url(self, metadata: dict[str, Any]) -> str:
        return (
            metadata.get("url")
            or metadata.get("source")
            or metadata.get("page_url")
            or metadata.get("VisitedWebPageURL")
            or ""
        )

    def _chunk_preview(self, text: str, limit: int = 200) -> str:
        if not text:
            return ""
        text = str(text)
        if len(text) <= limit:
            return text
        return text[:limit] + "..."

    def _build_chunk_sources_from_documents(
        self,
        documents: list[dict[str, Any]],
        *,
        title_fn=None,
        description_fn=None,
        url_fn=None,
        extra_fields_fn=None,
    ) -> list[dict[str, Any]]:
        """
        Build a chunk-level `sources` list from document-grouped results.

        Each chunk becomes a source with `id == chunk_id` so the frontend can resolve
        citations like `[citation:<chunk_id>]`.
        """
        sources: list[dict[str, Any]] = []

        for doc in documents:
            doc_info = doc.get("document", {}) or {}
            metadata = doc_info.get("metadata", {}) or {}
            url = url_fn(doc_info, metadata) if url_fn else self._get_doc_url(metadata)
            chunks = doc.get("chunks", []) or []
            display_title = (
                title_fn(doc_info, metadata)
                if title_fn
                else doc_info.get("title", "Untitled Document")
            )
            for chunk in chunks:
                chunk_id = chunk.get("chunk_id")
                chunk_content = chunk.get("content", "")
                description = (
                    description_fn(chunk, doc_info, metadata)
                    if description_fn
                    else self._chunk_preview(chunk_content)
                )
                source = {
                    "id": chunk_id,
                    "title": display_title,
                    "description": description,
                    "url": url,
                }
                if extra_fields_fn:
                    source.update(extra_fields_fn(chunk, doc_info, metadata) or {})
                sources.append(source)
        return sources

    async def get_connector_by_type(
        self,
        connector_type: SearchSourceConnectorType,
        search_space_id: int,
    ) -> SearchSourceConnector | None:
        """
        Get a connector by type for a specific search space

        Args:
            connector_type: The connector type to retrieve
            search_space_id: The search space ID to filter by

        Returns:
            Optional[SearchSourceConnector]: The connector if found, None otherwise
        """
        query = select(SearchSourceConnector).filter(
            SearchSourceConnector.search_space_id == search_space_id,
            SearchSourceConnector.connector_type == connector_type,
        )

        result = await self.session.execute(query)
        return result.scalars().first()



    async def search_notes(
        self,
        user_query: str,
        search_space_id: int,
        top_k: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple:
        """
        Search for Notes and return both the source information and langchain documents.

        Uses combined chunk-level and document-level hybrid search with RRF fusion.

        Args:
            user_query: The user's query
            search_space_id: The search space ID to search in
            top_k: Maximum number of results to return
            start_date: Optional start date for filtering documents by updated_at
            end_date: Optional end date for filtering documents by updated_at

        Returns:
            tuple: (sources_info, langchain_documents)
        """
        notes_docs = await self._combined_rrf_search(
            query_text=user_query,
            search_space_id=search_space_id,
            document_type="NOTE",
            top_k=top_k,
            start_date=start_date,
            end_date=end_date,
        )

        # Early return if no results
        if not notes_docs:
            return {
                "id": 51,
                "name": "Notes",
                "type": "NOTE",
                "sources": [],
            }, []

        def _title_fn(doc_info: dict[str, Any], metadata: dict[str, Any]) -> str:
            return doc_info.get("title", "Untitled Note")

        def _url_fn(_doc_info: dict[str, Any], _metadata: dict[str, Any]) -> str:
            return ""  # Notes don't have URLs

        def _description_fn(
            chunk: dict[str, Any], _doc_info: dict[str, Any], _metadata: dict[str, Any]
        ) -> str:
            return self._chunk_preview(chunk.get("content", ""), limit=200)

        sources_list = self._build_chunk_sources_from_documents(
            notes_docs,
            title_fn=_title_fn,
            url_fn=_url_fn,
            description_fn=_description_fn,
        )

        # Create result object
        result_object = {
            "id": 51,
            "name": "Notes",
            "type": "NOTE",
            "sources": sources_list,
        }

        return result_object, notes_docs

    # =========================================================================
    # Composio Connector Search Methods
    # =========================================================================

    async def search_composio_google_drive(
        self,
        user_query: str,
        search_space_id: int,
        top_k: int = 20,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple:
        """
        Search for Composio Google Drive files and return both the source information
        and langchain documents.

        Uses combined chunk-level and document-level hybrid search with RRF fusion.

        Args:
            user_query: The user's query
            search_space_id: The search space ID to search in
            top_k: Maximum number of results to return
            start_date: Optional start date for filtering documents by updated_at
            end_date: Optional end date for filtering documents by updated_at

        Returns:
            tuple: (sources_info, langchain_documents)
        """
        composio_drive_docs = await self._combined_rrf_search(
            query_text=user_query,
            search_space_id=search_space_id,
            document_type="COMPOSIO_GOOGLE_DRIVE_CONNECTOR",
            top_k=top_k,
            start_date=start_date,
            end_date=end_date,
        )

        # Early return if no results
        if not composio_drive_docs:
            return {
                "id": 54,
                "name": "Google Drive (Composio)",
                "type": "COMPOSIO_GOOGLE_DRIVE_CONNECTOR",
                "sources": [],
            }, []

        def _title_fn(doc_info: dict[str, Any], metadata: dict[str, Any]) -> str:
            return (
                doc_info.get("title")
                or metadata.get("title")
                or metadata.get("file_name")
                or "Untitled Document"
            )

        def _url_fn(_doc_info: dict[str, Any], metadata: dict[str, Any]) -> str:
            return metadata.get("url") or metadata.get("web_view_link") or ""

        def _description_fn(
            chunk: dict[str, Any], _doc_info: dict[str, Any], metadata: dict[str, Any]
        ) -> str:
            description = self._chunk_preview(chunk.get("content", ""), limit=200)
            info_parts = []
            mime_type = metadata.get("mime_type")
            modified_time = metadata.get("modified_time")
            if mime_type:
                info_parts.append(f"Type: {mime_type}")
            if modified_time:
                info_parts.append(f"Modified: {modified_time}")
            if info_parts:
                description = (description + " | " + " | ".join(info_parts)).strip(" |")
            return description

        def _extra_fields_fn(
            _chunk: dict[str, Any], _doc_info: dict[str, Any], metadata: dict[str, Any]
        ) -> dict[str, Any]:
            return {
                "mime_type": metadata.get("mime_type", ""),
                "file_id": metadata.get("file_id", ""),
                "modified_time": metadata.get("modified_time", ""),
            }

        sources_list = self._build_chunk_sources_from_documents(
            composio_drive_docs,
            title_fn=_title_fn,
            url_fn=_url_fn,
            description_fn=_description_fn,
            extra_fields_fn=_extra_fields_fn,
        )

        # Create result object
        result_object = {
            "id": 54,
            "name": "Google Drive (Composio)",
            "type": "COMPOSIO_GOOGLE_DRIVE_CONNECTOR",
            "sources": sources_list,
        }

        return result_object, composio_drive_docs

    # =========================================================================
    # Utility Methods for Connector Discovery
    # =========================================================================

    async def get_available_connectors(
        self,
        search_space_id: int,
    ) -> list[SearchSourceConnectorType]:
        """
        Get all available (enabled) connector types for a search space.

        Args:
            search_space_id: The search space ID

        Returns:
            List of SearchSourceConnectorType enums for enabled connectors
        """
        query = (
            select(SearchSourceConnector.connector_type)
            .filter(
                SearchSourceConnector.search_space_id == search_space_id,
            )
            .distinct()
        )

        result = await self.session.execute(query)
        connector_types = result.scalars().all()
        return [
            connector_type
            for connector_type in connector_types
            if connector_type not in DECOMMISSIONED_CONNECTOR_TYPES
        ]

    async def get_available_document_types(
        self,
        search_space_id: int,
    ) -> list[str]:
        """
        Get all document types that have at least one document in the search space.

        Args:
            search_space_id: The search space ID

        Returns:
            List of document type strings that have documents indexed
        """
        from sqlalchemy import distinct

        from app.db import Document

        query = select(distinct(Document.document_type)).filter(
            Document.search_space_id == search_space_id,
        )

        result = await self.session.execute(query)
        doc_types = result.scalars().all()
        return [str(dt) for dt in doc_types]

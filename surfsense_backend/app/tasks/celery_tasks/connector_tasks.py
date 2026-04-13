"""Celery tasks for connector indexing."""

import asyncio
import logging
import traceback
from collections.abc import Awaitable, Callable

from app.celery_app import celery_app
from app.tasks.celery_tasks import get_celery_session_maker

logger = logging.getLogger(__name__)


def _handle_greenlet_error(e: Exception, task_name: str, connector_id: int) -> None:
    """Log greenlet errors with context for debugging."""
    error_str = str(e)
    if "greenlet_spawn has not been called" in error_str:
        logger.error(
            f"GREENLET ERROR in {task_name} for connector {connector_id}: {error_str}\n"
            f"This typically means SQLAlchemy tried lazy-loading outside async context.\n"
            f"Stack trace:\n{traceback.format_exc()}"
        )
    else:
        logger.error(
            f"Error in {task_name} for connector {connector_id}: {error_str}\n"
            f"Stack trace:\n{traceback.format_exc()}"
        )


def _run_async(coro: Awaitable[None]) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


async def _run_with_session(
    runner: Callable[..., Awaitable[None]],
    connector_id: int,
    search_space_id: int,
    user_id: str,
    start_date: str | None,
    end_date: str | None,
) -> None:
    async with get_celery_session_maker()() as session:
        await runner(
            session,
            connector_id,
            search_space_id,
            user_id,
            start_date,
            end_date,
        )


@celery_app.task(name="index_github_repos", bind=True)
def index_github_repos_task(
    self,
    connector_id: int,
    search_space_id: int,
    user_id: str,
    start_date: str | None,
    end_date: str | None,
):
    from app.routes.search_source_connectors_routes import run_github_indexing

    _run_async(
        _run_with_session(
            run_github_indexing,
            connector_id,
            search_space_id,
            user_id,
            start_date,
            end_date,
        )
    )


@celery_app.task(name="index_google_drive_files", bind=True)
def index_google_drive_files_task(
    self,
    connector_id: int,
    search_space_id: int,
    user_id: str,
    items_dict: dict,
):
    async def _run() -> None:
        from app.routes.search_source_connectors_routes import run_google_drive_indexing

        async with get_celery_session_maker()() as session:
            await run_google_drive_indexing(
                session,
                connector_id,
                search_space_id,
                user_id,
                items_dict,
            )

    _run_async(_run())


@celery_app.task(name="index_luma_events", bind=True)
def index_luma_events_task(
    self,
    connector_id: int,
    search_space_id: int,
    user_id: str,
    start_date: str | None,
    end_date: str | None,
):
    from app.routes.search_source_connectors_routes import run_luma_indexing

    _run_async(
        _run_with_session(
            run_luma_indexing,
            connector_id,
            search_space_id,
            user_id,
            start_date,
            end_date,
        )
    )


@celery_app.task(name="index_elasticsearch_documents", bind=True)
def index_elasticsearch_documents_task(
    self,
    connector_id: int,
    search_space_id: int,
    user_id: str,
    start_date: str | None,
    end_date: str | None,
):
    from app.routes.search_source_connectors_routes import run_elasticsearch_indexing

    _run_async(
        _run_with_session(
            run_elasticsearch_indexing,
            connector_id,
            search_space_id,
            user_id,
            start_date,
            end_date,
        )
    )


@celery_app.task(name="index_crawled_urls", bind=True)
def index_crawled_urls_task(
    self,
    connector_id: int,
    search_space_id: int,
    user_id: str,
    start_date: str | None,
    end_date: str | None,
):
    from app.routes.search_source_connectors_routes import run_web_page_indexing

    try:
        _run_async(
            _run_with_session(
                run_web_page_indexing,
                connector_id,
                search_space_id,
                user_id,
                start_date,
                end_date,
            )
        )
    except Exception as e:
        _handle_greenlet_error(e, "index_crawled_urls", connector_id)
        raise


@celery_app.task(name="index_bookstack_pages", bind=True)
def index_bookstack_pages_task(
    self,
    connector_id: int,
    search_space_id: int,
    user_id: str,
    start_date: str | None,
    end_date: str | None,
):
    from app.routes.search_source_connectors_routes import run_bookstack_indexing

    _run_async(
        _run_with_session(
            run_bookstack_indexing,
            connector_id,
            search_space_id,
            user_id,
            start_date,
            end_date,
        )
    )


@celery_app.task(name="index_obsidian_vault", bind=True)
def index_obsidian_vault_task(
    self,
    connector_id: int,
    search_space_id: int,
    user_id: str,
    start_date: str | None,
    end_date: str | None,
):
    from app.routes.search_source_connectors_routes import run_obsidian_indexing

    _run_async(
        _run_with_session(
            run_obsidian_indexing,
            connector_id,
            search_space_id,
            user_id,
            start_date,
            end_date,
        )
    )


@celery_app.task(name="index_composio_connector", bind=True)
def index_composio_connector_task(
    self,
    connector_id: int,
    search_space_id: int,
    user_id: str,
    start_date: str | None,
    end_date: str | None,
):
    from app.routes.search_source_connectors_routes import run_composio_indexing

    _run_async(
        _run_with_session(
            run_composio_indexing,
            connector_id,
            search_space_id,
            user_id,
            start_date,
            end_date,
        )
    )

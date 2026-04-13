"""Decommissioned Notion update-page tool."""

from langchain_core.tools import tool

_DECOMMISSIONED = "Notion connector has been decommissioned and is no longer supported."


def create_update_notion_page_tool(*args, **kwargs):
    @tool
    async def update_notion_page(*tool_args, **tool_kwargs) -> dict:
        return {"status": "error", "message": _DECOMMISSIONED}

    return update_notion_page

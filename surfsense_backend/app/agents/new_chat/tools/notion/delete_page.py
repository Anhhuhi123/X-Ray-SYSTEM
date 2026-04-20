"""Decommissioned Notion delete-page tool."""

from langchain_core.tools import tool

_DECOMMISSIONED = "Notion connector has been decommissioned and is no longer supported."


def create_delete_notion_page_tool(*args, **kwargs):
    @tool
    async def delete_notion_page(*tool_args, **tool_kwargs) -> dict:
        return {"status": "error", "message": _DECOMMISSIONED}

    return delete_notion_page

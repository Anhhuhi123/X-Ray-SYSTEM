"""Decommissioned Linear update-issue tool."""

from langchain_core.tools import tool

_DECOMMISSIONED = "Linear connector has been decommissioned and is no longer supported."


def create_update_linear_issue_tool(*args, **kwargs):
    @tool
    async def update_linear_issue(*tool_args, **tool_kwargs) -> dict:
        return {"status": "error", "message": _DECOMMISSIONED}

    return update_linear_issue

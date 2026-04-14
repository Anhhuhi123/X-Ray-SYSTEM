"""
Connector indexers module for background tasks.

This module provides a collection of connector indexers for different platforms
and services. Each indexer is responsible for handling the indexing of content
from a specific connector type.

Available indexers:
- Slack: Index messages from Slack channels
- Notion: Index pages from Notion workspaces
- Linear: Index issues from Linear workspaces
- Jira: Index issues from Jira projects
- Confluence: Index pages from Confluence spaces
- Discord: Index messages from Discord servers
- ClickUp: Index tasks from ClickUp workspaces
- Google Gmail: Index messages from Google Gmail
- Google Calendar: Index events from Google Calendar
- Webcrawler: Index crawled URLs
"""

# Communication platforms
# Calendar and scheduling
from .airtable_indexer import index_airtable_records
from .clickup_indexer import index_clickup_tasks
from .confluence_indexer import index_confluence_pages
from .discord_indexer import index_discord_messages

# Development platforms
from .google_calendar_indexer import index_google_calendar_events
from .google_drive_indexer import index_google_drive_files
from .google_gmail_indexer import index_google_gmail_messages
from .jira_indexer import index_jira_issues

# Issue tracking and project management
from .linear_indexer import index_linear_issues

# Documentation and knowledge management
from .notion_indexer import index_notion_pages
from .obsidian_indexer import index_obsidian_vault
from .slack_indexer import index_slack_messages
from .webcrawler_indexer import index_crawled_urls

__all__ = [  # noqa: RUF022
    "index_airtable_records",
    "index_clickup_tasks",
    "index_confluence_pages",
    "index_discord_messages",
    # Calendar and scheduling
    "index_google_calendar_events",
    "index_google_drive_files",
    "index_jira_issues",
    # Issue tracking and project management
    "index_linear_issues",
    # Documentation and knowledge management
    "index_notion_pages",
    "index_obsidian_vault",
    "index_crawled_urls",
    # Communication platforms
    "index_slack_messages",
    "index_google_gmail_messages",
]

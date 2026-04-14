from app.db import SearchSourceConnectorType

# Connectors intentionally decommissioned from runtime indexing/auth flows.
DECOMMISSIONED_CONNECTOR_TYPES: set[SearchSourceConnectorType] = {
    SearchSourceConnectorType.SLACK_CONNECTOR,
    SearchSourceConnectorType.TEAMS_CONNECTOR,
    SearchSourceConnectorType.NOTION_CONNECTOR,
    SearchSourceConnectorType.LINEAR_CONNECTOR,
    SearchSourceConnectorType.JIRA_CONNECTOR,
    SearchSourceConnectorType.CONFLUENCE_CONNECTOR,
    SearchSourceConnectorType.CLICKUP_CONNECTOR,
    SearchSourceConnectorType.GOOGLE_CALENDAR_CONNECTOR,
    SearchSourceConnectorType.AIRTABLE_CONNECTOR,
    SearchSourceConnectorType.GOOGLE_GMAIL_CONNECTOR,
    SearchSourceConnectorType.GOOGLE_DRIVE_CONNECTOR,
    SearchSourceConnectorType.DISCORD_CONNECTOR,
    SearchSourceConnectorType.CIRCLEBACK_CONNECTOR,
    SearchSourceConnectorType.COMPOSIO_GMAIL_CONNECTOR,
    SearchSourceConnectorType.COMPOSIO_GOOGLE_CALENDAR_CONNECTOR,
}


DECOMMISSIONED_CONNECTOR_TYPE_VALUES: set[str] = {
    connector_type.value for connector_type in DECOMMISSIONED_CONNECTOR_TYPES
}

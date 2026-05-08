from app.db import SearchSourceConnectorType

# Connectors intentionally decommissioned from runtime indexing/auth flows.
DECOMMISSIONED_CONNECTOR_TYPES: set[SearchSourceConnectorType] = set()


DECOMMISSIONED_CONNECTOR_TYPE_VALUES: set[str] = {
    connector_type.value for connector_type in DECOMMISSIONED_CONNECTOR_TYPES
}

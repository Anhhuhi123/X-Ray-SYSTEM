"""Decommissioned Linear tool metadata service."""

from dataclasses import dataclass


@dataclass
class LinearWorkspace:
    id: int = 0
    name: str = "Linear (decommissioned)"
    organization_name: str = "Linear (decommissioned)"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "organization_name": self.organization_name,
        }


@dataclass
class LinearIssue:
    id: str = ""
    identifier: str = ""
    title: str = ""
    state: str = ""
    connector_id: int = 0
    document_id: int = 0
    indexed_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "identifier": self.identifier,
            "title": self.title,
            "state": self.state,
            "connector_id": self.connector_id,
            "document_id": self.document_id,
            "indexed_at": self.indexed_at,
        }


class LinearToolMetadataService:
    def __init__(self, db_session):
        self._db_session = db_session

    async def get_creation_context(self, *args, **kwargs) -> dict:
        return {
            "error": "Linear connector has been decommissioned and is no longer supported."
        }

    async def get_update_context(self, *args, **kwargs) -> dict:
        return {
            "error": "Linear connector has been decommissioned and is no longer supported."
        }

    async def get_delete_context(self, *args, **kwargs) -> dict:
        return {
            "error": "Linear connector has been decommissioned and is no longer supported."
        }

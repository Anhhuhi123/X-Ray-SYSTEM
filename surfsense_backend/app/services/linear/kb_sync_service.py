"""Decommissioned Linear KB sync service."""


class LinearKBSyncService:
    def __init__(self, db_session):
        self.db_session = db_session

    async def sync_after_update(self, *args, **kwargs) -> dict:
        return {
            "status": "error",
            "message": "Linear connector has been decommissioned and is no longer supported.",
        }

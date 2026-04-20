"""Utilities for retrieving Google account identity information."""

import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def fetch_google_user_email(credentials: Credentials) -> str | None:
    """Fetch the authenticated user's email address via Gmail profile API."""
    try:
        service = build("gmail", "v1", credentials=credentials)
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress")
        if email:
            logger.debug(f"Fetched Google user email: {email}")
            return email
        return None
    except Exception as e:
        logger.warning(f"Error fetching Google user email: {e!s}")
        return None

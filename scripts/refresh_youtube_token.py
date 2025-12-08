#!/usr/bin/env python3
"""
Refresh YouTube OAuth2 token stored in upload_video.py-oauth2.json
"""
import os
import logging
import httplib2
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OAUTH_FILE = os.getenv('YOUTUBE_OAUTH_FILE', 'upload_video.py-oauth2.json')
CLIENT_SECRETS = os.getenv('YOUTUBE_CLIENT_SECRETS', 'client_secrets.json')

if not os.path.exists(OAUTH_FILE):
    logger.error(f"OAuth storage file not found: {OAUTH_FILE}")
    raise SystemExit(1)

storage = Storage(OAUTH_FILE)
credentials = storage.get()

if credentials is None:
    logger.error("No credentials found in storage. Please perform initial OAuth flow.")
    raise SystemExit(1)

logger.info(f"Current token expiry: {getattr(credentials, 'token_expiry', None)}")

if not hasattr(credentials, 'refresh_token') or not credentials.refresh_token:
    logger.error("No refresh token available. You must re-run the OAuth consent flow manually.")
    raise SystemExit(1)

try:
    logger.info("Refreshing credentials...")
    credentials.refresh(httplib2.Http())
    storage.put(credentials)
    logger.info("Successfully refreshed YouTube OAuth credentials.")
    logger.info(f"New expiry: {getattr(credentials, 'token_expiry', None)}")
    print("REFRESH_OK")
except AccessTokenRefreshError as e:
    logger.error(f"AccessTokenRefreshError: {e}")
    raise SystemExit(2)
except Exception as e:
    logger.exception(f"Unexpected error while refreshing credentials: {e}")
    raise SystemExit(3)

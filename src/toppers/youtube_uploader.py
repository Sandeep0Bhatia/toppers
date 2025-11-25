"""
YouTube video uploader for Toppers Top 10 videos
"""
import http.client as httplib
import httplib2
import os
import random
import time
import logging
from typing import Optional, Dict

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets, AccessTokenRefreshError
from oauth2client.file import Storage

logger = logging.getLogger(__name__)

# Retry configuration
httplib2.RETRIES = 1
MAX_RETRIES = 10

RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error, IOError, httplib.NotConnected,
    httplib.IncompleteRead, httplib.ImproperConnectionState,
    httplib.CannotSendRequest, httplib.CannotSendHeader,
    httplib.ResponseNotReady, httplib.BadStatusLine
)

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# YouTube API configuration
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


class YouTubeUploader:
    """Handles YouTube video uploads with OAuth2 authentication"""

    def __init__(
        self,
        client_secrets_file: str = "client_secrets.json",
        oauth_storage_file: str = "upload_video.py-oauth2.json"
    ):
        """
        Initialize YouTube uploader.

        Args:
            client_secrets_file: Path to OAuth client secrets JSON
            oauth_storage_file: Path to stored OAuth credentials
        """
        self.client_secrets_file = client_secrets_file
        self.oauth_storage_file = oauth_storage_file
        self.youtube = None

    def get_authenticated_service(self) -> any:
        """
        Get authenticated YouTube service with automatic credential refresh.

        Returns:
            Authenticated YouTube API service
        """
        if self.youtube:
            return self.youtube

        if not os.path.exists(self.client_secrets_file):
            raise FileNotFoundError(
                f"Client secrets file not found: {self.client_secrets_file}"
            )

        flow = flow_from_clientsecrets(
            self.client_secrets_file,
            scope=YOUTUBE_UPLOAD_SCOPE
        )

        storage = Storage(self.oauth_storage_file)
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            # Try to refresh credentials if they exist but are invalid
            if credentials is not None and hasattr(credentials, 'refresh_token'):
                try:
                    logger.info("Attempting to refresh expired YouTube credentials...")
                    credentials.refresh(httplib2.Http())
                    storage.put(credentials)
                    logger.info("✓ YouTube credentials refreshed successfully")
                except AccessTokenRefreshError as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    logger.warning("OAuth credentials invalid. Manual authentication required.")
                    raise Exception("OAuth credentials expired and refresh failed. Please re-authenticate.")
                except Exception as e:
                    logger.error(f"Unexpected error refreshing credentials: {e}")
                    raise Exception("OAuth credentials not valid. Please re-authenticate.")
            else:
                logger.warning("OAuth credentials invalid or missing. Manual authentication required.")
                raise Exception("OAuth credentials not valid. Please re-authenticate.")

        self.youtube = build(
            YOUTUBE_API_SERVICE_NAME,
            YOUTUBE_API_VERSION,
            http=credentials.authorize(httplib2.Http())
        )

        return self.youtube

    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str,
        category: str = "24",  # 24 = Entertainment
        keywords: Optional[list] = None,
        privacy_status: str = "public"
    ) -> Optional[str]:
        """
        Upload video to YouTube.

        Args:
            file_path: Path to video file
            title: Video title
            description: Video description
            category: YouTube category ID (default: 24 = Entertainment)
            keywords: List of keywords/tags
            privacy_status: "public", "private", or "unlisted"

        Returns:
            Video ID if successful, None otherwise
        """
        if not os.path.exists(file_path):
            logger.error(f"Video file not found: {file_path}")
            return None

        if privacy_status not in VALID_PRIVACY_STATUSES:
            logger.warning(f"Invalid privacy status: {privacy_status}. Using 'public'")
            privacy_status = "public"

        try:
            youtube = self.get_authenticated_service()

            body = dict(
                snippet=dict(
                    title=title,
                    description=description,
                    tags=keywords or [],
                    categoryId=category
                ),
                status=dict(
                    privacyStatus=privacy_status,
                    selfDeclaredMadeForKids=False
                )
            )

            logger.info(f"Uploading video: {title}")
            logger.info(f"File: {file_path}")
            logger.info(f"Privacy: {privacy_status}")

            insert_request = youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
            )

            video_id = self._resumable_upload(insert_request)
            return video_id

        except HttpError as e:
            logger.error(f"YouTube API error: {e.resp.status} - {e.content}")
            return None
        except Exception as e:
            logger.error(f"Upload error: {str(e)}", exc_info=True)
            return None

    def _resumable_upload(self, insert_request) -> Optional[str]:
        """
        Handle resumable upload with exponential backoff.

        Args:
            insert_request: YouTube API insert request

        Returns:
            Video ID if successful
        """
        response = None
        error = None
        retry = 0

        while response is None:
            try:
                logger.info("Uploading video chunks...")
                status, response = insert_request.next_chunk()

                if response is not None:
                    if 'id' in response:
                        video_id = response['id']
                        logger.info(f"Video uploaded successfully! ID: {video_id}")
                        logger.info(f"Video URL: https://www.youtube.com/watch?v={video_id}")
                        return video_id
                    else:
                        logger.error(f"Unexpected response: {response}")
                        return None

            except HttpError as e:
                if e.resp.status in RETRIABLE_STATUS_CODES:
                    error = f"Retriable HTTP error {e.resp.status}: {e.content}"
                else:
                    raise

            except RETRIABLE_EXCEPTIONS as e:
                error = f"Retriable error: {e}"

            if error is not None:
                logger.warning(error)
                retry += 1

                if retry > MAX_RETRIES:
                    logger.error("Max retries exceeded. Upload failed.")
                    return None

                max_sleep = 2 ** retry
                sleep_seconds = random.random() * max_sleep
                logger.info(f"Sleeping {sleep_seconds:.2f} seconds before retry...")
                time.sleep(sleep_seconds)

        return None


def upload_toppers_video(
    video_path: str,
    topic: str,
    summary: str,
    privacy_status: str = "public"
) -> Optional[str]:
    """
    Convenience function to upload Top 10 video.

    Args:
        video_path: Path to generated video
        topic: Top 10 topic/title
        summary: Brief content summary
        privacy_status: YouTube privacy setting

    Returns:
        Video ID if successful
    """
    uploader = YouTubeUploader()

    # Create title
    title = topic if topic.startswith("Top 10") else f"Top 10 {topic}"

    # Create description
    description = f"""{summary}

What do you think about this list? Drop your opinion in the comments!

Subscribe for more fascinating Top 10 lists about culture, beauty, innovation, and human achievement from around the world.

#top10 #top10list #trending #viral #shorts #youtubeshorts #facts #interesting #educational"""

    keywords = [
        "top 10",
        "top 10 list",
        "countdown",
        "facts",
        "interesting",
        "educational",
        "trending",
        "viral",
        "shorts",
        "youtube shorts"
    ]

    return uploader.upload_video(
        file_path=video_path,
        title=title,
        description=description,
        category="24",  # Entertainment
        keywords=keywords,
        privacy_status=privacy_status
    )

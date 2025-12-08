#!/usr/bin/env python3
"""
Perform OAuth2 flow to obtain YouTube credentials and save to upload_video.py-oauth2.json
This script will print a URL; open it in a browser, approve, then paste the code here.
"""
import os
import json
import logging
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLIENT_SECRETS = os.getenv('YOUTUBE_CLIENT_SECRETS', 'client_secrets.json')
OAUTH_FILE = os.getenv('YOUTUBE_OAUTH_FILE', 'upload_video.py-oauth2.json')
SCOPE = 'https://www.googleapis.com/auth/youtube'

if not os.path.exists(CLIENT_SECRETS):
    logger.error(f"client_secrets.json not found at {CLIENT_SECRETS}. Place your OAuth client secrets there.")
    raise SystemExit(1)

flow = flow_from_clientsecrets(CLIENT_SECRETS, scope=SCOPE, redirect_uri='urn:ietf:wg:oauth:2.0:oob')

auth_uri = flow.step1_get_authorize_url()
print('\nPlease open this URL in your browser, authorize the application, then paste the authorization code here:\n')
print(auth_uri)

code = input('\nEnter the authorization code: ').strip()
if not code:
    logger.error('No code provided. Exiting.')
    raise SystemExit(1)

try:
    credentials = flow.step2_exchange(code)
    storage = Storage(OAUTH_FILE)
    storage.put(credentials)
    logger.info(f'Credentials saved to {OAUTH_FILE}')
    print('OK')
except Exception as e:
    logger.exception(f'Failed to exchange code for credentials: {e}')
    raise SystemExit(1)

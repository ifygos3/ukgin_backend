"""
One-time helper to generate a YouTube OAuth 2.0 refresh token.

Prerequisites:
    1. Create a project in Google Cloud Console.
    2. Enable the YouTube Data API v3.
    3. Create OAuth 2.0 Client credentials (type: Desktop app).
    4. Add http://localhost:8080/ to your OAuth consent screen's
       "Authorized redirect URIs".
    5. Install dependencies:
           pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
    6. Set these environment variables before running:
           YOUTUBE_CLIENT_ID=your-client-id.apps.googleusercontent.com
           YOUTUBE_CLIENT_SECRET=your-client-secret
    7. Run this script, open the printed URL in a browser, authorize the
       account that owns the YouTube channel, and paste the resulting
       code back into the terminal.

The script will print the refresh token. Copy it into your .env file
as YOUTUBE_REFRESH_TOKEN=<token>.

WARNING:
    Do NOT commit this script or your .env file to version control.
    The refresh token is long-lived and grants upload access to your
    YouTube channel.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django so we can reuse existing settings if available.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ukgin_config.settings')
try:
    import django
    django.setup()
    from django.conf import settings
    CLIENT_ID = getattr(settings, 'YOUTUBE_CLIENT_ID', '') or os.getenv('YOUTUBE_CLIENT_ID', '')
    CLIENT_SECRET = getattr(settings, 'YOUTUBE_CLIENT_SECRET', '') or os.getenv('YOUTUBE_CLIENT_SECRET', '')
except Exception:
    settings = None
    CLIENT_ID = os.getenv('YOUTUBE_CLIENT_ID', '')
    CLIENT_SECRET = os.getenv('YOUTUBE_CLIENT_SECRET', '')

if not CLIENT_ID or not CLIENT_SECRET:
    print('Error: YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET environment variables are required.')
    sys.exit(1)

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
except ImportError:
    print('Error: Missing required packages.')
    print('Install them with:')
    print('    pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client')
    sys.exit(1)


SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
REDIRECT_URI = 'http://localhost:8080/'


def main():
    print('Starting YouTube OAuth flow...')
    print(f'Client ID: {CLIENT_ID}')
    print(f'Redirect URI: {REDIRECT_URI}')
    print()

    flow = InstalledAppFlow.from_client_config(
        {
            'installed': {
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'redirect_uris': [REDIRECT_URI],
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
            }
        },
        scopes=SCOPES,
    )

    try:
        creds = flow.run_local_server(port=8080, prompt='consent')
    except Exception as exc:
        print(f'\nOAuth flow failed: {exc}')
        print('Make sure you added http://localhost:8080/ as an authorized redirect URI in Google Cloud Console.')
        sys.exit(1)

    refresh_token = creds.refresh_token
    if not refresh_token:
        print('Error: No refresh token was returned. Make sure you requested offline access (prompt=consent).')
        sys.exit(1)

    print('\n' + '=' * 60)
    print('SUCCESS! Copy the refresh token below into your .env file.')
    print('=' * 60)
    print(f'YOUTUBE_REFRESH_TOKEN={refresh_token}')
    print('=' * 60)
    print('\nAdd it to your backend/.env file, then restart your Django server.')


if __name__ == '__main__':
    main()

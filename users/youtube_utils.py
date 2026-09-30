import os
import io
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django.conf import settings


YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def _get_youtube_credentials():
    if not all([settings.YOUTUBE_CLIENT_ID, settings.YOUTUBE_CLIENT_SECRET, settings.YOUTUBE_REFRESH_TOKEN]):
        raise RuntimeError(
            'YouTube is not configured. Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, and YOUTUBE_REFRESH_TOKEN in your environment.'
        )
    creds = Credentials(
        None,
        refresh_token=settings.YOUTUBE_REFRESH_TOKEN,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.YOUTUBE_CLIENT_ID,
        client_secret=settings.YOUTUBE_CLIENT_SECRET,
        scopes=YOUTUBE_SCOPES,
    )
    if not creds.valid:
        creds.refresh(Request())
    return creds


def upload_video_to_youtube(title, description, file_path, tags=None, privacy_status='public'):
    creds = _get_youtube_credentials()
    youtube = build('youtube', 'v3', credentials=creds)

    body = {
        'snippet': {
            'title': title or 'UKGIN Gallery Video',
            'description': description or '',
            'tags': tags or ['UKGIN', 'gallery'],
            'categoryId': '22',
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False,
        },
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype='video/*')
    request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f'[YouTubeUpload] Upload progress: {int(status.progress() * 100)}%')

    video_id = response.get('id')
    if not video_id:
        raise RuntimeError('YouTube upload failed: no video ID returned.')

    channel_handle = getattr(settings, 'YOUTUBE_CHANNEL_HANDLE', '@ukginglobal')
    return f'https://www.youtube.com/watch?v={video_id}', video_id

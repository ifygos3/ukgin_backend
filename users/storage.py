import mimetypes
import posixpath

from django.core.files.base import ContentFile, File
from django.core.files.storage import Storage
from django.urls import reverse


class DatabaseFileStorage(Storage):
    """Stores file bytes in the database instead of on the container filesystem.

    Container filesystems are disposable, so a constitution (or any document) saved
    to /app/media disappears on the next deploy. Keeping the bytes in Postgres makes
    uploads durable on any host, including free tiers with no persistent disk.
    """

    def __init__(self, location='', base_url=None):
        self.location = location
        self.base_url = base_url

    def deconstruct(self):
        return (
            'users.storage.DatabaseFileStorage',
            [],
            {'location': self.location, 'base_url': self.base_url},
        )

    # Imported lazily: users.models imports this module for the field definition.
    @property
    def blobs(self):
        from .models import DocumentBlob
        return DocumentBlob

    def _normalize_name(self, name):
        # upload_to joins with os.sep, so names arrive as 'constitutions\\file.pdf' on Windows.
        name = posixpath.normpath(name.replace('\\', '/')).lstrip('/')
        if self.location:
            name = posixpath.join(self.location, name)
        return name

    def get_available_name(self, name, max_length=None):
        return self._normalize_name(name)

    def _save(self, name, content):
        name = self._normalize_name(name)
        if hasattr(content, 'chunks'):
            data = b''.join(content.chunks())
        else:
            data = content.read()
        content_type = getattr(content, 'content_type', '') or mimetypes.guess_type(name)[0] or 'application/octet-stream'
        self.blobs.objects.update_or_create(
            name=name,
            defaults={'data': data, 'content_type': content_type, 'size': len(data)},
        )
        return name

    def _open(self, name, mode='rb'):
        blob = self.blobs.objects.filter(name=self._normalize_name(name)).first()
        if blob is None:
            raise FileNotFoundError(f'No stored file named {name}')
        if 'w' in mode or 'a' in mode or '+' in mode:
            raise NotImplementedError('DatabaseFileStorage is read-only')
        return ContentFile(blob.data, name=name)

    def exists(self, name):
        return self.blobs.objects.filter(name=self._normalize_name(name)).exists()

    def size(self, name):
        blob = self.blobs.objects.filter(name=self._normalize_name(name)).only('size').first()
        return blob.size if blob else None

    def delete(self, name):
        deleted, _ = self.blobs.objects.filter(name=self._normalize_name(name)).delete()
        return bool(deleted)

    def url(self, name):
        # Documents are only ever served through their public streaming endpoints;
        # the Django admin still renders a working "Currently:" link through this.
        if self._normalize_name(name).startswith('constitutions/'):
            return reverse('public-constitution-file')
        return None

    def path(self, name):
        raise NotImplementedError('DatabaseFileStorage has no filesystem path')

    def listdir(self, path):
        raise NotImplementedError('DatabaseFileStorage does not support directory listing')

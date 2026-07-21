"""
Custom Django storage backend that stores media files (company logo) in a
Supabase Storage bucket via its REST API, so uploads survive Render's
ephemeral disk across redeploys instead of living only in the local
MEDIA_ROOT folder.

Uses the service_role key for all writes/deletes (server-side only, never
exposed to the browser) and relies on the bucket being public for reads,
so URLs can point straight at Supabase without per-request signing.
"""
import mimetypes
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class SupabaseStorage(Storage):
    def __init__(self):
        self.base_url = settings.SUPABASE_URL.rstrip('/')
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.bucket = settings.SUPABASE_STORAGE_BUCKET

    def _object_url(self, name):
        return f"{self.base_url}/storage/v1/object/{self.bucket}/{quote(name)}"

    def _headers(self, content_type=None):
        headers = {'Authorization': f'Bearer {self.service_key}'}
        if content_type:
            headers['Content-Type'] = content_type
        return headers

    def _save(self, name, content):
        content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        content.seek(0)
        resp = requests.put(
            self._object_url(name),
            headers=self._headers(content_type),
            data=content.read(),
            timeout=30,
        )
        resp.raise_for_status()
        return name

    def _open(self, name, mode='rb'):
        from django.core.files.base import ContentFile
        resp = requests.get(self._object_url(name), headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return ContentFile(resp.content, name=name)

    def exists(self, name):
        resp = requests.head(self._object_url(name), headers=self._headers(), timeout=15)
        return resp.status_code == 200

    def delete(self, name):
        requests.delete(self._object_url(name), headers=self._headers(), timeout=15)

    def url(self, name):
        return f"{self.base_url}/storage/v1/object/public/{self.bucket}/{quote(name)}"

    def size(self, name):
        resp = requests.head(self._object_url(name), headers=self._headers(), timeout=15)
        resp.raise_for_status()
        return int(resp.headers.get('Content-Length', 0))

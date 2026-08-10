from django.apps import AppConfig
from django.conf import settings


class UsersConfig(AppConfig):
    name = 'users'

    def ready(self):
        print(f'[EmailConfig] backend={settings.EMAIL_BACKEND}, host={settings.EMAIL_HOST}, port={settings.EMAIL_PORT}, user={settings.EMAIL_HOST_USER}, from={settings.DEFAULT_FROM_EMAIL}')

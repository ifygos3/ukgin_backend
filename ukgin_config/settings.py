import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
import cloudinary

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

load_dotenv(os.path.join(BASE_DIR, '.env'))

from cloudinary_storage.storage import MediaCloudinaryStorage
from django.core.files.uploadedfile import UploadedFile


DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024

class AutoDetectCloudinaryStorage(MediaCloudinaryStorage):
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.webm', '.mkv', '.ogg', '.ogv', '.flv', '.wmv'}
    RAW_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv', '.zip', '.rar', '.7z'}
    _detected_videos = {}
    _detected_raws = {}

    def _get_resource_type(self, name):
        if name in self._detected_videos:
            return self._detected_videos[name]
        if name in self._detected_raws:
            return self._detected_raws[name]
        extension = os.path.splitext(name)[1].lower()
        if extension in self.VIDEO_EXTENSIONS:
            self._detected_videos[name] = 'video'
            return 'video'
        if extension in self.RAW_EXTENSIONS:
            self._detected_raws[name] = 'raw'
            return 'raw'
        return super()._get_resource_type(name)

    def _save(self, name, content):
        mime_type = getattr(content, 'content_type', '') or ''
        original_name = getattr(content, 'name', '') or ''
        name = self._normalise_name(name)
        name = self._prepend_prefix(name)
        wrapped = UploadedFile(content, name)
        wrapped.content_type = mime_type
        wrapped._original_name = original_name
        response = self._upload(name, wrapped)
        result_type = response.get('resource_type', 'image')
        self._detected_videos[name] = result_type
        public_id = response.get('public_id')
        if public_id and public_id != name:
            self._detected_videos[public_id] = result_type
        return public_id

    def _upload(self, name, content):
        resource_type = self._get_resource_type(name)
        try:
            mime_type = getattr(content, 'content_type', '') or ''
            original_name = getattr(content, '_original_name', '') or getattr(content, 'name', '') or ''
            if mime_type.startswith('video/'):
                resource_type = 'video'
            elif mime_type in (
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'text/plain',
                'text/csv',
                'application/zip',
                'application/x-rar-compressed',
                'application/x-7z-compressed',
            ) or mime_type.startswith('application/') or mime_type.startswith('text/'):
                resource_type = 'raw'
            if resource_type == 'image':
                original_ext = os.path.splitext(original_name)[1].lower()
                if original_ext in self.VIDEO_EXTENSIONS:
                    resource_type = 'video'
                elif original_ext in self.RAW_EXTENSIONS:
                    resource_type = 'raw'
        except Exception:
            pass
        options = {'use_filename': True, 'resource_type': resource_type, 'tags': self.TAG}
        folder = os.path.dirname(name)
        if folder:
            options['folder'] = folder
        return cloudinary.uploader.upload(content, **options)


def get_env_value(name, cast=None):
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"The required environment variable '{name}' is not set.")
    if cast is not None:
        try:
            return cast(value)
        except ValueError as exc:
            raise RuntimeError(f"Invalid value for '{name}': {exc}") from exc
    return value


def get_optional_env_value(name, cast=None, default=None):
    value = os.getenv(name)
    if value is None:
        return default
    if cast is not None:
        try:
            return cast(value)
        except ValueError as exc:
            raise RuntimeError(f"Invalid value for '{name}': {exc}") from exc
    return value


def get_bool_env(name):
    value = get_env_value(name).strip().lower()
    if value in ('true', '1', 'yes', 'on'):
        return True
    if value in ('false', '0', 'no', 'off'):
        return False
    raise RuntimeError(f"Invalid boolean value for '{name}': '{value}'")


def get_list_env(name):
    value = get_env_value(name)
    return [item.strip() for item in value.split(',') if item.strip()]


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_value('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_bool_env('DEBUG')

ALLOWED_HOSTS = get_list_env('ALLOWED_HOSTS')
CORS_ALLOWED_ORIGINS = get_list_env('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = get_list_env('CSRF_TRUSTED_ORIGINS')

EMAIL_BACKEND = get_optional_env_value('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = get_optional_env_value('EMAIL_HOST', default='localhost')
EMAIL_PORT = int(get_optional_env_value('EMAIL_PORT', default='587'))
EMAIL_HOST_USER = get_optional_env_value('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = get_optional_env_value('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = get_optional_env_value('EMAIL_USE_TLS', default='True').strip().lower() in ('true', '1', 'yes', 'on')
DEFAULT_FROM_EMAIL = get_optional_env_value('DEFAULT_FROM_EMAIL', default='webmaster@localhost')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

USE_CONSOLE_EMAIL_BACKEND = get_optional_env_value('USE_CONSOLE_EMAIL_BACKEND', default='false').strip().lower() in ('true', '1', 'yes', 'on')
if USE_CONSOLE_EMAIL_BACKEND:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

print(f'[EmailConfig] backend={EMAIL_BACKEND}, host={EMAIL_HOST}, port={EMAIL_PORT}, user={EMAIL_HOST_USER}, from={DEFAULT_FROM_EMAIL}, console={USE_CONSOLE_EMAIL_BACKEND}')

DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary',
    'cloudinary_storage',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'users',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ukgin_config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ukgin_config.wsgi.application'
AUTH_USER_MODEL = 'users.User'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.environ.get('DB_NAME', 'ukgin_db'),
#         'USER': os.environ.get('DB_USER', 'postgres'),
#         'PASSWORD': os.environ.get('DB_PASSWORD', '556677'),
#         'HOST': os.environ.get('DB_HOST', 'localhost'),
#         'PORT': os.environ.get('DB_PORT', '5432')
#     }
# }



DATABASES = {
    'default': {
        'ENGINE': get_env_value('DB_ENGINE'),
        'NAME': get_env_value('DB_NAME'),
        'USER': get_env_value('DB_USER'),
        'PASSWORD': get_env_value('DB_PASSWORD'),
        'HOST': get_env_value('DB_HOST'),
        'PORT': get_env_value('DB_PORT', cast=int),
    }
}


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
     'DEFAULT_AUTHENTICATION_CLASSES': (
         
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,

    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JSON_ENCODER": None,
    "JWK_URL": None,
    "LEEWAY": 0,

    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTHENTICATION_RULE": "rest_framework_simplejwt.serializers.default_user_authentication_rule",
    "ON_LOGIN_SUCCESS": "rest_framework_simplejwt.serializers.default_on_login_success",
    "ON_LOGIN_FAILED": "rest_framework_simplejwt.serializers.default_on_login_failed",

    "AUTH_TOKEN_CLASSES": (
        "rest_framework_simplejwt.tokens.AccessToken",
    ),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",

    "JTI_CLAIM": "jti",

    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),

    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    "TOKEN_VERIFY_SERIALIZER": "rest_framework_simplejwt.serializers.TokenVerifySerializer",
    "TOKEN_BLACKLIST_SERIALIZER": "rest_framework_simplejwt.serializers.TokenBlacklistSerializer",
    "SLIDING_TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer",
    "SLIDING_TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSlidingSerializer",

    "CHECK_REVOKE_TOKEN": False,
    "REVOKE_TOKEN_CLAIM": "hash_password",
    "CHECK_USER_IS_ACTIVE": True,
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

CLOUDINARY_URL = os.getenv('CLOUDINARY_URL')
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
    'DEFAULT_TRANSFORMATION': {
        'quality': 'auto',
        'fetch_format': 'auto',
    },
}

USE_CLOUDINARY_STORAGE = bool(
    CLOUDINARY_URL or (
        CLOUDINARY_STORAGE['CLOUD_NAME'] and
        CLOUDINARY_STORAGE['API_KEY'] and
        CLOUDINARY_STORAGE['API_SECRET']
    )
)

STORAGES = {
    'default': {
        'BACKEND': 'ukgin_config.settings.AutoDetectCloudinaryStorage' if USE_CLOUDINARY_STORAGE else 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

if USE_CLOUDINARY_STORAGE:
    DEFAULT_FILE_STORAGE = 'ukgin_config.settings.AutoDetectCloudinaryStorage'
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'


# Default primary key field type
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

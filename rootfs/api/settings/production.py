"""
Django settings for the Drycc Resources project.
"""
import os
import uuid
import random
import string
import dj_database_url


def randstr(k):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=k))


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# drycc resources app version.
VERSION = os.environ.get('VERSION', uuid.uuid1().hex[:8])

# A boolean that turns on/off debug mode.
DEBUG = os.environ.get('DRYCC_DEBUG', 'false').lower() == "true"

# Silence two security messages around SSL as router takes care of them
SILENCED_SYSTEM_CHECKS = [
    'security.W004',
    'security.W008',
    'security.W012',
    'security.W016',
]

CONN_MAX_AGE = 60 * 3

ALLOWED_HOSTS = ['*']

TIME_ZONE = os.environ.get('TZ', 'UTC')
LANGUAGE_CODE = 'en-us'
USE_I18N = False
USE_L10N = True
USE_TZ = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                "django.template.context_processors.request",
            ],
        },
    },
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'api.middleware.DjangoAPIVersionMiddleware',
]

ROOT_URLCONF = 'api.urls'
WSGI_APPLICATION = 'api.wsgi.application'

INSTALLED_APPS = (
    'corsheaders',
    'gunicorn',
    'rest_framework',
    'api',
)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Security settings
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_HEADERS = (
    'content-type',
    'accept',
    'origin',
    'Authorization',
    'Host',
)

CORS_EXPOSE_HEADERS = (
    'DRYCC_API_VERSION',
    'DRYCC_PLATFORM_VERSION',
)

X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# standard datetime format used for logging, model timestamps, etc.
DRYCC_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

REST_FRAMEWORK = {
    'DATETIME_FORMAT': DRYCC_DATETIME_FORMAT,
    'DEFAULT_MODEL_SERIALIZER_CLASS': 'rest_framework.serializers.ModelSerializer',
    'DEFAULT_PERMISSION_CLASSES': (
        'api.permissions.IsAppUser',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'api.passthrough.ControllerPassthroughAuthentication',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'EXCEPTION_HANDLER': 'api.exceptions.custom_exception_handler',
    # This service authenticates via ControllerPassthroughAuthentication and does not
    # install django.contrib.auth/contenttypes. Disable DRF's default AnonymousUser so
    # it does not try to import django.contrib.auth.models on the unauthenticated path.
    'UNAUTHENTICATED_USER': None,
}

APPEND_SLASH = False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'root': {'level': 'DEBUG' if DEBUG else 'WARN'},
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
        },
        'api': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'scheduler': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    }
}

# names which apps cannot reserve for routing
RESERVED_NAME_PATTERNS = [r"^drycc(?:-[\w-]+)?$", r"^kube(?:-[\w-]+)?$", r"^default$"]

# default scheduler settings
SCHEDULER_MODULE = 'scheduler'
SCHEDULER_URL = "https://{}:{}".format(
    os.environ.get('KUBERNETES_SERVICE_HOST', 'kubernetes.default'),
    os.environ.get('KUBERNETES_SERVICE_PORT', '443'),
)

K8S_API_VERIFY_TLS = os.environ.get('K8S_API_VERIFY_TLS', 'true').lower() == "true"

SECRET_KEY = os.environ.get('DRYCC_SECRET_KEY', randstr(64))

# Database
DRYCC_DATABASE_URL = os.environ.get(
    'DRYCC_DATABASE_URL', 'postgres://postgres:@:5432/drycc_resources')
DATABASES = {
    'default': dj_database_url.config(default=DRYCC_DATABASE_URL)
}

# regex for validating app names and other names
APP_URL_REGEX = '[a-z0-9-]+'
NAME_REGEX = r'[a-z0-9]+(\-[a-z0-9]+)*'

# Controller passthrough settings
DRYCC_CONTROLLER_URL = os.environ.get('DRYCC_CONTROLLER_URL', 'http://drycc-controller.drycc')
DRYCC_CONTROLLER_VERIFY_TLS = os.environ.get(
    'DRYCC_CONTROLLER_VERIFY_TLS', 'true').lower() == 'true'
DRYCC_CONTROLLER_AUTH_CACHE_TTL = int(os.environ.get('DRYCC_CONTROLLER_AUTH_CACHE_TTL', '30'))
DRYCC_RESOURCES_CATALOG_CACHE_TTL = int(
    os.environ.get('DRYCC_RESOURCES_CATALOG_CACHE_TTL', '300'))

# Cache Valkey Configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get('DRYCC_VALKEY_URL', 'redis://:@127.0.0.1:6379'),
    }
}

# Quickwit Configuration (optional, for logging)
QUICKWIT_INDEXER_URL = os.environ.get('QUICKWIT_INDEXER_URL', None)
QUICKWIT_LOG_INDEX_PREFIX = os.environ.get('QUICKWIT_LOG_INDEX_PREFIX', None)

# Workflow-manager Configuration (optional, for usage reporting)
WORKFLOW_MANAGER_URL = os.environ.get('WORKFLOW_MANAGER_URL', None)
WORKFLOW_MANAGER_ACCESS_KEY = os.environ.get('WORKFLOW_MANAGER_ACCESS_KEY', None)

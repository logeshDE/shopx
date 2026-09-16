from decouple import Csv, config

from .base import *

import dj_database_url

# ── Core ───────────────────────────────────────────────────────
SECRET_KEY   = config('SECRET_KEY')
DEBUG        = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# ── Database ───────────────────────────────────────────────────
DATABASES = {
    'default': dj_database_url.parse(
        config('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ── Redis ──────────────────────────────────────────────────────
REDIS_URL = config('REDIS_URL')

CELERY_BROKER_URL        = REDIS_URL
CELERY_RESULT_BACKEND    = REDIS_URL

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

# ── Static files (WhiteNoise) ──────────────────────────────────
STATIC_URL   = '/static/'
STATIC_ROOT  = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
)

# ── Media files (Cloudinary) ───────────────────────────────────
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY':    config('CLOUDINARY_API_KEY'),
    'API_SECRET': config('CLOUDINARY_API_SECRET'),
}
MEDIA_URL = f"https://res.cloudinary.com/{config('CLOUDINARY_CLOUD_NAME')}/"

# ── Email (Brevo — 300 free emails/day) ───────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = config('EMAIL_HOST',          default='smtp-relay.brevo.com')
EMAIL_PORT          = config('EMAIL_PORT',           default=587, cast=int)
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL',  default='noreply@shopx.com')

# ── HTTPS + cookies ────────────────────────────────────────────
SESSION_COOKIE_SECURE          = True
CSRF_COOKIE_SECURE             = True
SECURE_SSL_REDIRECT            = True
SECURE_HSTS_SECONDS            = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD            = True
SECURE_PROXY_SSL_HEADER        = ('HTTP_X_FORWARDED_PROTO', 'https')

# ── CSRF: trust your Railway domain ───────────────────────────
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    cast=Csv(),
    default='',
)

# ── Rate limiting ──────────────────────────────────────────────
RATELIMIT_ENABLE = True

# ── Logging ───────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level':    'INFO',
    },
    'loggers': {
        'django': {
            'handlers':  ['console'],
            'level':     config('LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
    },
}
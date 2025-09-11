import os
import json
import ast
from pathlib import Path
from datetime import timedelta
from decouple import config


# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent


# Secrets and security
SECRET_KEY = config('SECRET_KEY')
DEBUG = True
ALLOWED_HOSTS = ['*', '139.59.29.54', 'localhost', '106.51.236.218']
INTERNAL_IPS = ['127.0.0.1', 'localhost', '106.51.236.218', '192.168.1.6', '192.168.1.11', '192.168.1.10', '10.1.2.204', '10.82.85.84', '10.141.43.117', '10.141.43.84', '10.10.1.242']


# Feature flags
ENABLE_S3 = config('ENABLE_S3', default='0') in ('1', 'true', 'True', 'yes', 'YES')


# Try-load storages so we can guard INSTALLED_APPS/config
STORAGES_AVAILABLE = False
if ENABLE_S3:
    try:
        import storages  # noqa: F401
        STORAGES_AVAILABLE = True
    except Exception:
        STORAGES_AVAILABLE = False


# Apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',

    'debug_toolbar',

    'profileDesk',
    'authDesk',
    'communityDesk',
    'storeDesk',
    'homeDesk',
    'favouriteDesk',
    'premiumDesk',
    'searchDesk',
    'notificationDesk',
    'coinManagementDesk',
    'digitalcomicDesk',
    'motioncomicDesk',
    'carouselDesk',
    'creatorDesk',
    'paymentsDesk',
]


# Add storages only if available and enabled
if STORAGES_AVAILABLE:
    INSTALLED_APPS.append('storages')


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'pratilipiPc.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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


WSGI_APPLICATION = 'pratilipiPc.wsgi.application'


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'pratilipipcdb',
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}


# Cache (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}


# Password validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# I18N / TZ
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# Static/Media
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'profileDesk.CustomUser'


# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '1000/day',
        'user': '10000/day',
        'review': '500/day',
        'wishlist': '1000/day',
        'order': '500/day',
        'submission': '100/day',
    },
    'UNAUTHENTICATED_USER': None,
    'UNAUTHENTICATED_TOKEN': None,
}


# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'LEEWAY': 60,
}


# Security (adjust to True in production)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'


# Razorpay
RAZORPAY_KEY_ID = config("RAZORPAY_KEY_ID", default=None)
RAZORPAY_KEY_SECRET = config("RAZORPAY_KEY_SECRET", default=None)
RAZORPAY_WEBHOOK_SECRET = config('RAZORPAY_WEBHOOK_SECRET', default=None)


# -----------------------------
# Google Play configuration
# -----------------------------
def _parse_json_env(name: str, default_val):
    raw = config(name, default=None)
    if not raw:
        return default_val
    try:
        return json.loads(raw)
    except Exception:
        try:
            return ast.literal_eval(raw)
        except Exception:
            return default_val


# Use your app's applicationId for dev; real value when moving to Play
GOOGLE_PLAY_PACKAGE_NAME = config('GOOGLE_PLAY_PACKAGE_NAME', default='com.pratilipi.box')

# Server-authoritative SKU maps
COIN_PACK_SKUS = _parse_json_env('COIN_PACK_SKUS', {
    'coins_100': 100,
    'coins_250': 250,
    'coins_500': 500,
    'coins_1000': 1000,
})

SUB_PLAN_SKUS = _parse_json_env('SUB_PLAN_SKUS', {
    'premium_3m': {'plan': '3_month'},
    'premium_6m': {'plan': '6_month'},
    'premium_12m': {'plan': '12_month'},
})


# -----------------------------
# AWS S3 (optional)
# -----------------------------
if STORAGES_AVAILABLE:
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default=None)
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default=None)
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default=None)
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='ap-south-1')
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = 'public-read'

    # Only enable if all essentials are present
    if all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME]):
        DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
import os  # Import os for environment variable handling
from pathlib import Path  # Import Path for file path management
from datetime import timedelta  # Import for JWT token lifetime
from decouple import config  # Import decouple for .env configuration

# Build paths inside the project like this: BASE_DIR / 'subdir'
BASE_DIR = Path(__file__).resolve().parent.parent  # Define the project base directory

# Load environment variables from .env file
SECRET_KEY = config('SECRET_KEY')  # Secure key from environment

# Security settings
DEBUG = True  # Enable debug mode for development (disable in production)
ALLOWED_HOSTS = ['*']  # Allow all for testing (restrict in production to your IPs like '192.168.1.4', '10.0.2.2')
INTERNAL_IPS = ['127.0.0.1', 'localhost', '192.168.1.9', '10.184.78.84', '10.82.85.84', '10.141.43.117', '10.141.43.84']  # Add laptop IP for debug toolbar
# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',  # Admin interface
    'django.contrib.auth',  # Authentication system
    'django.contrib.contenttypes',  # Content type framework
    'django.contrib.sessions',  # Session framework
    'django.contrib.messages',  # Message framework
    'django.contrib.staticfiles',  # Static file handling
    'rest_framework',  # REST API framework
    'rest_framework_simplejwt',  # JWT authentication
    'rest_framework_simplejwt.token_blacklist',  # Token blacklisting for logout
    'profileDesk',  # Custom app for Android users
    'authDesk',  # New authentication app
    'communityDesk', # Custom app for community features
    'storeDesk',  # Custom app for store features
    'homeDesk',  # Custom app for home features
    'favouriteDesk',  # Custom app for favourites
    'premiumDesk', # Custom app for premium features
    'searchDesk', # Custom app for search functionality
    'notificationDesk', # Custom app for notifications
    'coinManagementDesk', # Custom app for coin management
    'digitalcomicDesk', # Custom app for digital comics
    'motioncomicDesk', # Custom app for motion comics
    'carouselDesk',  # Custom app for carousel features
    'creatorDesk',  # Custom app for creator features
    'debug_toolbar',  # Debug toolbar for development
    'paymentsDesk',  # Custom app for payment features

]


MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',  # Debug toolbar middleware for development
    'django.middleware.security.SecurityMiddleware',  # Security enhancements
    'django.contrib.sessions.middleware.SessionMiddleware',  # Session management
    'django.middleware.common.CommonMiddleware',  # Common middleware
    'django.middleware.csrf.CsrfViewMiddleware',  # CSRF protection
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Authentication
    'django.contrib.messages.middleware.MessageMiddleware',  # Message handling
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Clickjacking protection
]

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/0',  # Local Redis instance, default port
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

ROOT_URLCONF = 'pratilipiPc.urls'  # Root URL configuration

# Custom User Model for the project
AUTH_USER_MODEL = 'profileDesk.CustomUser'  # Points to the custom user model

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',  # Template engine
        'DIRS': [BASE_DIR / 'templates'],  # Add this line
        'APP_DIRS': True,  # Look for templates in app directories
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',  # Request context
                'django.contrib.auth.context_processors.auth',  # Authentication context
                'django.contrib.messages.context_processors.messages',  # Message context
            ],
        },
    },
]

WSGI_APPLICATION = 'pratilipiPc.wsgi.application'  # WSGI application entry point

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # Use MySQL as the database engine
        'NAME': 'pratilipipcdb',  # Database name
        'USER': config('DB_USER'),  # Database user from .env
        'PASSWORD': config('DB_PASSWORD'),  # Database password from .env
        'HOST': 'localhost',  # Database host
        'PORT': '3306',  # Default MySQL port
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",  # Set strict SQL mode
        },
    }
}

# Password validation settings
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

# Internationalization settings
LANGUAGE_CODE = 'en-us'  # Default language
TIME_ZONE = 'Asia/Kolkata'  # Set to Indian Standard Time
USE_I18N = True  # Enable internationalization
USE_TZ = True  # Enable time zone support

# Static and Media files configuration
STATIC_URL = 'static/'  # URL for static files
MEDIA_URL = '/media/'  # URL for media files
MEDIA_ROOT = BASE_DIR / 'media'  # Local directory for media files

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'  # Use BigAutoField for IDs

# REST Framework configuration
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
        'anon': '100/day',
        'user': '1000/day',
        'review': '50/day',  # Limit reviews per user
        'wishlist': '100/day',  # Limit wishlist actions
        'order': '50/day',  # Limit orders per user
        'submission': '10/day',  # Limit submissions per user
    },
    'UNAUTHENTICATED_USER': None,
    'UNAUTHENTICATED_TOKEN': None,
}

# Simple JWT configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,  # Enable blacklisting after token rotation
    'LEEWAY': 60,
}

# Logging configuration
'''LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'debug.log',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}'''
# print(BASE_DIR)  # Add this in settings.py temporarily

# AWS S3 Configuration (add in settings.py)
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = 'ap-south-1'  # Example region, adjust as needed
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = 'public-read'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Security settings (enable in production)
SECURE_SSL_REDIRECT = False  # Set to True in production with HTTPS
SESSION_COOKIE_SECURE = False  # Set to True in production
CSRF_COOKIE_SECURE = False  # Set to True in production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Razorpay credentials (keep secret)
# ...existing code...

RAZORPAY_KEY_ID = config("RAZORPAY_KEY_ID")        # Use config instead of env
RAZORPAY_KEY_SECRET = config("RAZORPAY_KEY_SECRET")

# ...existing code...

TIME_ZONE = 'Asia/Kolkata'  # Yeh IST ke liye sahi hai
USE_TZ = True


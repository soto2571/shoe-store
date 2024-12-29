"""
Django settings for choco_hypewear project.

Generated by 'django-admin startproject' using Django 5.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
from decouple import config
import os
    
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = config('SECRET_KEY')

# DEBUG setting from .env file
DEBUG = config('DEBUG', default=False, cast=bool)

# Stripe keys based on the DEBUG flag
if DEBUG:
    STRIPE_PUBLISHABLE_KEY = config('STRIPE_TEST_PUBLISHABLE_KEY')
    STRIPE_SECRET_KEY = config('STRIPE_TEST_SECRET_KEY')
else:
    STRIPE_PUBLISHABLE_KEY = config('STRIPE_LIVE_PUBLISHABLE_KEY')
    STRIPE_SECRET_KEY = config('STRIPE_LIVE_SECRET_KEY')

# Stripe webhook
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET')

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # Use SMTP backend
EMAIL_HOST = 'smtp.gmail.com'  # Gmail SMTP server
EMAIL_PORT = 587  # Port for TLS
EMAIL_USE_TLS = True  # Use TLS encryption
EMAIL_HOST_USER = config('EMAIL_HOST_USER')  # Load email user from environment
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')  # Load email password from environment
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER  # Default "from" email for outgoing emails

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['shoe-store-dqrq.onrender.com', '127.0.0.1', 'localhost']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'store',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

ROOT_URLCONF = 'choco_hypewear.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'choco_hypewear.wsgi.application'


SHIPPING_BOXES = [
    {"name": "Small Box", "max_weight": 6, "max_volume": 432, "price": 12.00},  # 6 lbs, 12x12x3
    {"name": "Medium Box", "max_weight": 12, "max_volume": 1728, "price": 20.00},  # 12 lbs, 12x12x12
    {"name": "Large Box", "max_weight": 20, "max_volume": 4096, "price": 30.00},  # 20 lbs, 16x16x16
    {"name": "Extra Large Box", "max_weight": 40, "max_volume": 8000, "price": 50.00},  # 40 lbs, 20x20x20
]


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases


import dj_database_url

DEBUG = config('DEBUG', default=False, cast=bool)

if DEBUG:
    # Local development database
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='myprojectdb'),
            'USER': config('DB_USER', default='soto2571'),
            'PASSWORD': config('DB_PASSWORD', default='123456789'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
else:
    # Production database (Render)
    DATABASES = {
        'default': dj_database_url.config(default=config('DATABASE_URL'))
    }


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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

LOGIN_REDIRECT_URL = '/owner-dashboard/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'debug.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'  # URL to access static files

STATICFILES_DIRS = [  # Directories where Django looks for static files
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'  # Destination for collectstatic
STATIC_VERSION = '1.0.8'  # Update this version whenever you modify your static files
TEMPLATES[0]['OPTIONS']['debug'] = True



MEDIA_URL = '/media/'
MEDIA_ROOT = '/var/www/media/'



# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

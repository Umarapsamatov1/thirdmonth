import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-studyflow-local-dev-key-change-for-production')
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
                  'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'core']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
              'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
              'django.contrib.auth.middleware.AuthenticationMiddleware',
              'django.contrib.messages.middleware.MessageMiddleware',
              'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [
    {'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
     'OPTIONS': {'context_processors': ['django.template.context_processors.debug',
                                        'django.template.context_processors.request',
                                        'django.contrib.auth.context_processors.auth',
                                        'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True
# Admin paneldagi Django tarjimasida yetishmagan o‘zbekcha matnlar
LOCALE_PATHS = [BASE_DIR / 'locale']
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'

# Configure SMTP through environment variables for real email delivery.
# Without SMTP credentials, development mail is printed to the terminal.
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
    else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "StudyFlow <noreply@studyflow.local>")
EMAIL_TIMEOUT = 15

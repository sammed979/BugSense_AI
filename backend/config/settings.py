"""
Django settings for BugSense AI project.
"""

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load the backend-local environment regardless of the process working directory.
load_dotenv(BASE_DIR / '.env')

# Add services and sandbox to Python path
import sys
sys.path.insert(0, str(BASE_DIR / 'services'))
sys.path.insert(0, str(BASE_DIR / 'sandbox'))

# Prevent Django from forcing trailing slash redirects (can interfere with CORS)
APPEND_SLASH = False


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
IS_RENDER = os.environ.get('RENDER', '').strip().lower() == 'true'
debug_setting = os.environ.get('DJANGO_DEBUG', os.environ.get('DEBUG', 'False'))
DEBUG = not IS_RENDER and debug_setting.strip().lower() in {'1', 'true', 'yes', 'on'}

# Allowed hosts - always include Render domain
default_hosts = ['localhost', '127.0.0.1', 'bugsense-ai-backend.onrender.com', 'bugsense-ai-mulk.onrender.com', '*.onrender.com']

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', ','.join(default_hosts)).split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',  # For production static file serving
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'apps.accounts.apps.AccountsConfig',
    'apps.dashboard.apps.DashboardConfig',
    'apps.projects.apps.ProjectsConfig',
    'apps.analysis.apps.AnalysisConfig',
    'apps.repair.apps.RepairConfig',
    'apps.execution.apps.ExecutionConfig',
    'apps.verification.apps.VerificationConfig',
    'apps.history.apps.HistoryConfig',
    'apps.learning.apps.LearningConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # For production static file serving
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'config.wsgi.application'


# Database: Render must use its PostgreSQL DATABASE_URL; SQLite is local-only.
database_url = os.environ.get('DATABASE_URL', '').strip()

if database_url:
    import dj_database_url

    database_config = dj_database_url.parse(
        database_url,
        conn_max_age=600,
        conn_health_checks=True,
    )
    if IS_RENDER and database_config['ENGINE'] != 'django.db.backends.postgresql':
        raise ImproperlyConfigured('Render deployments require DATABASE_URL to use PostgreSQL.')
    DATABASES = {'default': database_config}
elif IS_RENDER or not DEBUG:
    raise ImproperlyConfigured('DATABASE_URL is required outside local DEBUG mode.')
else:
    # SQLite is only the development fallback.
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
# Password validation
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
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,  # Disabled for simpler token refresh
    'BLACKLIST_AFTER_ROTATION': False,  # Disabled for simpler token refresh
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS Configuration
# Default includes common development origins and production Vercel frontend
default_origins = 'http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,https://bugsenseai-frontend.vercel.app'
cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS', default_origins)
# Ensure production Vercel origin is always present
if 'https://bugsenseai-frontend.vercel.app' not in cors_origins:
    cors_origins += ',https://bugsenseai-frontend.vercel.app'
# Add production frontend URL from env if available
production_frontend_url = os.environ.get('FRONTEND_URL', '')
if production_frontend_url and production_frontend_url not in cors_origins:
    cors_origins += f',{production_frontend_url}'
CORS_ALLOWED_ORIGINS = cors_origins.split(',')
CORS_ALLOW_CREDENTIALS = False  # JWT auth doesn't need credentials
# In DEBUG mode, allow all origins to support Vercel preview deployments
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False  # Always False for production security
CORS_ALLOW_HEADERS = [
    'content-type',
    'authorization',
    'x-csrftoken',
    'x-requested-with',
]
CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'OPTIONS',
    'PUT',
    'PATCH',
    'DELETE',
]
# CSRF Configuration (for session auth if used later)
CSRF_TRUSTED_ORIGINS = cors_origins.split(',')
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False

# AI Configuration (Google AI Studio Gemini)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', os.environ.get('GOOGLE_API_KEY', ''))
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
AI_PROVIDER = os.environ.get('AI_PROVIDER', 'gemini')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o')

# Execution Configuration
EXECUTION_ENABLED = os.environ.get('EXECUTION_ENABLED', 'False') == 'True'
EXECUTION_TIMEOUT_SECONDS = int(os.environ.get('EXECUTION_TIMEOUT_SECONDS', '5'))
EXECUTION_MEMORY_LIMIT_MB = int(os.environ.get('EXECUTION_MEMORY_LIMIT_MB', '128'))
EXECUTION_MAX_OUTPUT_BYTES = int(os.environ.get('EXECUTION_MAX_OUTPUT_BYTES', '65536'))
REPAIR_MAX_ATTEMPTS = int(os.environ.get('REPAIR_MAX_ATTEMPTS', '3'))

# Email Configuration (for password reset)
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@bugsense.local')

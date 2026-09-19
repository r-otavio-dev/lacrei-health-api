"""Settings for the Lacrei Saúde scheduling API.

The defaults are intentionally convenient for local development. Production
must opt in with DJANGO_ENV=production and provide all secrets explicitly.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return value
    return default


def env_list(*names: str, default: str = "") -> list[str]:
    return [item.strip() for item in first_env(*names, default=default).split(",") if item.strip()]


ENVIRONMENT = os.getenv("DJANGO_ENV", "development").lower()
DEBUG = env_bool("DJANGO_DEBUG", ENVIRONMENT != "production")
if ENVIRONMENT == "production" and DEBUG:
    raise ImproperlyConfigured("DJANGO_DEBUG must be false in production")

SECRET_KEY = first_env("DJANGO_SECRET_KEY", "SECRET_KEY")
if not SECRET_KEY:
    if ENVIRONMENT == "production":
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is required in production")
    SECRET_KEY = "local-development-only-secret-key-change-me"  # nosec B105
elif ENVIRONMENT == "production" and len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must contain at least 50 characters")

default_hosts = "" if ENVIRONMENT == "production" else "localhost,127.0.0.1,testserver"
ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "ALLOWED_HOSTS",
    default=default_hosts,
)
if ENVIRONMENT == "production" and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS is required in production")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "apps.scheduling",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.AccessLogMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# DATABASE_URL takes precedence. PostgreSQL component variables are the fallback.
# Tests can explicitly use DATABASE_URL=sqlite:///:memory: or DJANGO_USE_SQLITE=true.
database_url = os.getenv("DATABASE_URL", "").strip()
use_sqlite = env_bool("DJANGO_USE_SQLITE", False)
if ENVIRONMENT == "production" and use_sqlite:
    raise ImproperlyConfigured("DJANGO_USE_SQLITE cannot be enabled in production")
if database_url and not use_sqlite:
    parsed_database_url = urlparse(database_url)
    if parsed_database_url.scheme in {"postgres", "postgresql"}:
        database_options = {
            key: values[-1]
            for key, values in parse_qs(parsed_database_url.query).items()
            if key in {"sslmode", "sslrootcert", "sslcert", "sslkey"}
        }
        sslmode = os.getenv(
            "POSTGRES_SSLMODE",
            "require" if ENVIRONMENT == "production" else "",
        )
        if sslmode and "sslmode" not in database_options:
            database_options["sslmode"] = sslmode
        database_options["connect_timeout"] = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": unquote(parsed_database_url.path.lstrip("/")),
                "USER": unquote(parsed_database_url.username or ""),
                "PASSWORD": unquote(parsed_database_url.password or ""),
                "HOST": parsed_database_url.hostname or "localhost",
                "PORT": str(parsed_database_url.port or 5432),
                "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
                "CONN_HEALTH_CHECKS": True,
                "OPTIONS": database_options,
            }
        }
    elif parsed_database_url.scheme == "sqlite":
        if ENVIRONMENT == "production":
            raise ImproperlyConfigured("SQLite cannot be used in production")
        sqlite_name = unquote(parsed_database_url.path)
        if sqlite_name in {"/:memory:", ":memory:"}:
            sqlite_name = ":memory:"
        elif sqlite_name.startswith("/") and os.name == "nt" and len(sqlite_name) > 2:
            sqlite_name = sqlite_name[1:]
        DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": sqlite_name}}
    else:
        raise ImproperlyConfigured("DATABASE_URL must use postgresql://, postgres:// or sqlite://")
elif not use_sqlite and os.getenv("POSTGRES_DB"):
    postgres_options: dict[str, str | int] = {
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "5"))
    }
    sslmode = os.getenv(
        "POSTGRES_SSLMODE",
        "require" if ENVIRONMENT == "production" else "",
    )
    if sslmode:
        postgres_options["sslmode"] = sslmode
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": first_env("POSTGRES_HOST", "DB_HOST", default="db"),
            "PORT": first_env("POSTGRES_PORT", "DB_PORT", default="5432"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": postgres_options,
        }
    }
else:
    if ENVIRONMENT == "production" and not use_sqlite:
        raise ImproperlyConfigured("DATABASE_URL or POSTGRES_DB is required in production")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "America/Sao_Paulo")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
if ENVIRONMENT == "production":
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("API_MAX_BODY_BYTES", str(1024 * 1024)))
DATA_UPLOAD_MAX_NUMBER_FIELDS = int(os.getenv("API_MAX_FORM_FIELDS", "100"))

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": int(os.getenv("API_PAGE_SIZE", "20")),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("API_ANON_THROTTLE", "30/minute"),
        "user": os.getenv("API_USER_THROTTLE", "300/minute"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Lacrei Saúde - API de Consultas",
    "DESCRIPTION": "API segura para gerenciamento de profissionais e consultas médicas.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "COMPONENT_SPLIT_REQUEST": True,
}

CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS", "CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = env_bool("CORS_ALLOW_CREDENTIALS", False)
# Regex origins are useful for ephemeral staging frontends, but are opt-in.
CORS_ALLOWED_ORIGIN_REGEXES = env_list(
    "DJANGO_CORS_ALLOWED_ORIGIN_REGEXES", "CORS_ALLOWED_ORIGIN_REGEXES"
)

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "CSRF_TRUSTED_ORIGINS")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", ENVIRONMENT == "production")
SESSION_COOKIE_SECURE = ENVIRONMENT == "production"
CSRF_COOKIE_SECURE = ENVIRONMENT == "production"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = int(
    os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000" if ENVIRONMENT == "production" else "0")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = ENVIRONMENT == "production"
SECURE_HSTS_PRELOAD = ENVIRONMENT == "production"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "rename_fields": {"asctime": "timestamp", "levelname": "level"},
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if ENVIRONMENT == "production" else "standard",
        }
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "api.access": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

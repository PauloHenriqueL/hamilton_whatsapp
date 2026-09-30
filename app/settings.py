"""
Settings do Hamilton 2.0.

Versão enxuta portada de ../hamilton-api/app/settings.py: mantém o essencial
(Neon via DATABASE_URL, whitenoise, locale pt-BR, segurança HTTPS em produção) e
remove o que saiu de escopo no 2.0 (Stripe, Sofia, DRF/JWT, Autentique, e-mail).
"""
from pathlib import Path
import os
import sys
import locale
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# override=False: variáveis já presentes no ambiente (ex.: painel do Render) vencem.
load_dotenv(BASE_DIR / '.env', override=False)

SECRET_KEY = os.getenv('SECRET_KEY', '')
if not SECRET_KEY:
    if os.getenv('DJANGO_ALLOW_INSECURE_KEY') == '1' or sys.argv[1:2] in (['check'], ['test']):
        # Chave descartável só para `check`/`test` locais quando não há .env.
        SECRET_KEY = 'insecure-dev-key-nao-use-em-producao'
    else:
        raise ValueError(
            "SECRET_KEY não configurada! Adicione SECRET_KEY no seu .env. "
            "Gere uma com: python -c "
            "\"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
        )

DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [h.strip() for h in os.getenv(
    'ALLOWED_HOSTS', 'localhost,127.0.0.1'
).split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'principais',
    'conciliacao',
    'fiscal',
    'dashboard',
]

LOGIN_URL = 'login'
# Redirect pós-login é resolvido por papel na view de login (D4); este é o fallback.
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'principais.middleware.BloqueiaEscritaEmViewAsMiddleware',  # D11b
]

ROOT_URLCONF = 'app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'app' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'principais.context_processors.supervisao',  # D11b
                'principais.context_processors.notificacoes',  # D14b
            ],
        },
    },
]

WSGI_APPLICATION = 'app.wsgi.application'

# --- Banco ------------------------------------------------------------------
# DATABASE_URL aponta para o Neon do v2 (banco SEPARADO do Hamilton antigo).
# Sem DATABASE_URL, cai em SQLite local. A migração de dados (D6) lê o banco
# antigo por uma conexão própria, nunca por este 'default'.
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    _db = urlparse(DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _db.path.replace('/', ''),
            'USER': _db.username,
            'PASSWORD': _db.password,
            'HOST': _db.hostname,
            'PORT': _db.port or 5432,
            'OPTIONS': {'sslmode': 'require'},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# --- Banco LEGADO (migração de corte único — D6, decisão #20) ----------------
# Conexão de SOMENTE LEITURA ao banco de produção do Hamilton antigo, usada só
# pelo comando `migrar_hamilton`. Fica configurada apenas quando LEGADO_DATABASE_URL
# está no ambiente (no go-live); ausente, o comando avisa e não roda.
LEGADO_DATABASE_URL = os.getenv('LEGADO_DATABASE_URL')
if LEGADO_DATABASE_URL:
    _leg = urlparse(LEGADO_DATABASE_URL)
    DATABASES['legado'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _leg.path.replace('/', ''),
        'USER': _leg.username,
        'PASSWORD': _leg.password,
        'HOST': _leg.hostname,
        'PORT': _leg.port or 5432,
        'OPTIONS': {'sslmode': 'require'},
        'TIME_ZONE': TIME_ZONE,
    }

# A suíte nunca toca banco remoto: roda em SQLite in-memory.
RODANDO_TESTES = sys.argv[1:2] == ['test']
if RODANDO_TESTES:
    DATABASES = {
        'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'app', 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Formatação de datas/moeda em pt-BR.
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_TIME, '')

# ── SEGURANÇA HTTPS E COOKIES (só em produção, DEBUG=False) ──────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

X_FRAME_OPTIONS = 'DENY'

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()
]

# ── NOTA FISCAL (Webmania — usado a partir de D16) ───────────────────────────
WEBMANIA_API_TOKEN = os.getenv('WEBMANIA_API_TOKEN', '')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {module} {message}', 'style': '{'},
        'simple': {'format': '{levelname} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'principais': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}

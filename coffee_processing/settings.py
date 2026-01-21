"""
Django settings for coffee_processing project.
"""

from pathlib import Path
import environ
import os

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Take environment variables from .env file
environ.Env.read_env(os.path.join(Path(__file__).resolve().parent, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# Application definition
INSTALLED_APPS = [
    'jazzmin',  # Must be before django.contrib.admin
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'beneficio',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'coffee_processing.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Esta línea es importante
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
WSGI_APPLICATION = 'coffee_processing.wsgi.application'

# Database
# Database
DATABASES = {
    'default': env.db(default='sqlite:///db.sqlite3')
}

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
LANGUAGE_CODE = 'es-gt'
TIME_ZONE = 'America/Guatemala'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Asegura que las cookies de sesión y CSRF solo viajen por HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ========== JAZZMIN SETTINGS ==========
JAZZMIN_SETTINGS = {
    # Title on the login screen
    "site_title": "Beneficio El Gigante",

    # Title on the brand
    "site_header": "Beneficio El Gigante",

    # Logo to use for your site
    "site_brand": "El Gigante Admin",

    # Welcome text on the login screen
    "welcome_sign": "Bienvenido al Panel de Administración",

    # Copyright on the footer
    "copyright": "Beneficio El Gigante",

    # Show the sidebar
    "show_sidebar": True,

    # Show navigation expanded by default
    "navigation_expanded": True,

    # Hide models from navigation
    "hide_models": [],

    # Custom icons for models
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "beneficio.TipoCafe": "fas fa-coffee",
        "beneficio.Bodega": "fas fa-warehouse",
        "beneficio.Lote": "fas fa-boxes",
        "beneficio.Procesado": "fas fa-industry",
        "beneficio.Reproceso": "fas fa-recycle",
        "beneficio.Mezcla": "fas fa-blender",
        "beneficio.DetalleMezcla": "fas fa-stream",
        "beneficio.Catacion": "fas fa-clipboard-check",
        "beneficio.DefectoCatacion": "fas fa-exclamation-triangle",
        "beneficio.Comprador": "fas fa-handshake",
        "beneficio.Compra": "fas fa-shopping-cart",
        "beneficio.MantenimientoPlanta": "fas fa-tools",
        "beneficio.HistorialMantenimiento": "fas fa-history",
        "beneficio.ReciboCafe": "fas fa-receipt",
        "beneficio.Trabajador": "fas fa-hard-hat",
        "beneficio.PlanillaSemanal": "fas fa-calendar-week",
        "beneficio.RegistroDiario": "fas fa-clipboard-list",
    },

    # Default icon for models that don't have one
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    # Use rounded corners on all elements
    "use_google_fonts_cdn": True,

    # Show UI Customizer on the sidebar
    "show_ui_builder": False,

    # Color theme
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {"auth.user": "collapsible", "auth.group": "vertical_tabs"},
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-success",
    "accent": "accent-olive",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-success",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "flatly",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def parse_csv_setting(value):
    cleaned = value.strip().strip("[]")
    items = []

    for item in cleaned.split(","):
        item = item.strip().strip("\"'")

        if item:
            items.append(item)

    return items


SECRET_KEY = "dev-only-cloud-toolbox-secret-key"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

ROOT_URLCONF = "cloud_toolbox.urls"
WSGI_APPLICATION = "cloud_toolbox.wsgi.application"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "django.contrib.sessions",
    "django.contrib.messages",
    "portal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

AUTHENTICATION_BACKENDS = [
    "portal.authentication.InternalLdapBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "login"

LDAP_DOMAIN = os.environ.get("LDAP_DOMAIN", "INTERNAL")
LDAP_AUTHORIZED_GROUPS = [
    group.strip()
    for group in os.environ.get(
        "LDAP_AUTHORIZED_GROUPS",
        "cloud-toolbox-users,cloud-toolbox-admins",
    ).split(",")
    if group.strip()
]

OPENSTACK_REGIONS = parse_csv_setting(
    os.environ.get(
        "OPENSTACK_REGIONS",
        "us-east-1,us-west-2,eu-west-1,eu-central-1,ap-southeast-1",
    )
)

OPENSTACK_VERSIONS = parse_csv_setting(
    os.environ.get(
        "OPENSTACK_VERSIONS",
        os.environ.get("OPENSTACK_TARGETS", "v1,v2"),
    )
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

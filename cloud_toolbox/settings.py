import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def comma_separated_values(value):
    values = []

    for item in value.split(","):
        cleaned = item.strip()

        if cleaned:
            values.append(cleaned)

    return values


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
        "DIRS": [os.path.join(BASE_DIR, "templates")],
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
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

STATIC_URL = "static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
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

OPENSTACK_REGIONS = comma_separated_values(
    os.environ.get(
        "OPENSTACK_REGIONS",
        "us-east-1,us-west-2,eu-west-1,eu-central-1,ap-southeast-1",
    )
)

OPENSTACK_VERSIONS = comma_separated_values(
    os.environ.get(
        "OPENSTACK_VERSIONS",
        os.environ.get("OPENSTACK_TARGETS", "v1,v2"),
    )
)

OBJECT_STORAGE_RINGS = comma_separated_values(
    os.environ.get(
        "OBJECT_STORAGE_RINGS",
        (
            "OBJRNGPARMARTIG01,OBJRNGPARMARTIG02,OBJRNGPARMAR01,"
            "OBJRNGNORSEC01,OBJRNGNYCPCY01,OBJRNGSINLOW01"
        ),
    )
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

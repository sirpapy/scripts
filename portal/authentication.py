from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User

from portal.services.ldap_auth import ldap_auth


class InternalLdapBackend(BaseBackend):
    def authenticate(self, _request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        if not ldap_auth(
            settings.LDAP_DOMAIN,
            username,
            password,
            settings.LDAP_AUTHORIZED_GROUPS,
        ):
            return None

        user, created = User.objects.get_or_create(username=username)

        if created:
            user.set_unusable_password()
            user.save()

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

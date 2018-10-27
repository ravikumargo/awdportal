# Provides custom login authentication classes
#
# See the Django documentation at https://docs.djangoproject.com/en/1.6/topics/auth/customizing/

from django_auth_ldap.backend import LDAPBackend


class ATPLDAPBackend(LDAPBackend):
    """Backend class used to authenticate users via the GW LDAP provider"""

    def get_or_create_user(self, username, ldap_user):
        """
        This must return a (User, created) 2-tuple for the given LDAP user.
        username is the Django-friendly username of the user. ldap_user.dn is
        the user's DN and ldap_user.attrs contains all of their LDAP attributes.
        """
        model = self.get_user_model()
        username_field = getattr(model, 'USERNAME_FIELD', 'username')

        kwargs = {
            username_field + '__iexact': username,
        }

        try:
            user = model.objects.get(**kwargs)
        except model.DoesNotExist:
            raise ldap_user.AuthenticationFailed

        return (user, False)

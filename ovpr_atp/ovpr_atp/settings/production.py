"""Production settings and globals."""

from __future__ import absolute_import

from os import environ

from .base import *

# Normally you should not import ANYTHING from Django directly
# into your settings, but ImproperlyConfigured is an exception.
from django.core.exceptions import ImproperlyConfigured


def get_env_setting(setting):
    """ Get the environment setting or return exception """
    try:
        return environ[setting]
    except KeyError:
        error_msg = "Set the %s env variable" % setting
        raise ImproperlyConfigured(error_msg)

########## HOST CONFIGURATION
# See: https://docs.djangoproject.com/en/1.5/releases/1.5/#allowed-hosts-required-in-production
ALLOWED_HOSTS = ['localhost', 'ovpr.andrewtbaker.com', 'awdtstapp1.es.gwu.edu', 'awdprdapp1.es.gwu.edu', 'awards.research.gwu.edu']
########## END HOST CONFIGURATION

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = 'smtp.gwu.edu'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-password
EMAIL_HOST_PASSWORD = ''

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-user
EMAIL_HOST_USER = ''

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = '25'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = '[%s] ' % SITE_NAME
########## END EMAIL CONFIGURATION

########## DATABASE CONFIGURATION
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'ovpr_atp',
        'USER': 'ovpr_atp',
        'PASSWORD': get_env_setting('MYSQL_PASSWORD'),
        'HOST': '127.0.0.1',
    }
}
########## END DATABASE CONFIGURATION

########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
########## END CACHE CONFIGURATION

########## COOKIES
SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SECURE = True
##########

########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = get_env_setting('SECRET_KEY')
########## END SECRET CONFIGURATION

########## CAYUSE CONFIGURATION
CAYUSE_PASSWORD = get_env_setting('CAYUSE_PASSWORD')
########## END CAYUSE CONFIGURATION

########## EAS CONFIGURATION
EAS_URL = 'https://app.eas.gwu.edu/webservices/SOAProvider/plsql/gwu_gms_atp_pub/'
EAS_PASSWORD = get_env_setting('EAS_PASSWORD')
EAS_NONCE = get_env_setting('EAS_NONCE')
########## END EAS CONFIGURATION

########## LDAP CONFIGURATION
AUTH_LDAP_SERVER_URI = 'ldap://authad.gwu.edu'

AUTH_LDAP_BIND_DN = "CN=DIT-SVC-ATPP,OU=Service_Accounts,OU=Accounts,OU=DIT,OU=GWResources,DC=ead,DC=gwu,DC=edu"
AUTH_LDAP_BIND_PASSWORD = get_env_setting('LDAP_PASSWORD')

import ldap
from django_auth_ldap.config import LDAPSearch, LDAPSearchUnion

AUTH_LDAP_USER_SEARCH = LDAPSearchUnion(
    LDAPSearch("OU=Accounts,OU=GWUsers,DC=ead,DC=gwu,DC=edu", ldap.SCOPE_SUBTREE, "(cn=%(user)s)"),
    LDAPSearch("OU=Service_Accounts,OU=Accounts,OU=DIT,OU=GWResources,DC=ead,DC=gwu,DC=edu", ldap.SCOPE_SUBTREE, "(cn=%(user)s)"),
)

AUTH_LDAP_USER_ATTR_MAP = {"first_name": "givenName", "last_name": "sn", "email": "extensionAttribute1"}

AUTHENTICATION_BACKENDS = (
    'core.backends.ATPLDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
)
########## END LDAP CONFIGURATION

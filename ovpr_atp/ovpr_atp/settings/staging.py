from __future__ import absolute_import

from .production import *

########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
########## END DEBUG CONFIGURATION

########## EAS SETTINGS
EAS_URL = 'https://app.eas.gwu.edu/webservices/SOAProvider/plsql/gwu_gms_atp_pub/'
########## END EAS SETTINGS

########## COOKIES
SESSION_COOKIE_SECURE = False

CSRF_COOKIE_SECURE = False
##########

PHS_FUNDED_RECIPIENTS = ['atp@gwu.edu']
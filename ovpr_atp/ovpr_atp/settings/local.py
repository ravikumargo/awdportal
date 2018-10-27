"""Development settings and globals."""

from __future__ import absolute_import

from os import environ
from os.path import join, normpath

from .base import *


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
########## END DEBUG CONFIGURATION


########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########## END EMAIL CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'testing',
        'USER': 'root',
        'PASSWORD': 'toor',
        'HOST': 'localhost',
        'PORT': '3306',
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

########## TEMPLATE CONFIGURATION
TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
)

########## TOOLBAR CONFIGURATION
# See: http://django-debug-toolbar.readthedocs.org/en/latest/installation.html#explicit-setup
INSTALLED_APPS += (
    # 'debug_toolbar',
    'django_extensions',
)

# MIDDLEWARE_CLASSES += (
#     'debug_toolbar.middleware.DebugToolbarMiddleware',
# )
#
# DEBUG_TOOLBAR_PATCH_SETTINGS = False

# http://django-debug-toolbar.readthedocs.org/en/latest/installation.html
INTERNAL_IPS = ('127.0.0.1',)
########## END TOOLBAR CONFIGURATION

########## CAYUSE CONFIGURATION
CAYUSE_ENDPOINT = 'https://sds-or.cayuse424.com/561/gwu/reports/'
CAYUSE_PASSWORD = environ['CAYUSE_PASSWORD']
########## END CAYUSE CONFIGURATION

########## EAS CONFIGURATION
EAS_URL = 'https://tst.eas.gwu.edu/webservices/SOAProvider/plsql/gwu_gms_atp_pub/'
# EAS_URL = 'http://easupg.es.gwu.edu:8009/webservices/SOAProvider/plsql/gwu_gms_atp_pub/'
EAS_PASSWORD = environ['EAS_PASSWORD']
EAS_NONCE = environ['EAS_NONCE']
########## END EAS CONFIGURATION

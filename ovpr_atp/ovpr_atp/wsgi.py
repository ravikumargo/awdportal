"""
WSGI config for ovpr_atp project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os
from os.path import abspath, dirname
from sys import path

SITE_ROOT = dirname(dirname(abspath(__file__)))
path.append(SITE_ROOT)

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "jajaja.settings"
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ovpr_atp.settings.production")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.

os.environ['DJANGO_SETTINGS_MODULE'] = ''
os.environ['SECRET_KEY'] = ''
os.environ['MYSQL_PASSWORD'] = ''
os.environ['CAYUSE_PASSWORD'] = ''
os.environ['LDAP_PASSWORD'] = ''
os.environ['EAS_PASSWORD'] = ''
os.environ['EAS_NONCE'] = ''

from django.core.wsgi import get_wsgi_application
_application = get_wsgi_application()

def application(environ, start_response):
  # os.environ['DJANGO_SETTINGS_MODULE'] = environ.get('DJANGO_SETTINGS_MODULE')
  # os.environ['SECRET_KEY'] = environ.get('SECRET_KEY')
  # os.environ['MYSQL_PASSWORD'] = environ.get('MYSQL_PASSWORD')
  # os.environ['CAYUSE_PASSWORD'] = environ.get('CAYUSE_PASSWORD')
  # os.environ['LDAP_PASSWORD'] = environ.get('LDAP_PASSWORD')
  # os.environ['EAS_PASSWORD'] = environ.get('EAS_PASSWORD')
  # os.environ['EAS_NONCE'] = environ.get('EAS_NONCE')
  return _application(environ, start_response)

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

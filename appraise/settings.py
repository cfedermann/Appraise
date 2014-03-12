# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>
"""
from django import VERSION as DJANGO_VERSION

import os

# Try to load ROOT_PATH from local settings, otherwise use default.
try:
    from local_settings import ROOT_PATH, DEPLOYMENT_PREFIX, DEBUG

except ImportError:
    ROOT_PATH = os.getcwd()
    DEPLOYMENT_PREFIX = 'appraise'
    DEBUG = True

TEMPLATE_DEBUG = DEBUG

# Import local settings, this allows to set git binary and secret key.
try:
    from random import choice
    from local_settings import GIT_BINARY, SECRET_KEY

except ImportError:
    GIT_BINARY = 'git'
    SECRET_KEY = ''.join([chr(choice(range(128))) for _ in range(50)])

try:
    from subprocess import check_output
    commit_log = check_output([GIT_BINARY, 'log', '--pretty=oneline'])
    # pylint: disable-msg=E1103
    COMMIT_TAG = commit_log.split('\n')[0].split()[0]

# pylint: disable-msg=W0703
except Exception, e:
    COMMIT_TAG = None

FORCE_SCRIPT_NAME = ""

import logging
from logging.handlers import RotatingFileHandler

# Logging settings for this Django project.
LOG_PATH = ROOT_PATH
LOG_LEVEL = logging.DEBUG
LOG_FILENAME = os.path.join(LOG_PATH, 'appraise.log')
LOG_FORMAT = "[%(asctime)s] %(name)s::%(levelname)s %(message)s"
LOG_DATE = "%m/%d/%Y @ %H:%M:%S"
LOG_FORMATTER = logging.Formatter(LOG_FORMAT, LOG_DATE)

LOG_HANDLER = RotatingFileHandler(filename=LOG_FILENAME, mode="a",
  maxBytes=1024*1024, backupCount=5, encoding="utf-8")
LOG_HANDLER.setLevel(level=LOG_LEVEL)
LOG_HANDLER.setFormatter(LOG_FORMATTER)

LOGIN_URL = '/{0}login/'.format(DEPLOYMENT_PREFIX)
LOGIN_REDIRECT_URL = '/{0}'.format(DEPLOYMENT_PREFIX)
LOGOUT_URL = '/{0}logout/'.format(DEPLOYMENT_PREFIX)

ADMINS = (
  # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
  'default': {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': os.path.join(ROOT_PATH, 'development.db'),
  }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = '{0}/media/'.format(ROOT_PATH)

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/{0}media/'.format(DEPLOYMENT_PREFIX)

# For Django versions before 1.4, we additionally set ADMIN_MEDIA_PREFIX.
if DJANGO_VERSION[1] < 4:
    ADMIN_MEDIA_PREFIX = '/{0}files/admin/'.format(DEPLOYMENT_PREFIX)

# The absolute path to the directory where collectstatic will collect static
# files for deployment.
STATIC_ROOT = os.path.join(ROOT_PATH, '/static-files/')

# URL to use when referring to static files located in STATIC_ROOT.
STATIC_URL = '/{0}files/'.format(DEPLOYMENT_PREFIX)

STATICFILES_DIRS = (
  os.path.join(ROOT_PATH, 'static'),
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
  'django.template.loaders.filesystem.Loader',
  'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
  'django.middleware.common.CommonMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  'django.contrib.messages.middleware.MessageMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'appraise.urls'

TEMPLATE_DIRS = (
  # Put strings here, like "/home/html/django_templates".
  # Always use forward slashes, even on Windows.
  # Don't forget to use absolute paths, not relative paths.
  os.path.join(ROOT_PATH, 'templates'),
)

TEMPLATE_CONTEXT_PROCESSORS = (
  'django.core.context_processors.debug',
  'django.core.context_processors.i18n',
  'django.core.context_processors.media',
  'django.core.context_processors.static',
  'django.contrib.auth.context_processors.auth',
  'django.contrib.messages.context_processors.messages',
)

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

INSTALLED_APPS = (
  'django.contrib.auth',
  'django.contrib.contenttypes',
  'django.contrib.sessions',
  'django.contrib.sites',
  'django.contrib.staticfiles',
  'django.contrib.admin',
  'django.contrib.messages',

  'appraise.wmt14',
)

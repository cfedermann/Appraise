# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>
"""
import logging
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.auth.views import login as LOGIN, logout as LOGOUT
from django.contrib.auth.views import password_change as PASSWORD_CHANGE
from django.core.urlresolvers import reverse
from django.shortcuts import render
from appraise.settings import LOG_LEVEL, LOG_HANDLER, COMMIT_TAG

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('appraise.views')
LOGGER.addHandler(LOG_HANDLER)

def frontpage(request):
    """
    Renders the front page view.
    """
    LOGGER.info('Rendering frontpage view for user "{0}".'.format(
      request.user.username or "Anonymous"))
    
    # Compute admin URL for super users.
    admin_url = None
    if request.user.is_superuser:
        admin_url = reverse('admin:index')
    
    dictionary = {
      'commit_tag': COMMIT_TAG,
      'title': 'Appraise evaluation system',
      'installed_apps': ['wmt14'],
      'admin_url': admin_url,
    }
    
    return render(request, 'frontpage.html', dictionary)


def login(request, template_name):
    """
    Renders login view by connecting to django.contrib.auth.views.
    """
    LOGGER.info('Rendering login view for user "{0}".'.format(
      request.user.username or "Anonymous"))
    
    if request.user.username:
        dictionary = {
          'commit_tag': COMMIT_TAG,
          'message': 'You are already logged in as "{0}".'.format(
            request.user.username),
          'title': 'Appraise evaluation system',
          'installed_apps': ['wmt14'],
        }
        
        return render(request, 'frontpage.html', dictionary)
    
    extra_context = {'commit_tag': COMMIT_TAG, 'installed_apps': ['wmt14']}
    return LOGIN(request, template_name, extra_context=extra_context)


def logout(request, next_page):
    """
    Renders logout view by connecting to django.contrib.auth.views.
    """
    LOGGER.info('Logging out user "{0}", redirecting to "{1}".'.format(
      request.user.username or "Anonymous", next_page)) 
    
    return LOGOUT(request, next_page)


def password_change(request, template_name):
    """
    Renders password change view by connecting to django.contrib.auth.views.
    """
    LOGGER.info('Rendering password change view for user "{0}".'.format(
      request.user.username or "Anonymous"))
    
    if not request.user.username:
        dictionary = {
          'commit_tag': COMMIT_TAG,
          'message': 'You are not logged in and hence cannot change your password!',
          'title': 'Appraise evaluation system',
          'installed_apps': ['wmt14'],
        }
        
        return render(request, 'frontpage.html', dictionary)
    
    # Compute admin URL for super users.
    admin_url = None
    if request.user.is_superuser:
        admin_url = reverse('admin:index')
    
    post_change_redirect = reverse('appraise.wmt14.views.overview')
    extra_context = {
      'commit_tag': COMMIT_TAG,
      'installed_apps': ['wmt14'],
      'admin_url': admin_url,
    }
    return PASSWORD_CHANGE(request, template_name,
      post_change_redirect=post_change_redirect,
      password_change_form=AdminPasswordChangeForm, extra_context=extra_context)
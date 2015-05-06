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
from django.shortcuts import render, render_to_response
from appraise.settings import LOG_LEVEL, LOG_HANDLER, COMMIT_TAG

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('appraise.views')
LOGGER.addHandler(LOG_HANDLER)

# HTTP error handlers supporting COMMIT_TAG.
def _page_not_found(request, template_name='404.html'):  
    """Custom HTTP 404 handler that preserves URL_PREFIX."""  
    LOGGER.info('Rendering HTTP 404 view for user "{0}".'.format(
      request.user.username or "Anonymous"))

    context = {
      'commit_tag': COMMIT_TAG,
      'title': 'Appraise evaluation system',
      'installed_apps': ['wmt15'],
    }
    
    return render_to_response('404.html', context)

  
def _server_error(request, template_name='500.html'):  
    """Custom HTTP 500 handler that preserves URL_PREFIX."""  
    LOGGER.info('Rendering HTTP 500 view for user "{0}".'.format(
      request.user.username or "Anonymous"))

    context = {
      'commit_tag': COMMIT_TAG,
      'title': 'Appraise evaluation system',
      'installed_apps': ['wmt15'],
    }
    
    return render_to_response('500.html', context)


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
    
    context = {
      'commit_tag': COMMIT_TAG,
      'title': 'Appraise evaluation system',
      'installed_apps': ['wmt15'],
      'admin_url': admin_url,
    }
    
    return render(request, 'frontpage.html', context)


def login(request, template_name):
    """
    Renders login view by connecting to django.contrib.auth.views.
    """
    LOGGER.info('Rendering login view for user "{0}".'.format(
      request.user.username or "Anonymous"))
    
    if request.user.username:
        context = {
          'commit_tag': COMMIT_TAG,
          'message': 'You are already logged in as "{0}".'.format(
            request.user.username),
          'title': 'Appraise evaluation system',
          'installed_apps': ['wmt15'],
        }
        
        return render(request, 'frontpage.html', context)
    
    postedUsername = None
    if request.POST.has_key('username'): 
        postedUsername = request.POST['username']
    
    extra_context = {
      'commit_tag': COMMIT_TAG,
      'title': 'Appraise evaluation system',
      'installed_apps': ['wmt15'],
      'username': postedUsername,
    }
    
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
    
    context = {
      'commit_tag': COMMIT_TAG,
      'title': 'Appraise evaluation system',
      'installed_apps': ['wmt15'],
    }
    
    # Verify that user session is active.  Otherwise, redirect to front page.
    if not request.user.username:
        context.update({
          'message': 'You are not logged in and hence cannot change your password!',
        })
        return render(request, 'frontpage.html', context)
    
    # For increased security Verify that old password was correct.
    if request.method == 'POST':
        old_password = request.POST.get('old_password', None)
        if not request.user.check_password(old_password):
            context.update({
              'message': 'Authentication failed so your password has not been changed!',
            })
            return render(request, 'frontpage.html', context)
        
        password1 = request.POST.get('password1', None)
        password2 = request.POST.get('password2', None)
        if password1 != password2:
            context.update({
              'message': 'You provided two non-matching values for your new password so your password has not been changed!',
            })
            return render(request, 'frontpage.html', context)
        
    
    # Compute admin URL for super users.
    admin_url = None
    if request.user.is_superuser:
        admin_url = reverse('admin:index')
    
    post_change_redirect = reverse('appraise.wmt15.views.overview')
    context.update({
      'admin_url': admin_url,
    })
    return PASSWORD_CHANGE(request, template_name,
      post_change_redirect=post_change_redirect,
      password_change_form=AdminPasswordChangeForm, extra_context=context)

# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
"""
import logging
from django.contrib.auth.views import login as LOGIN, logout as LOGOUT
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
    
    dictionary = {
      'commit_tag': COMMIT_TAG,
      'title': 'Appraise evaluation system',
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
        }
        
        return render(request, 'frontpage.html', dictionary)
    
    extra_context = {'commit_tag': COMMIT_TAG}
    return LOGIN(request, template_name, extra_context=extra_context)


def logout(request, next_page):
    """
    Renders logout view by connecting to django.contrib.auth.views.
    """
    LOGGER.info('Logging out user "{0}", redirecting to "{1}".'.format(
      request.user.username or "Anonymous", next_page)) 
    
    return LOGOUT(request, next_page)
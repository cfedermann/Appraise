# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>
"""
# pylint: disable-msg=W0611
from django.conf.urls import patterns, include, handler404, handler500
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from appraise.settings import MEDIA_ROOT, DEBUG, DEPLOYMENT_PREFIX

admin.autodiscover()

# HTTP error handlers supporting COMMIT_TAG.
handler404 = 'appraise.views._page_not_found'
handler500 = 'appraise.views._server_error'

# Basis URL patterns for Appraise project.
urlpatterns = patterns('appraise.views',
  (r'^{0}$'.format(DEPLOYMENT_PREFIX), 'frontpage'),
  (r'^{0}login/$'.format(DEPLOYMENT_PREFIX), 'login', {'template_name': 'login.html'}),
  (r'^{0}logout/$'.format(DEPLOYMENT_PREFIX), 'logout', {'next_page': '/{0}'.format(DEPLOYMENT_PREFIX)}),
  (r'^{0}password/$'.format(DEPLOYMENT_PREFIX), 'password_change', {'template_name': 'password_change.html'}),
  (r'^{0}admin/'.format(DEPLOYMENT_PREFIX), include(admin.site.urls)),
)

# Patterns for "wmt16" app.
urlpatterns += patterns('appraise.wmt16.views',
  (r'^{0}wmt16/$'.format(DEPLOYMENT_PREFIX), 'overview'),
  (r'^{0}wmt16/(?P<hit_id>[a-f0-9]{{8}})/'.format(DEPLOYMENT_PREFIX), 'hit_handler'),
  (r'^{0}wmt16/mturk/'.format(DEPLOYMENT_PREFIX), 'mturk_handler'),
  (r'^{0}wmt16/status/$'.format(DEPLOYMENT_PREFIX), 'status'),
  (r'^{0}wmt16/update-status/(?P<key>(global_stats|language_pair_stats|group_stats|user_stats|clusters))?/?$'.format(DEPLOYMENT_PREFIX), 'update_status'),
  (r'^{0}wmt16/update-ranking/$'.format(DEPLOYMENT_PREFIX), 'update_ranking'),
  (r'^{0}wmt16/signup/$'.format(DEPLOYMENT_PREFIX), 'signup'),
  (r'^{0}wmt16/profile/$'.format(DEPLOYMENT_PREFIX), 'profile_update'),
  (r'^{0}wmt16/export-to-pairwise-csv/(?P<token>[^/]+)/(?P<project>[^/]+)/$'.format(DEPLOYMENT_PREFIX), 'export_to_pairwise_csv'),
  (r'^{0}wmt16/export-to-ranking-csv/(?P<token>[^/]+)/(?P<project>[^/]+)/$'.format(DEPLOYMENT_PREFIX), 'export_to_ranking_csv'),
  (r'^{0}wmt16/export-to-ranking-xml/(?P<token>[^/]+)/(?P<project>[^/]+)/$'.format(DEPLOYMENT_PREFIX), 'export_to_ranking_xml'),
)

if DEBUG:
    urlpatterns += staticfiles_urlpatterns()

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

# Basis URL patterns for Appraise project.
urlpatterns = patterns('appraise.views',
  (r'^{0}/$', 'frontpage'),
  (r'^{0}/login/$'.format(DEPLOYMENT_PREFIX), 'login', {'template_name': 'login.html'}),
  (r'^{0}/logout/$'.format(DEPLOYMENT_PREFIX), 'logout', {'next_page': '/{0}/'.format(DEPLOYMENT_PREFIX)}),
  (r'^{0}/admin/'.format(DEPLOYMENT_PREFIX), include(admin.site.urls)),
)

# Patterns for "evaluation" app.
#urlpatterns += patterns('appraise.evaluation.views',
#  (r'^{0}/evaluation/$'.format(DEPLOYMENT_PREFIX), 'overview'),
#  (r'^{0}/evaluation/(?P<task_id>[a-f0-9]{{32}})/'.format(DEPLOYMENT_PREFIX), 'task_handler'),
#  (r'^{0}/status/$'.format(DEPLOYMENT_PREFIX), 'status_view'),
#  (r'^{0}/status/(?P<task_id>[a-f0-9]{{32}})/'.format(DEPLOYMENT_PREFIX), 'status_view'),
#  (r'^{0}/export/(?P<task_id>[a-f0-9]{{32}})/'.format(DEPLOYMENT_PREFIX), 'export_task_results'),
#  (r'^{0}/agreement/(?P<task_id>[a-f0-9]{{32}})/'.format(DEPLOYMENT_PREFIX), 'export_agreement_data'),
#)

# Patterns for "WMT13" app.
#urlpatterns += patterns('appraise.wmt13.views',
#  (r'^{0}/wmt13/$'.format(DEPLOYMENT_PREFIX), 'overview'),
#  (r'^{0}/wmt13/(?P<hit_id>[a-f0-9]{{8}})/'.format(DEPLOYMENT_PREFIX), 'hit_handler'),
#  (r'^{0}/wmt13/mturk/'.format(DEPLOYMENT_PREFIX), 'mturk_handler'),
#  (r'^{0}/wmt13/status/$'.format(DEPLOYMENT_PREFIX), 'status'),
#  (r'^{0}/wmt13/update-status/$'.format(DEPLOYMENT_PREFIX), 'update_status'),
#  (r'^{0}/wmt13/update-ranking/$'.format(DEPLOYMENT_PREFIX), 'update_ranking'),
#)

# Patterns for "WMT14" app.
urlpatterns += patterns('appraise.wmt14.views',
  (r'^{0}/wmt14/$'.format(DEPLOYMENT_PREFIX), 'overview'),
  (r'^{0}/wmt14/(?P<hit_id>[a-f0-9]{{8}})/'.format(DEPLOYMENT_PREFIX), 'hit_handler'),
  (r'^{0}/wmt14/mturk/'.format(DEPLOYMENT_PREFIX), 'mturk_handler'),
  (r'^{0}/wmt14/status/$'.format(DEPLOYMENT_PREFIX), 'status'),
  (r'^{0}/wmt14/update-status/$'.format(DEPLOYMENT_PREFIX), 'update_status'),
  (r'^{0}/wmt14/update-ranking/$'.format(DEPLOYMENT_PREFIX), 'update_ranking'),
)

if DEBUG:
    urlpatterns += staticfiles_urlpatterns()

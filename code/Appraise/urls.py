"""Appraise URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, handler404, handler500, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from Dashboard import views as dashboard_views
from EvalView import views as evalview_views
from Appraise.settings import BASE_CONTEXT, DEBUG

# Base context for all views.
#BASE_CON3TEXT = {
#  'commit_tag': '#wmt17dev',
#  'title': 'Appraise evaluation system',
#  'static_url': STATIC_URL,
#}

# HTTP error handlers supporting COMMIT_TAG.
handler404 = 'Dashboard.views._page_not_found'
handler500 = 'Dashboard.views._server_error'

# pylint: disable=C0330
urlpatterns = [
    url(r'^admin/', admin.site.urls),

    url(r'^$', dashboard_views.frontpage, name='frontpage'),
    url(r'^dashboard/create-profile/$',
      dashboard_views.create_profile,
      name='create-profile'
    ),

    url(r'^dashboard/sign-in/$',
      auth_views.LoginView.as_view(
        template_name='Dashboard/signin.html',
        extra_context=BASE_CONTEXT
      ),
      name='sign-in'
    ),

    url(r'^dashboard/sign-out/$',
      auth_views.LogoutView.as_view(
        template_name='Dashboard/signout.html', # TODO: this does not exist!
        extra_context=BASE_CONTEXT
      ),
      name='sign-out'
    ),

    url(r'^dashboard/change-password/$',
      auth_views.PasswordChangeView.as_view(
        template_name='Dashboard/change-password.html',
        success_url='/dashboard/',
        extra_context=BASE_CONTEXT
      ),
      name='change-password'
    ),

    url(r'^dashboard/update-profile/$',
      dashboard_views.update_profile,
      name='update-profile'
    ),

    url(r'^dashboard/$', dashboard_views.dashboard, name='dashboard'),

    url(r'^group-status/$', dashboard_views.group_status, name='group-status'),
    url(r'^system-status/$', dashboard_views.system_status, name='system-status'),
    url(r'^multimodal-status/$', dashboard_views.multimodal_status, name='multimodal-status'),
    url(r'^multimodal-systems/$', dashboard_views.multimodal_systems, name='multimodal-systems'),
    url(r'^metrics-status/$', dashboard_views.metrics_status, name='metrics-status'),
    url(r'^fe17-status/$', dashboard_views.fe17_status, name='fe17-status'),

    url(r'^direct-assessment/$', evalview_views.direct_assessment, name='direct-assessment'),
    url(r'^direct-assessment/(?P<code>[a-z]{3})/$', evalview_views.direct_assessment, name='direct-assessment'),
    url(r'^direct-assessment/(?P<code>[a-z]{3})/(?P<campaign_name>[a-zA-Z0-9]+)/$', evalview_views.direct_assessment, name='direct-assessment'),

    url(r'^multimodal-assessment/$', evalview_views.multimodal_assessment, name='multimodal-assessment'),
    url(r'^multimodal-assessment/(?P<code>[a-z]{3})/$', evalview_views.multimodal_assessment, name='multimodal-assessment'),
    url(r'^multimodal-assessment/(?P<code>[a-z]{3})/(?P<campaign_name>[a-zA-Z0-9]+)/$', evalview_views.multimodal_assessment, name='multimodal-assessment'),
]

if DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

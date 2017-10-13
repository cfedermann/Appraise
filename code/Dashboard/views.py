# pylint: disable=C0330
import logging

from collections import defaultdict
from datetime import datetime
from hashlib import md5
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.auth.views import password_change
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, reverse, redirect, render_to_response

from Appraise.settings import LOG_LEVEL, LOG_HANDLER, STATIC_URL, BASE_CONTEXT
from EvalData.models import DirectAssessmentTask, DirectAssessmentResult
from EvalData.models import MultiModalAssessmentTask, MultiModalAssessmentResult
from EvalData.models import WorkAgenda, TaskAgenda
from .models import UserInviteToken, LANGUAGE_CODES_AND_NAMES


# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('Dashboard.views')
LOGGER.addHandler(LOG_HANDLER)


HITS_REQUIRED_BEFORE_ENGLISH_ALLOWED = 5

# HTTP error handlers supporting COMMIT_TAG.
def _page_not_found(request, template_name='404.html'):
    """Custom HTTP 404 handler that preserves URL_PREFIX."""
    LOGGER.info('Rendering HTTP 404 for user "{0}". Request.path={1}'.format(
      request.user.username or "Anonymous", request.path))

    return render_to_response('Dashboard/404.html', BASE_CONTEXT)


def _server_error(request, template_name='500.html'):
    """Custom HTTP 500 handler that preserves URL_PREFIX."""
    LOGGER.info('Rendering HTTP 500 for user "{0}". Request.path={1}'.format(
      request.user.username or "Anonymous", request.path))

    return render_to_response('Dashboard/500.html', BASE_CONTEXT)

def frontpage(request, extra_context=None):
    """
    Appraise front page.
    """
    LOGGER.info('Rendering frontpage view for user "{0}".'.format(
      request.user.username or "Anonymous"))

    context = {
      'active_page': 'frontpage'
    }
    context.update(BASE_CONTEXT)
    if extra_context:
        context.update(extra_context)

    return render(request, 'Dashboard/frontpage.html', context)

def create_profile(request):
    """
    Renders the create profile view.
    """
    errors = None
    username = None
    email = None
    token = None
    languages = []
    language_choices = [x for x in LANGUAGE_CODES_AND_NAMES.items()]
    language_choices.sort(key=lambda x: x[1])

    focus_input = 'id_username'

    if request.method == "POST":
        username = request.POST.get('username', None)
        email = request.POST.get('email', None)
        token = request.POST.get('token', None)
        languages = request.POST.getlist('languages', None)

        if username and email and token and languages:
            try:
                # Check if given invite token is still active.
                invite = UserInviteToken.objects.filter(token=token)
                if not invite.exists() or not invite[0].active:
                    raise ValueError('invalid_token')

                # We now have a valid invite token...
                invite = invite[0]

                # Check if desired username is already in use.
                current_user = User.objects.filter(username=username)
                if current_user.exists():
                    raise ValueError('invalid_username')

                # Compute set of evaluation languages for this user.
                eval_groups = []
                for code in languages:
                    language_group = Group.objects.filter(name=code)
                    if language_group.exists():
                        eval_groups.extend(language_group)

                # Create new user account and add to group.
                password = '{0}{1}'.format(
                  invite.group.name[:2].upper(),
                  md5(invite.group.name.encode('utf-8')).hexdigest()[:8]
                )
                user = User.objects.create_user(username, email, password)

                # Update group settings for the new user account.
                user.groups.add(invite.group)
                for eval_group in eval_groups:
                    user.groups.add(eval_group)

                user.save()

                # Disable invite token and attach to current user.
                invite.active = False
                invite.user = user
                invite.save()

                # Login user and redirect to dashboard page.
                user = authenticate(username=username, password=password)
                login(request, user)
                return redirect('dashboard')

            # For validation errors, invalidate the respective value.
            except ValueError as issue:
                if issue.args[0] == 'invalid_username':
                    username = None

                elif issue.args[0] == 'invalid_token':
                    token = None

                else:
                    username = None
                    email = None
                    token = None
                    languages = None

            # For any other exception, clean up and ask user to retry.
            except:
                from traceback import format_exc
                print(format_exc()) # TODO: need logger here!
                username = None
                email = None
                token = None
                languages = None

        # Detect which input should get focus for next page rendering.
        if not username:
            focus_input = 'id_username'
            errors = ['invalid_username']

        elif not email:
            focus_input = 'id_email'
            errors = ['invalid_email']

        elif not token:
            focus_input = 'id_token'
            errors = ['invalid_token']

        elif not languages:
            focus_input = 'id_languages'
            errors = ['invalid_languages']

    context = {
      'active_page': "OVERVIEW", # TODO: check
      'errors': errors,
      'focus_input': focus_input,
      'username': username,
      'email': email,
      'token': token,
      'languages': languages,
      'language_choices': language_choices,
      'title': 'Create profile',
    }
    context.update(BASE_CONTEXT)

    return render(request, 'Dashboard/create-profile.html', context)

@login_required
def update_profile(request):
    """
    Renders the profile update view.
    """
    errors = None
    languages = set()
    language_choices = [x for x in LANGUAGE_CODES_AND_NAMES.items()]
    language_choices.sort(key=lambda x: x[1])
    focus_input = 'id_projects'

    if request.method == "POST":
        languages = set(request.POST.getlist('languages', None))
        if languages:
            try:
                # Compute set of evaluation languages for this user.
                for code, _ in language_choices:
                    language_group = Group.objects.filter(name=code)
                    if language_group.exists():
                        language_group = language_group[0]
                        if code in languages:
                            language_group.user_set.add(request.user)
                        else:
                            language_group.user_set.remove(request.user)
                        language_group.save()

                # Redirect to dashboard.
                return redirect('dashboard')

            # For any other exception, clean up and ask user to retry.
            except:
                from traceback import format_exc
                print(format_exc())

                languages = set()

        # Detect which input should get focus for next page rendering.
        if not languages:
            focus_input = 'id_languages'
            errors = ['invalid_languages']

    # Determine user target languages
    for group in request.user.groups.all():
        if group.name.lower() in [x.lower() for x in LANGUAGE_CODES_AND_NAMES.keys()]:
            languages.add(group.name.lower())

    context = {
      'active_page': "OVERVIEW",
      'errors': errors,
      'focus_input': focus_input,
      'languages': languages,
      'language_choices': language_choices,
      'title': 'Update profile',
    }
    context.update(BASE_CONTEXT)

    return render(request, 'Dashboard/update-profile.html', context)

@login_required
def dashboard(request):
    """
    Appraise dashboard page.
    """
    t1 = datetime.now()

    context = {
      'active_page': 'dashboard'
    }
    context.update(BASE_CONTEXT)

    annotations = DirectAssessmentResult.get_completed_for_user(request.user)
    hits, total_hits = DirectAssessmentResult.get_hit_status_for_user(request.user)

    # If user still has an assigned task, only offer link to this task.
    current_task = DirectAssessmentTask.get_task_for_user(request.user)

    # Check if marketTargetLanguage for current_task matches user languages.
    if current_task:
        code = current_task.marketTargetLanguageCode()
        print(request.user.groups.all())
        if code not in request.user.groups.values_list('name', flat=True):
            LOGGER.info('Language {0} not in user languages for user {1}. ' \
              'Giving up task {2}'.format(code, request.user.username,
              current_task)
            )

            current_task.assignedTo.remove(request.user)
            current_task = None

    if not current_task:
        current_task = MultiModalAssessmentTask.get_task_for_user(request.user)

    # Check if marketTargetLanguage for current_task matches user languages.
    if current_task:
        code = current_task.marketTargetLanguageCode()
        print(request.user.groups.all())
        if code not in request.user.groups.values_list('name', flat=True):
            LOGGER.info('Language {0} not in user languages for user {1}. ' \
              'Giving up task {2}'.format(code, request.user.username,
              current_task)
            )

            current_task.assignedTo.remove(request.user)
            current_task = None

    t2 = datetime.now()

    # If there is no current task, check if user is done with work agenda.
    work_completed = False
    if not current_task:
        agendas = TaskAgenda.objects.filter(
          user=request.user
        )

        for agenda in agendas:
            LOGGER.info('Identified work agenda {0}'.format(agenda))
            for serialized_open_task in agenda._open_tasks.all():
                open_task = serialized_open_task.get_object_instance()
                if open_task.next_item_for_user(request.user) is not None:
                    current_task = open_task
                    campaign = agenda.campaign
                else:
                    agenda._completed_asks.add(serialized_open_task)
                    agenda._open_tasks.remove(serialized_open_task)
            agenda.save()

        if not current_task and agendas.count() > 0:
            LOGGER.info('Work agendas completed, no more tasks for user')
            work_completed = True

    # Otherwise, compute set of language codes eligible for next task.
    campaign_languages = {}
    multimodal_languages = {}
    languages = []
    if not current_task and not work_completed:
        for code in LANGUAGE_CODES_AND_NAMES:
            if request.user.groups.filter(name=code).exists():
                if not code in languages:
                    languages.append(code)

        if hits < HITS_REQUIRED_BEFORE_ENGLISH_ALLOWED:
            if len(languages) > 1 and 'eng' in languages:
                languages.remove('eng')

        # Remove any language for which no free task is available.
        from Campaign.models import Campaign
        for campaign in Campaign.objects.all():
            is_multi_modal_campaign = 'multimodal' in campaign.campaignName.lower()

            if is_multi_modal_campaign:
                multimodal_languages[campaign.campaignName] = []
                multimodal_languages[campaign.campaignName].extend(languages)

            else:
                campaign_languages[campaign.campaignName] = []
                campaign_languages[campaign.campaignName].extend(languages)

            for code in languages:
                next_task_available = None
                if not is_multi_modal_campaign:
                    next_task_available = DirectAssessmentTask.get_next_free_task_for_language(code, campaign, request.user)
                else:
                    next_task_available = MultiModalAssessmentTask.get_next_free_task_for_language(code, campaign, request.user)

                if not next_task_available:
                    if not is_multi_modal_campaign:
                        campaign_languages[campaign.campaignName].remove(code)
                    else:
                        multimodal_languages[campaign.campaignName].remove(code)

            print("campaign = {0} languages = {1}".format(
              campaign.campaignName, campaign_languages[campaign.campaignName] if not is_multi_modal_campaign else multimodal_languages[campaign.campaignName]
            ))

    t3 = datetime.now()

    duration = DirectAssessmentResult.get_time_for_user(request.user)
    days = duration.days
    hours = int((duration.total_seconds() - (days * 86400)) / 3600)
    minutes = int(((duration.total_seconds() - (days * 86400)) % 3600) / 60)
    seconds = int((duration.total_seconds() - (days * 86400)) % 60)

    t4 = datetime.now()

    all_languages = []
    for key, values in campaign_languages.items():
        for value in values:
            all_languages.append((value, LANGUAGE_CODES_AND_NAMES[value], key))

    print(str(all_languages).encode('utf-8'))

    mmt_languages = []
    for key, values in multimodal_languages.items():
        for value in values:
            mmt_languages.append((value, LANGUAGE_CODES_AND_NAMES[value], key))

    print(str(mmt_languages).encode('utf-8'))

    is_multi_modal_campaign = False
    if current_task:
        is_multi_modal_campaign = 'multimodal' in current_task.campaign.campaignName.lower()

    context.update({
      'annotations': annotations,
      'hits': hits,
      'total_hits': total_hits,
      'days': days,
      'hours': hours,
      'minutes': minutes,
      'seconds': seconds,
      'current_task': current_task,
      'current_type': 'direct' if not is_multi_modal_campaign else 'multimodal',
      'languages': all_languages,
      'multimodal': mmt_languages,
      'debug_times': (t2-t1, t3-t2, t4-t3, t4-t1),
      'template_debug': 'debug' in request.GET,
      'work_completed': work_completed,
    })

    return render(request, 'Dashboard/dashboard.html', context)


@login_required
def group_status(request):
    """
    Appraise group status page.
    """
    t1 = datetime.now()

    context = {
      'active_page': 'group-status'
    }
    context.update(BASE_CONTEXT)

    t2 = datetime.now()
    group_data = DirectAssessmentResult.compute_accurate_group_status()
    t3 = datetime.now()

    group_status = []
    for group in group_data:
        group_status.append((group, group_data[group][0], group_data[group][1]))

    sorted_status = sorted(group_status, key=lambda x: x[1], reverse=True)
    t4 = datetime.now()

    context.update({
      'group_status': list(sorted_status),
      'sum_completed': sum([x[1] for x in group_status]),
      'sum_total': sum([x[2] for x in group_status]),
      'debug_times': (t2-t1, t3-t2, t4-t3, t4-t1),
      'template_debug': 'debug' in request.GET,
    })

    return render(request, 'Dashboard/group-status.html', context)


@login_required
def multimodal_status(request):
    """
    Appraise group status page.
    """
    t1 = datetime.now()

    context = {
      'active_page': 'group-status'
    }
    context.update(BASE_CONTEXT)

    t2 = datetime.now()
    group_data = MultiModalAssessmentResult.compute_accurate_group_status()
    t3 = datetime.now()

    group_status = []
    for group in group_data:
        group_status.append((group, group_data[group][0], group_data[group][1]))

    sorted_status = sorted(group_status, key=lambda x: x[1], reverse=True)
    t4 = datetime.now()

    context.update({
      'group_status': list(sorted_status),
      'sum_completed': sum([x[1] for x in group_status]),
      'sum_total': sum([x[2] for x in group_status]),
      'debug_times': (t2-t1, t3-t2, t4-t3, t4-t1),
      'template_debug': 'debug' in request.GET,
    })

    return render(request, 'Dashboard/group-status.html', context)


@login_required
def system_status(request):
    """
    Appraise system status page.
    """
    t1 = datetime.now()

    context = {
      'active_page': 'system-status'
    }
    context.update(BASE_CONTEXT)

    t2 = datetime.now()
    system_data = DirectAssessmentResult.get_system_status(sort_index=1)
    t3 = datetime.now()
    sorted_status = []
    total_completed = 0
    for code in system_data:
        if not system_data[code]:
            continue

        for data in system_data[code]:
            sorted_status.append((code, data[0], data[1]))
            total_completed += data[1]

    t4 = datetime.now()
    context.update({
      'system_status': sorted_status,
      'total_completed': total_completed,
      'debug_times': (t2-t1, t3-t2, t4-t3, t4-t1),
      'template_debug': 'debug' in request.GET,
    })

    return render(request, 'Dashboard/system-status.html', context)


@login_required
def multimodal_systems(request):
    """
    Appraise system status page.
    """
    t1 = datetime.now()

    context = {
      'active_page': 'system-status'
    }
    context.update(BASE_CONTEXT)

    t2 = datetime.now()
    system_data = MultiModalAssessmentResult.get_system_status(sort_index=1)
    t3 = datetime.now()
    sorted_status = []
    total_completed = 0
    for code in system_data:
        if not system_data[code]:
            continue

        for data in system_data[code]:
            sorted_status.append((code, data[0], data[1]))
            total_completed += data[1]

    t4 = datetime.now()
    context.update({
      'system_status': sorted_status,
      'total_completed': total_completed,
      'debug_times': (t2-t1, t3-t2, t4-t3, t4-t1),
      'template_debug': 'debug' in request.GET,
    })

    return render(request, 'Dashboard/system-status.html', context)


@login_required
def metrics_status(request):
    """
    Appraise system status page.
    """
    t1 = datetime.now()

    context = {
      'active_page': 'system-status'
    }
    context.update(BASE_CONTEXT)

    t2 = datetime.now()
    task_data = DirectAssessmentTask.objects.filter(id__in=[x+5427 for x in range(48)])
    t3 = datetime.now()
    task_status = []
    for t in task_data.order_by('id'):
        source_language = t.items.first().metadata.market.sourceLanguageCode
        target_language = t.items.first().metadata.market.targetLanguageCode
        annotators = t.assignedTo.count()
        results = t.evaldata_directassessmentresult_task.count()
        task_status.append((
          t.id, source_language, target_language, annotators, round(100*annotators/15.0), results, round(100*results/(15*70.0))
        ))
    t4 = datetime.now()
    context.update({
      'task_status': task_status,
      'debug_times': (t2-t1, t3-t2, t4-t3, t4-t1),
      'template_debug': 'debug' in request.GET,
    })

    return render(request, 'Dashboard/metrics-status.html', context)


@login_required
def fe17_status(request):
    """
    Appraise system status page.
    """
    t1 = datetime.now()

    context = {
      'active_page': 'system-status'
    }
    context.update(BASE_CONTEXT)

    t2 = datetime.now()
    task_data = DirectAssessmentTask.objects.filter(id__gte=37)
    t3 = datetime.now()
    task_status = []
    for t in task_data.order_by('id'):
        source_language = t.items.first().metadata.market.sourceLanguageCode
        target_language = t.items.first().metadata.market.targetLanguageCode
        annotators = t.assignedTo.count()
        results = t.evaldata_directassessmentresult_task.count()
        task_status.append((
          t.id, source_language, target_language, annotators, round(100*annotators/4.0), results, round(100*results/(4*100.0))
        ))
    t4 = datetime.now()
    context.update({
      'task_status': task_status,
      'debug_times': (t2-t1, t3-t2, t4-t3, t4-t1),
      'template_debug': 'debug' in request.GET,
    })

    return render(request, 'Dashboard/metrics-status.html', context)

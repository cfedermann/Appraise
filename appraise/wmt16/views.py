# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>
"""
import logging

from datetime import datetime, timedelta
from hashlib import md5
from os.path import join
from random import seed, shuffle
from subprocess import check_output
from tempfile import gettempdir
from urllib import unquote

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from appraise.wmt16.models import LANGUAGE_PAIR_CHOICES, UserHITMapping, \
  HIT, RankingTask, RankingResult, UserHITMapping, UserInviteToken, Project, \
  GROUP_HIT_REQUIREMENTS, MAX_USERS_PER_HIT, initialize_database
from appraise.settings import LOG_LEVEL, LOG_HANDLER, COMMIT_TAG, ROOT_PATH, STATIC_URL
from appraise.utils import datetime_to_seconds, seconds_to_timedelta

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('appraise.wmt16.views')
LOGGER.addHandler(LOG_HANDLER)

# Base context for all views.
BASE_CONTEXT = {
  'commit_tag': COMMIT_TAG,
  'title': 'Appraise evaluation system',
  'installed_apps': ['wmt16'],
  'static_url': STATIC_URL,
}

# We keep status and ranking information available in memory to speed up
# access and avoid lengthy delays caused by computation of this data.
STATUS_CACHE = {}
RANKINGS_CACHE = {}

# Initalized database
initialize_database()


    
def _get_active_users_for_group(group_to_check):
    """
    Determine all users in the given group who have been active in the last 90 days.
    """
    ninetydaysago = datetime.now() - timedelta(days=90)
    active_users = []
    if group_to_check.exists():
        active_users = group_to_check[0].user_set.filter(last_login__gt=ninetydaysago)
    return active_users


def _compute_next_task_for_user(user, project, language_pair):
    """
    Computes the next task for the given user, project and language pair combination.

    This may either be the HIT the given user is currently working on or a
    new HIT in case the user has completed all previous HITs already.

    By convention, language_pair is a String in format xxx2yyy where both
    xxx and yyy are ISO-639-3 language codes.

    """
    # Check if project is valid for the given user.
    if not project in user.project_set.all():
        LOGGER.debug('User {0} does not work on project {1}.'.format(
          user, project
        ))
        return None
    
    # Check if language_pair is valid for the given user.
    if not user.groups.filter(name=language_pair):
        LOGGER.debug('User {0} does not know language pair {1}.'.format(
          user, language_pair))
        return None

    # Check if there exists a current HIT for the given user.
    current_hitmap = UserHITMapping.objects.filter(user=user,
      project=project, hit__language_pair=language_pair)

    # If there is no current HIT to continue with, find a random HIT for the
    # given user.  We keep generating a random block_id in [1, 1000] until we
    # find a matching HIT which the current user has not yet completed.
    if not current_hitmap:
        LOGGER.debug('No current HIT for user {0}, fetching HIT.'.format(
          user))
        
        # Compatible HIT instances need to match the given language pair!
        # Furthermore, they need to be active and not reserved for MTurk.
        hits = HIT.objects.filter(active=True, mturk_only=False,
          completed=False, project=project, language_pair=language_pair)
        
        LOGGER.debug("HITs = {0}".format(hits))
        
        # Compute list of compatible block ids and randomise its order.
        #
        # cfedermann: for WMT14 Matt did not provide block ids anymore.
        #   This meant that our shuffled list of block ids only contained
        #   [-1, ..., -1] entries;  using these to filter and check for
        #   respective HIT status is a quadratic increase of redundant work
        #   which will take prohibitively long when there is no next HIT.
        #
        #   Converting to unique HIT ids will speed up things drastically.
        hit_ids = list(set(hits.values_list('hit_id', flat=True)))
        shuffle(hit_ids)
        LOGGER.debug("HIT IDs = {0}".format(hit_ids))
        
        # Find the next HIT for the current user.
        random_hit = None
        for hit_id in hit_ids:
            for hit in hits.filter(hit_id=hit_id):
                hit_users = list(hit.users.all())
                
                # Check if this HIT is mapped to users.  This code prevents
                # that more than MAX_USERS_PER_HIT users complete a HIT.
                for hitmap in UserHITMapping.objects.filter(hit=hit):
                    if not hitmap.user in hit_users:
                        hit_users.append(hitmap.user)
                
                if not user in hit_users:
                    if len(hit_users) < MAX_USERS_PER_HIT:
                        random_hit = hit
                        break
            
            if random_hit:
                break
        
        # If we still haven't found a next HIT, there simply is none...
        if not random_hit:
            # TODO: We should now investigate if there is any HIT assigned
            #   to a user but has not been finished in a certain time span.
            #   Such a HIT can be freed and assigned to the current user.            
            return None
        
        # Update User/HIT mappings s.t. the system knows about the next HIT.
        current_hitmap = UserHITMapping.objects.create(user=user,
          project=project, hit=random_hit)
    
    # Otherwise, select first match from QuerySet.
    else:
        current_hitmap = current_hitmap[0]
        
        # Sanity check preventing stale User/HIT mappings to screw up things.
        #
        # Before we checked if `len(hit_users) >= 3`.
        hit_users = list(current_hitmap.hit.users.all())
        if user in hit_users or len(hit_users) >= 1 \
          or not current_hitmap.hit.active:
            LOGGER.debug('Detected stale User/HIT mapping {0}->{1}'.format(
              user, current_hitmap.hit))
            current_hitmap.delete()
            return _compute_next_task_for_user(user, project, language_pair)
    
    LOGGER.debug('User {0} currently working on HIT {1}'.format(user,
      current_hitmap.hit))
    
    return current_hitmap.hit


def _save_results(item, user, duration, raw_result):
    """
    Creates or updates the RankingResult for the given item and user.
    """
    LOGGER.debug('item: {}, user: {}, duration: {}, raw_result: {}'.format(
      item, user, duration, raw_result.encode('utf-8')))
    
    _existing_result = RankingResult.objects.filter(item=item, user=user)
    
    if _existing_result:
        _result = _existing_result[0]
    
    else:
        _result = RankingResult(item=item, user=user)
    
    LOGGER.debug(u'\n\nResults data for user "{0}":\n\n{1}\n'.format(
      user.username or "Anonymous",
      u'\n'.join([str(x) for x in [_result, duration, raw_result]])))
    
    _result.duration = str(duration)
    _result.raw_result = raw_result
    
    _result.save()


def _find_next_item_to_process(items, user, random_order=False):
    """
    Computes the next item the current user should process or None, if done.
    """
    user_results = RankingResult.objects.filter(user=user)
    
    processed_items = user_results.values_list('item__pk', flat=True)
    
    # cfedermann: this might be sub optimal wrt. performance!
    unprocessed_items = list(items.exclude(pk__in=processed_items))

    if random_order:
        shuffle(unprocessed_items)
    
    if unprocessed_items:
        return unprocessed_items[0]
    
    return None


def _compute_context_for_item(item):
    """
    Computes the source and reference texts for item, including context.
    
    Left/right context is only displayed if it belongs to the same document,
    hence we check the doc-id attribute before adding context.
    
    """
    source_text = [None, None, None]
    reference_text = [None, None, None]
    
    left_context = RankingTask.objects.filter(hit=item.hit, pk=item.id-1)
    right_context = RankingTask.objects.filter(hit=item.hit, pk=item.id+1)
    
    _item_doc_id = getattr(item.attributes, 'doc-id', None)
    
    # Item text and, if available, reference text are always set.
    source_text[1] = item.source[0]
    if item.reference:
        reference_text[1] = item.reference[0]
    
    # Only display context if left/right doc-ids match current item's doc-id.
    if left_context:
        _left = left_context[0]
        _left_doc_id = getattr(_left.attributes, 'doc-id', None)
        
        if _left_doc_id == _item_doc_id:
            source_text[0] = _left.source[0]
            if _left.reference:
                reference_text[0] = _left.reference[0]
    
    if right_context:
        _right = right_context[0]
        _right_doc_id = getattr(_right.attributes, 'doc-id', None)
        
        if _right_doc_id == _item_doc_id:
            source_text[2] = _right.source[0]
            if _right.reference:
                reference_text[2] = _right.reference[0]
    
    return (source_text, reference_text)


@login_required
def _handle_ranking(request, task, items):
    """
    Handler for Ranking tasks.
    
    Finds the next item belonging to the given task, renders the page template
    and creates an RankingResult instance on HTTP POST submission.
    
    """
    form_valid = False
    
    # If the request has been submitted via HTTP POST, extract data from it.
    if request.method == "POST":
        item_id = request.POST.get('item_id', None)
        end_timestamp = request.POST.get('end_timestamp', None)
        order_random = request.POST.get('order', None)
        start_timestamp = request.POST.get('start_timestamp', None)
        submit_button = request.POST.get('submit_button', None)
        
        # The form is only valid if all variables could be found.
        form_valid = all((item_id, end_timestamp, order_random,
          start_timestamp, submit_button))
    
    # If the form is valid, we have to save the results to the database.
    if form_valid:
        # Retrieve EvalutionItem instance for the given id or raise Http404.
        current_item = get_object_or_404(RankingTask, pk=int(item_id))
        
        # Compute duration for this item.
        start_datetime = datetime.fromtimestamp(float(start_timestamp))
        end_datetime = datetime.fromtimestamp(float(end_timestamp))
        duration = end_datetime - start_datetime
        
        # Initialise order from order_random.
        order = [int(x) for x in order_random.split(',')]
        
        # Compute ranks for translation alternatives using order.
        ranks = {}
        for index in range(len(current_item.translations)):
            rank = request.POST.get('rank_{0}'.format(index), -1)
            ranks[order[index]] = int(rank)
        
        # If "Flag Error" was clicked, _raw_result is set to "SKIPPED".
        if submit_button == 'FLAG_ERROR':
            _raw_result = 'SKIPPED'
        
        # Otherwise, the _raw_result is a comma-separated list of ranks.
        elif submit_button == 'SUBMIT':
            _raw_result = range(len(current_item.translations))
            _raw_result = ','.join([str(ranks[x]) for x in _raw_result])
        
        _results_data = [current_item, type(current_item), request.user,
          type(request.user), duration, type(duration), _raw_result,
          type(_raw_result)]
        LOGGER.debug(u'\n\nResults data for user "{0}":\n\n{1}\n'.format(
          request.user.username or "Anonymous",
          u'\n'.join([str(x) for x in _results_data])))
        
        # Save results for this item to the Django database.
        _save_results(current_item, request.user, duration, _raw_result)
    
    # Find next item the current user should process or return to overview.
    item = _find_next_item_to_process(items, request.user, False)
    if not item:
        return redirect('appraise.wmt16.views.overview')

    # Compute source and reference texts including context where possible.
    source_text, reference_text = _compute_context_for_item(item)
    
    # Retrieve the number of finished items for this user and task. We
    # increase finished_items by one as we are processing the first
    # unfinished item.
    finished_items = 1 + RankingResult.objects.filter(user=request.user,
      item__hit=item.hit).count()
    
    # Create list of translation alternatives in randomised order.
    translations = []
    order = range(len(item.translations))
    shuffle(order)
    for index in order:
        translations.append(item.translations[index])
    
    dictionary = {
      'action_url': request.path,
      'item_id': item.id,
      'sentence_id': item.source[1]['id'],
      'language_pair': item.hit.get_language_pair_display(),
      'order': ','.join([str(x) for x in order]),
      'reference_text': reference_text,
      'source_text': source_text,
      'task_progress': '{0}/3'.format(finished_items),
      'title': 'Ranking',
      'translations': translations,
    }
    dictionary.update(BASE_CONTEXT)
    
    return render(request, 'wmt16/ranking.html', dictionary)


@login_required
def hit_handler(request, hit_id):
    """
    General task handler.
    
    Finds the task with the given hit_id and redirects to its task handler.
    
    """
    LOGGER.info('Rendering task handler view for user "{0}".'.format(
      request.user.username or "Anonymous"))
    
    hit = get_object_or_404(HIT, hit_id=hit_id)
    if not hit.active:
        LOGGER.debug('Detected inactive User/HIT mapping {0}->{1}'.format(
          request.user, hit))
        new_hit = _compute_next_task_for_user(request.user, hit.project, hit.language_pair)
        if new_hit:
            return redirect('appraise.wmt16.views.hit_handler',
              hit_id=new_hit.hit_id)
        
        else:
            return redirect('appraise.wmt16.views.overview')
    
    items = RankingTask.objects.filter(hit=hit)
    if not items:
        return redirect('appraise.wmt16.views.overview')
    
    return _handle_ranking(request, hit, items)


# pylint: disable-msg=C0103
def mturk_handler(request):
    """
    MTurk-enabled task handler.
    """
    LOGGER.info('Rendering MTurk task handler view.')
    
    try:
        mturk_appraise_id = request.GET.get('appraise_id', None)
        hit = HIT.objects.get(hit_id=mturk_appraise_id)
        items = RankingTask.objects.filter(hit=hit)
        assert(len(items) == 3)
    
    except (AssertionError, ObjectDoesNotExist, MultipleObjectsReturned), msg:
        LOGGER.debug(msg)
        return HttpResponseForbidden("MTurk access forbidden")
    
    mturk_hitId = request.GET.get('hitId', None)
    mturk_assignmentId = request.GET.get('assignmentId', None)
    mturk_workerId = request.GET.get('workerId', None)
    
    srclang = hit.hit_attributes['source-language']
    trglang = hit.hit_attributes['target-language']
    
    # Bind items to item variables.
    item_1 = items[0]
    item_2 = items[1]
    item_3 = items[2]
    
    # Compute source and reference texts without context.  MTurk HITs contain
    # control sentences which, by definition, are out-of-context.  Hence, we
    # cannot show context without exposing the control's identity...
    source_text_1 = item_1.source[0]
    srcIndex_1 = item_1.source[1]['id']
    reference_text_1 = None
    if item_1.reference:
        reference_text_1 = item_1.reference[0]
    
    source_text_2 = item_2.source[0]
    srcIndex_2 = item_2.source[1]['id']
    reference_text_2 = None
    if item_2.reference:
        reference_text_2 = item_2.reference[0]
    
    source_text_3 = item_3.source[0]
    srcIndex_3 = item_3.source[1]['id']
    reference_text_3 = None
    if item_3.reference:
        reference_text_3 = item_3.reference[0]
    
    # Create list of translation alternatives in randomised order.
    translations_1 = []
    order_1 = range(len(item_1.translations))
    shuffle(order_1)
    for index in order_1:
        translations_1.append(item_1.translations[index])
    
    translations_2 = []
    order_2 = range(len(item_2.translations))
    shuffle(order_2)
    for index in order_2:
        translations_2.append(item_2.translations[index])
    
    translations_3 = []
    order_3 = range(len(item_3.translations))
    shuffle(order_3)
    for index in order_3:
        translations_3.append(item_3.translations[index])
    
    # System ids can be retrieved from HIT or segment level.
    if 'systems' in hit.hit_attributes.keys():
        systems_1 = hit.hit_attributes['systems']
        systems_2 = systems_1
        systems_3 = systems_1
    
    else:
        systems_1 = []
        for translation in item_1.translations:
            systems_1.append(translation[1]['system'])
        systems_1 = ','.join(systems_1)
        
        systems_2 = []
        for translation in item_2.translations:
            systems_2.append(translation[1]['system'])
        systems_2 = ','.join(systems_2)
        
        systems_3 = []
        for translation in item_3.translations:
            systems_3.append(translation[1]['system'])
        systems_3 = ','.join(systems_3)
    
    # Check referrer to determine action_url value.
    action_url = 'http://www.mturk.com/mturk/externalSubmit'
    if request.GET.has_key('turkSubmitTo'):
        action_url = unquote(request.GET.get('turkSubmitTo'))
        if not action_url.endswith('/mturk/externalSubmit'):
            action_url = action_url + '/mturk/externalSubmit'
    
    dictionary = {
      'action_url': action_url,
      'appraise_id': mturk_appraise_id,
      'hit_id': mturk_hitId,
      'assignment_id': mturk_assignmentId,
      'worker_id': mturk_workerId,
      'block_id': hit.block_id,
      'language_pair': hit.get_language_pair_display(),
      'order_1': ','.join([str(x) for x in order_1]),
      'order_2': ','.join([str(x) for x in order_2]),
      'order_3': ','.join([str(x) for x in order_3]),
      'systems_1': systems_1,
      'systems_2': systems_2,
      'systems_3': systems_3,
      'reference_text_1': reference_text_1,
      'reference_text_2': reference_text_2,
      'reference_text_3': reference_text_3,
      'source_text_1': source_text_1,
      'source_text_2': source_text_2,
      'source_text_3': source_text_3,
      'title': 'Ranking',
      'translations_1': translations_1,
      'translations_2': translations_2,
      'translations_3': translations_3,
      'srclang': srclang,
      'trglang': trglang,
      'srcIndex_1': srcIndex_1,
      'srcIndex_2': srcIndex_2,
      'srcIndex_3': srcIndex_3,
    }
    dictionary.update(BASE_CONTEXT)
    
    LOGGER.debug(u'\n\nMTurk data for HIT "{0}":\n\n{1}\n'.format(
      hit.hit_id,
      u'\n'.join([u'{0}\t->\t{1}'.format(*x) for x in dictionary.items()])))
    
    LOGGER.debug(u'\n\nMETA request data:\n\n{0}\n'.format(
      u'\n'.join([u'{0}: {1}'.format(*x) for x in request.META.items()])))
    
    return render(request, 'wmt16/mturk_ranking.html', dictionary)


@login_required
def overview(request):
    """
    Renders the evaluation tasks overview.
    """
    LOGGER.info('Rendering WMT16 HIT overview for user "{0}".'.format(
      request.user.username or "Anonymous"))
    
    # Re-initialise random number generator.
    seed(None)
    
    # Collect available language pairs for the current user.
    language_codes = set([x[0] for x in LANGUAGE_PAIR_CHOICES])
    language_pairs = request.user.groups.filter(name__in=language_codes)
    
    # Collect available annotation projects for the current user.
    annotation_projects = request.user.project_set.all()
    
    hit_data = []
    total = [0, 0, 0]

    for language_pair in language_pairs:
        for annotation_project in annotation_projects:
            hit = _compute_next_task_for_user(request.user, annotation_project, language_pair)
            user_status = HIT.compute_status_for_user(request.user, annotation_project, language_pair)
            for i in range(3):
                total[i] = total[i] + user_status[i]
        
            if hit:
                # Convert status seconds back into datetime.time instances.
                for i in range(2):
                    user_status[i+1] = seconds_to_timedelta(int(user_status[i+1]))
            
                hit_data.append(
                  (hit.get_language_pair_display(), hit.get_absolute_url(),
                   hit.hit_id, user_status, annotation_project)
                )
    
    # Convert total seconds back into datetime.timedelta instances.
    total[1] = seconds_to_timedelta(int(total[2]) / float(int(total[0]) or 1))
    
    # Remove microseconds to get a nicer timedelta rendering in templates.
    total[1] = total[1] - timedelta(microseconds=total[1].microseconds)
    
    total[2] = seconds_to_timedelta(int(total[2]))
    
    group = None
    for _group in request.user.groups.all():
        if _group.name == 'WMT16' \
          or _group.name.startswith('eng2') \
          or _group.name.endswith('2eng'):
            continue
        
        group = _group
        break
    
    if group is not None:
        group_name = group.name
        group_status = HIT.compute_status_for_group(group)
        for i in range(2):
            group_status[i+1] = seconds_to_timedelta(int(group_status[i+1]))
    
    else:
        group_status = None
        group_name = None
    
    LOGGER.debug(u'\n\nHIT data for user "{0}":\n\n{1}\n'.format(
      request.user.username or "Anonymous",
      u'\n'.join([u'{0}\t{1}\t{2}\t{3}'.format(*x) for x in hit_data])))

    # Compute admin URL for super users.
    admin_url = None
    if request.user.is_superuser:
        admin_url = reverse('admin:index')
    
    dictionary = {
      'active_page': "OVERVIEW",
      'hit_data': hit_data,
      'total': total,
      'group_name': group_name,
      'group_status': group_status,
      'admin_url': admin_url,
      'title': 'WMT16 Dashboard',
    }
    dictionary.update(BASE_CONTEXT)
    
    LOGGER.info(dictionary.values())
    
    return render(request, 'wmt16/overview.html', dictionary)


@login_required
def status(request):
    """
    Renders the status overview.
    """
    LOGGER.info('Rendering WMT16 HIT status for user "{0}".'.format(
      request.user.username or "Anonymous"))
    
    if not STATUS_CACHE.has_key('global_stats'):
        update_status(key='global_stats')
    
    if not STATUS_CACHE.has_key('language_pair_stats'):
        update_status(key='language_pair_stats')
    
    if not STATUS_CACHE.has_key('group_stats'):
        update_status(key='group_stats')
    
    if not STATUS_CACHE.has_key('user_stats'):
        update_status(key='user_stats')
    
    # Compute admin URL for super users.
    admin_url = None
    if request.user.is_superuser:
        admin_url = reverse('admin:index')
    
    dictionary = {
      'active_page': "STATUS",
      'global_stats': STATUS_CACHE['global_stats'],
      'language_pair_stats': STATUS_CACHE['language_pair_stats'],
      'group_stats': STATUS_CACHE['group_stats'],
      'user_stats': STATUS_CACHE['user_stats'],
      'clusters': RANKINGS_CACHE.get('clusters', []),
      'title': 'WMT16 Status',
      'admin_url': admin_url,
    }
    dictionary.update(BASE_CONTEXT)
    
    return render(request, 'wmt16/status.html', dictionary)


def update_ranking(request=None):
    """
    Updates the in-memory RANKINGS_CACHE dictionary.
    
    In order to get things up and running quickly, for WMT16 we will fall back
    to calling an external Perl script provided by Philipp Koehn;  after the
    evaluation has ended, we will re-work this into a fully integrated, Python
    based solution...
    
    """
    if request is not None:
        RANKINGS_CACHE['clusters'] = _compute_ranking_clusters(load_file=True)
        return HttpResponse('Ranking updated successfully')
    
    else:
        RANKINGS_CACHE['clusters'] = _compute_ranking_clusters()


def update_status(request=None, key=None):
    """
    Updates the in-memory STATUS_CACHE dictionary.
    """
    status_keys = ('global_stats', 'language_pair_stats', 'group_stats',
      'user_stats', 'clusters')
    
    # If a key is given, we only update the requested sub status.
    if key:
        status_keys = (key,)
    
    for status_key in status_keys:
        if status_key == 'global_stats':
            STATUS_CACHE[status_key] = _compute_global_stats()
        
        elif status_key == 'language_pair_stats':
            STATUS_CACHE[status_key] = _compute_language_pair_stats()
        
        elif status_key == 'group_stats':
            STATUS_CACHE[status_key] = _compute_group_stats()
        
        elif status_key == 'user_stats':
            # Only show top 25 contributors.
            user_stats = _compute_user_stats()
            STATUS_CACHE[status_key] = user_stats[:25]
    
    if request is not None:
        return HttpResponse('Status updated successfully')


def _compute_global_stats():
    """
    Computes some global statistics for the WMT16 evaluation campaign.
    """
    global_stats = []
    
    wmt16_group = Group.objects.filter(name='WMT16')
    wmt16_users = _get_active_users_for_group(wmt16_group)
      
    # Check how many HITs have been completed.  We now consider a HIT to be
    # completed once it has been annotated by one or more annotators.
    #
    # Before we required `hit.users.count() >= 3` for greater overlap.
    hits_completed = HIT.objects.filter(mturk_only=False, completed=True).count()
    
    # Check any remaining active HITs which are not yet marked complete.
    for hit in HIT.objects.filter(active=True, mturk_only=False, completed=False):
        if hit.users.count() >= 1:
            hits_completed = hits_completed + 1
            hit.completed = True
            hit.save()
    
    # Compute remaining HITs for all language pairs.
    hits_remaining = HIT.compute_remaining_hits()
    
    # Compute number of results contributed so far.
    ranking_results = RankingResult.objects.filter(
      item__hit__completed=True, item__hit__mturk_only=False)
    
    from math import factorial
    system_comparisons = 0
    for result in ranking_results:
        result.reload_dynamic_fields()
        combinations = factorial(result.systems)/(factorial(result.systems-2) * 2) if result.systems > 2 else 0
        system_comparisons = system_comparisons + combinations
    
    # Aggregate information about participating groups.
    groups = set()
    for user in wmt16_users:
        for group in user.groups.all():
            if group.name == 'WMT16' or group.name.startswith('eng2') \
              or group.name.endswith('2eng'):
                continue
            
            groups.add(group)
    
    # Compute average/total duration over all results.
    durations = RankingResult.objects.all().values_list('duration', flat=True)
    total_time = sum([datetime_to_seconds(x) for x in durations])
    avg_time = total_time / float(hits_completed or 1)
    avg_user_time = total_time / float(3 * hits_completed or 1)
    
    global_stats.append(('Users', len(wmt16_users)))
    global_stats.append(('Groups', len(groups)))
    global_stats.append(('HITs completed', '{0:,}'.format(hits_completed)))
    global_stats.append(('HITs remaining', '{0:,}'.format(hits_remaining)))
    global_stats.append(('Ranking results', '{0:,}'.format(ranking_results.count())))
    global_stats.append(('System comparisons', '{0:,}'.format(system_comparisons)))
    global_stats.append(('Average duration (per HIT)', seconds_to_timedelta(avg_time)))
    global_stats.append(('Average duration (per task)', seconds_to_timedelta(avg_user_time)))
    global_stats.append(('Total duration', seconds_to_timedelta(total_time)))
    
    return global_stats


def _compute_language_pair_stats():
    """
    Computes HIT statistics per language pair.
    """
    language_pair_stats = []
    
    # TODO: move LANGUAGE_PAIR_CHOICES better place.
    #
    # Running compute_remaining_hits() will also update completion status for HITs.
    for choice in LANGUAGE_PAIR_CHOICES:
        _code = choice[0]
        _name = choice[1]
        _remaining_hits = HIT.compute_remaining_hits(language_pair=_code)
        _completed_hits = HIT.objects.filter(completed=True, mturk_only=False,
          language_pair=_code)
        
        _unique_systems_for_language_pair = set()
        for _hit in _completed_hits:
            for _result in RankingResult.objects.filter(item__hit=_hit):
                for _translation in _result.item.translations:
                    for _system in set(_translation[1]['system'].split(',')):
                         _unique_systems_for_language_pair.add(_system)
        
        _completed_hits = _completed_hits.count()
        _total_hits = _remaining_hits + _completed_hits
                
        _data = (
          _name,
          len(_unique_systems_for_language_pair),
          (_remaining_hits, 100 * _remaining_hits/float(_total_hits or 1)),
          (_completed_hits, 100 * _completed_hits/float(_total_hits or 1))
        )
        
        language_pair_stats.append(_data)
    
    return language_pair_stats


def _compute_group_stats():
    """
    Computes group statistics for the WMT16 evaluation campaign.
    """
    group_stats = []
    
    wmt16_group = Group.objects.filter(name='WMT16')
    wmt16_users = _get_active_users_for_group(wmt16_group)
    
    # Aggregate information about participating groups.
    groups = set()
    for user in wmt16_users:
        for group in user.groups.all():
            if group.name == 'WMT16' or group.name.startswith('eng2') \
              or group.name.endswith('2eng'):
                continue
            
            groups.add(group)
            
    # TODO: move this to property of evaluation group or add dedicated data model.
    # GOAL: should be configurable from within the Django admin backend.
    #
    # MINIMAL: move to local_settings.py?
    #
    # The following dictionary defines the number of HITs each group should
    # have completed during the WMT16 evaluation campaign.
    
    for group in groups:
        _name = group.name
        if not _name in GROUP_HIT_REQUIREMENTS.keys():
            continue
        
        _group_stats = HIT.compute_status_for_group(group)
        _total = _group_stats[0]
        _required = GROUP_HIT_REQUIREMENTS[_name]
        _delta = _total - _required
        _data = (_total, _required, _delta)
        
        if _data[0] > 0:
            group_stats.append((_name, _data))
    
    # Sort by number of remaining HITs.
    group_stats.sort(key=lambda x: x[1][2])
    
    # Add totals at the bottom.
    global_total = sum([x[1][0] for x in group_stats])
    global_required = sum([x[1][1] for x in group_stats])
    global_delta = global_total - global_required
    global_data = (global_total, global_required, global_delta)
    group_stats.append(("Totals", global_data))
    
    return group_stats


def _compute_user_stats():
    """
    Computes user statistics for the WMT16 evaluation campaign.
    """
    user_stats = []
    
    wmt16_group = Group.objects.filter(name='WMT16')
    wmt16_users = _get_active_users_for_group(wmt16_group)
    
    for user in wmt16_users:
        _user_stats = HIT.compute_status_for_user(user)
        _name = user.username
        _avg_time = seconds_to_timedelta(_user_stats[1])
        _total_time = seconds_to_timedelta(_user_stats[2])
        _data = (_name, _user_stats[0], _avg_time, _total_time)
        
        if _data[0] > 0:
            user_stats.append(_data)
    
    # Sort by total number of completed HITs.
    user_stats.sort(key=lambda x: x[1])
    user_stats.reverse()
    
    return user_stats


def _compute_ranking_clusters(load_file=False):
    """
    Computes ranking clusters using Philipp Koehn's Perl code.
    """
    # Define file names.
    TMP_PATH = gettempdir()
    _script = join(ROOT_PATH, '..', 'scripts',
      'compute_ranking_clusters.perl')
    _wmt16 = join(TMP_PATH, 'wmt16-researcher-results.csv')
    _dump = join(TMP_PATH, 'wmt16-ranking-clusters.txt')
    
    # If not loading cluster data from file, re-compute everything.
    if not load_file:
        results = [u'srclang,trglang,srcIndex,documentId,segmentId,judgeId,' \
          'system1Number,system1Id,system2Number,system2Id,system3Number,' \
          'system3Id,system4Number,system4Id,system5Number,system5Id,' \
          'system1rank,system2rank,system3rank,system4rank,system5rank']
        
        # Compute current dump of WMT16 results in CSV format. We ignore any
        # results which are incomplete, i.e. have been SKIPPED.
        for result in RankingResult.objects.filter(item__hit__completed=True,
          item__hit__mturk_only=False):
            _csv_output = result.export_to_csv()
            if not _csv_output.endswith('-1,-1,-1,-1,-1'):
                results.append(_csv_output)
        
        results.append('')
        export_csv = u"\n".join(results)
        
        # Write current dump of results to file.
        with open(_wmt16, 'w') as outfile:
            outfile.write(export_csv)
        
        # Run Philipp's Perl script to compute ranking clusters.
        PERL_OUTPUT = check_output(['perl', _script, _wmt16], shell=True)
        
        with open(_dump, 'w') as outfile:
            outfile.write(PERL_OUTPUT)
    
    else:
        PERL_OUTPUT = ''
        with open(_dump, 'r') as infile:
            PERL_OUTPUT = infile.read()
    
    # Compute ranking cluster data for status page.
    CLUSTER_DATA = {}
    for line in PERL_OUTPUT.split("\n"):
        _data = line.strip().split(',')
        if not len(_data) == 5 or _data[0] == 'task':
            continue
        
        _data[0] = _data[0].replace('-', u' → ')
        if not CLUSTER_DATA.has_key(_data[0]):
            CLUSTER_DATA[_data[0]] = {}
        
        if not CLUSTER_DATA[_data[0]].has_key(_data[1]):
            CLUSTER_DATA[_data[0]][_data[1]] = []
        
        CLUSTER_DATA[_data[0]][_data[1]].append(_data[2:])
    
    _cluster_data = []
    _sorted_language_pairs = [x[1].decode('utf-8') for x in LANGUAGE_PAIR_CHOICES]
    for language_pair in _sorted_language_pairs:
        _language_data = []
        for cluster_id in sorted(CLUSTER_DATA[language_pair].keys()):
           _data = CLUSTER_DATA[language_pair][cluster_id]
           _language_data.append((cluster_id, _data))
        _cluster_data.append((language_pair, _language_data))
    
    return _cluster_data


def signup(request):
    """
    Renders the signup view.
    """
    LOGGER.info('Rendering WMT16 signup view.')
    errors = None
    username = None
    email = None
    token = None
    project_choices = Project.objects.all().values_list('name', flat=True).order_by('id')
    project_status = set()
    languages = set()
    
    focus_input = 'id_username'
    
    if request.method == "POST":
        username = request.POST.get('username', None)
        email = request.POST.get('email', None)
        token = request.POST.get('token', None)
        projects = request.POST.getlist('projects', None)
        languages = request.POST.getlist('languages', None)
        
        LOGGER.debug(projects)
        LOGGER.debug(languages)
        
        if username and email and token and projects and languages:
            try:
                # Check if given invite token is still active.
                invite = UserInviteToken.objects.filter(token=token)
                if not invite.exists() or not invite[0].active:
                    LOGGER.warning('Trying to create user "{0}" with ' \
                      'invalid invite token "{1}"'.format(username, token))
                    
                    raise ValueError('invalid_token')
                
                # We now have a valid invite token... 
                invite = invite[0]
                
                # Check if desired username is already in use.
                current_user = User.objects.filter(username=username)
                if current_user.exists():
                    LOGGER.warning('Trying to re-create user "{0}" with ' \
                      'invite token "{1}"'.format(current_user[0], token))
                    
                    raise ValueError('invalid_username')
                
                # Compute set of evaluation languages for this user.
                target_language_codes = set([x[0][3:] for x in LANGUAGE_PAIR_CHOICES])
                eval_groups = []
                for eval_language in target_language_codes:
                    if eval_language in languages:
                        eng2xyz = Group.objects.filter(name__endswith=eval_language)
                        if eng2xyz.exists():
                            eval_groups.extend(eng2xyz)

                # Also, add user to WMT16 group.
                wmt16_group = Group.objects.filter(name='WMT16')
                if wmt16_group.exists():
                    eval_groups.append(wmt16_group[0])
                
                LOGGER.debug('Evaluation languages: {0}'.format(eval_groups))
                
                # Create new user account and add to group.
                password = md5(invite.group.name).hexdigest()[:8]
                user = User.objects.create_user(username, email, password)
                
                # Update set of projects for this user.
                for project_name in projects:
                    project_instance = Project.objects.filter(name=project_name)
                    if project_instance.exists():
                        project_instance[0].users.add(user)
                
                # Update group settings for the new user account.
                invite.group.user_set.add(user)
                for eval_group in eval_groups:
                    eval_group.user_set.add(user)
                
                # Disable invite token.
                invite.active = False
                invite.save()
                
                # Login user and redirect to WMT16 overview page.
                user = authenticate(username=username, password=password)
                login(request, user)
                return redirect('appraise.wmt16.views.overview')
            
            # For validation errors, invalidate the respective value.
            except ValueError as issue:
                if issue.message == 'invalid_username':
                    username = None
                
                elif issue.message == 'invalid_token':
                    token = None
                
                else:
                    from traceback import format_exc
                    LOGGER.debug(format_exc())
                    
                    username = None
                    email = None
                    token = None
                    project_choices = Project.objects.all().values_list('name', flat=True).order_by('id')
                    project_status = set()
                    languages = set()
            
            # For any other exception, clean up and ask user to retry.
            except:
                from traceback import format_exc
                LOGGER.debug(format_exc())
                
                username = None
                email = None
                token = None
                project_choices = Project.objects.all().values_list('name', flat=True).order_by('id')
                project_status = set()
                languages = set()
        
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
        if not projects:
            focus_input = 'id_projects'
            errors = ['invalid_projects']
        elif not languages:
            focus_input = 'id_languages'
            errors = ['invalid_languages']

    context = {
      'active_page': "OVERVIEW",
      'errors': errors,
      'focus_input': focus_input,
      'username': username,
      'email': email,
      'token': token,
      'project_choices': project_choices,
      'project_status': project_status,
      'languages': languages,
      'title': 'WMT16 Sign up',
    }
    context.update(BASE_CONTEXT)
    
    return render(request, 'wmt16/signup.html', context)

@login_required
def profile_update(request):
    """
    Renders the profile update view.
    """
    LOGGER.info('Rendering WMT16 profile update view.')
    errors = None
    project_choices = Project.objects.all().values_list('name', flat=True).order_by('id')
    project_status = set()
    languages = set()
        
    focus_input = 'id_projects'
    
    if request.method == "POST":
        projects = request.POST.getlist('projects', None)
        languages = request.POST.getlist('languages', None)
        
        LOGGER.debug(projects)
        LOGGER.debug(languages)
        
        if projects and languages:
            try:
                # Update set of projects for this user.
                for project_name in projects:
                    project_instance = Project.objects.filter(name=project_name)
                    if project_instance.exists():
                        project_instance[0].users.add(request.user)
                
                # Compute set of evaluation languages for this user.
                target_language_codes = set([x[0][3:] for x in LANGUAGE_PAIR_CHOICES])
                LOGGER.debug('Language codes: {0}'.format(target_language_codes))
                eval_groups = []
                for eval_language in target_language_codes:
                    if eval_language in languages:
                        eng2xyz = Group.objects.filter(name__endswith=eval_language)
                        if eng2xyz.exists():
                            eval_groups.extend(eng2xyz)

                # Also, add user to WMT16 group.
                wmt16_group = Group.objects.filter(name='WMT16')
                if wmt16_group.exists():
                    eval_groups.append(wmt16_group[0])

                LOGGER.debug('Evaluation languages: {0}'.format(eval_groups))
                
                # Update group settings for the new user account.
                for eval_group in eval_groups:
                    eval_group.user_set.add(request.user)
                
                # Redirect to WMT16 overview page.
                return redirect('appraise.wmt16.views.overview')
            
            # For any other exception, clean up and ask user to retry.
            except:
                from traceback import format_exc
                LOGGER.debug(format_exc())
                
                project_choices = Project.objects.all().values_list('name', flat=True).order_by('id')
                project_status = set()
                languages = set()
        
        # Detect which input should get focus for next page rendering.
        if not projects:
            focus_input = 'id_projects'
            errors = ['invalid_projects']
        elif not languages:
            focus_input = 'id_languages'
            errors = ['invalid_languages']
    
    # Determine user annotation projects
    for project in Project.objects.all():
        if request.user in project.users.all():
            project_status.add(project.name)
    
    # Determine user target languages
    for group in request.user.groups.all():
        if 'eng2' in group.name or '2eng' in group.name:
            languages.add(group.name[3:])
        
    context = {
      'active_page': "OVERVIEW",
      'errors': errors,
      'focus_input': focus_input,
      'project_choices': project_choices,
      'project_status': project_status,
      'languages': languages,
      'title': 'WMT16 profile update',
    }
    context.update(BASE_CONTEXT)
    
    return render(request, 'wmt16/profile_update.html', context)

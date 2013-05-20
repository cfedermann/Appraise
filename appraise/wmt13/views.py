# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>
"""
import logging

from collections import Counter
from datetime import datetime, date
from random import randint, seed, shuffle
from time import mktime

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import Context
from django.template.defaultfilters import slugify
from django.template.loader import get_template

from appraise.wmt13.models import HIT, RankingTask, RankingResult
from appraise.settings import LOG_LEVEL, LOG_HANDLER, COMMIT_TAG

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('appraise.wmt13.views')
LOGGER.addHandler(LOG_HANDLER)


from appraise.wmt13.models import LANGUAGE_PAIR_CHOICES
from appraise.wmt13.models import HIT, RankingTask, UserHITMapping


def _compute_next_task_for_user(user, language_pair):
    """
    Computes the next task for the given user and language pair combination.

    This may either be the HIT the given user is currently working on or a
    new HIT in case the user has completed all previous HITs already.

    By convention, language_pair is a String in format xxx2yyy where both
    xxx and yyy are ISO-639-3 language codes.

    """
    # Check if language_pair is valid for the given user.
    if not user.groups.filter(name=language_pair):
        LOGGER.debug('User {0} does not know language pair {1}.'.format(
          user, language_pair))
        return None

    # Check if there exists a current HIT for the given user.
    current_hitmap = UserHITMapping.objects.filter(user=user,
      hit__language_pair=language_pair)

    # If there is no current HIT to continue with, find a random HIT for the
    # given user.  We keep generating a random block_id in [1, 1000] until we
    # find a matching HIT which the current user has not yet completed.
    if not current_hitmap:
        LOGGER.debug('No current HIT for user {0}, fetching HIT.'.format(
          user))
        
        # TODO: this is bizarre;  maybe we can just live with getting the
        # values_list of all block_ids which are still available for the
        # given user and then draw one of these randomly using random.choice?
        
        random_id = randint(1, 1000)
        random_hit = None
        
        # Compatible HIT instances need to match the given language pair!
        hits = HIT.objects.filter(language_pair=language_pair, active=True)
        
        # Compute list of compatible block ids and randomise its order.
        block_ids = list(hits.values_list('block_id', flat=True))
        shuffle(block_ids)
        
        # Find the next HIT for the current user.
        random_hit = None
        for block_id in block_ids:
            matching_hits = HIT.objects.filter(block_id=block_id,
              language_pair=language_pair)
            
            for hit in matching_hits:
                hit_users = list(hit.users.all())
                if len(hit_users) < 3 and not user in hit_users:
                    random_hit = hit
                    break
        
        if False:
            # First check if there exists a HIT with block_id >= random_id.
            random_hits = hits.filter(block_id__gte=random_id)
            for hit in random_hits:
                hit_users = list(hit.users.all())
                if len(hit_users) < 3 and not user in hit_users:
                    random_hit = hit
                    break
        
            # If this did not yield a next HIT, try with block_id < random_id.
            if not random_hit:
                random_hits = hits.filter(block_id__lt=random_id)
                for hit in random_hits:
                    hit_users = list(hit.users.all())
                    if len(hit_users) < 3 and not user in hit_users:
                        random_hit = hit
                        break
        
        # If we still haven't found a next HIT, there simply is none...
        if not random_hit:
            return None
        
        # Update User/HIT mappings s.t. the system knows about the next HIT.
        current_hitmap = UserHITMapping.objects.create(user=user,
          hit=random_hit)
    
    # Otherwise, select first match from QuerySet.
    else:
        current_hitmap = current_hitmap[0]
    
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
    
    print _result
    print duration, raw_result
    
    _result.duration = str(duration)
    _result.raw_result = raw_result
    
    print type(_result.duration)
    
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
        
        print _raw_result
        print
        print current_item, type(current_item)
        print request.user, type(request.user)
        print duration, type(duration)
        print _raw_result, type(_raw_result)
        # Save results for this item to the Django database.
        _save_results(current_item, request.user, duration, _raw_result)
    
    # Find next item the current user should process or return to overview.
    item = _find_next_item_to_process(items, request.user, False)
    if not item:
        return redirect('appraise.wmt13.views.overview')

    # Compute source and reference texts including context where possible.
    source_text, reference_text = _compute_context_for_item(item)
    
    # Retrieve the number of finished items for this user and the total number
    # of items for this task. We increase finished_items by one as we are
    # processing the first unfinished item.
    finished_items, total_items = task.get_finished_for_user(request.user)
    finished_items += 1
    
    # Create list of translation alternatives in randomised order.
    translations = []
    order = range(len(item.translations))
    shuffle(order)
    for index in order:
        translations.append(item.translations[index])
    
    dictionary = {
      'action_url': request.path,
      'commit_tag': COMMIT_TAG,
      'description': None,
      'item_id': item.id,
      'block_id': item.hit.block_id,
      'language_pair': item.hit.get_language_pair_display(),
      'order': ','.join([str(x) for x in order]),
      'reference_text': reference_text,
      'source_text': source_text,
      'task_progress': '{0:03d}/{1:03d}'.format(finished_items, total_items),
      'title': 'Ranking',
      'translations': translations,
    }
    
    return render(request, 'wmt13/ranking.html', dictionary)


@login_required
def hit_handler(request, hit_id):
    """
    General task handler.
    
    Finds the task with the given hit_id and redirects to its task handler.
    
    """
    LOGGER.info('Rendering task handler view for user "{0}".'.format(
      request.user.username or "Anonymous"))
    
    hit = get_object_or_404(HIT, hit_id=hit_id)
    items = RankingTask.objects.filter(hit=hit)
    if not items:
        return redirect('appraise.wmt13.views.overview')
    
    return _handle_ranking(request, hit, items)


# TODO: check this code.
@login_required
def overview(request):
    """
    Renders the evaluation tasks overview.
    """
    LOGGER.info('Rendering WMT13 HIT overview for user "{0}".'.format(
      request.user.username or "Anonymous"))
    
    # Re-initialise random number generator.
    seed(None)
    
    # Collect available language pairs for the current user.
    language_codes = set([x[0] for x in LANGUAGE_PAIR_CHOICES])
    language_pairs = request.user.groups.filter(name__in=language_codes)
    
    hit_data = []
    for language_pair in language_pairs:
        current_hit = _compute_next_task_for_user(request.user, language_pair)
        if current_hit:
            hit_data.append(
              (current_hit.get_language_pair_display(),
               current_hit.get_absolute_url(), current_hit.block_id,
               current_hit.get_status_for_user(request.user))
            )
    
    # TODO: add HIT status to HIT object model to speed up things!
    #       we might then be able to just pass one HIT instance?
    
    print hit_data
    
    dictionary = {
      'active_page': "OVERVIEW",
      'commit_tag': COMMIT_TAG,
      'hit_data': hit_data,
      'title': 'WMT13 Dashboard',
    }
    
    return render(request, 'wmt13/overview.html', dictionary)


# TODO: check this code.
@login_required
def profile_view(request):
    """
    Renders the evaluation tasks status page for staff users.
    """
    LOGGER.info('Rendering evaluation task overview for user "{0}".'.format(
      request.user.username))
    
    if hit_id:
        task = get_object_or_404(HIT, hit_id=hit_id)
        
        headers = task.get_status_header()
        status = []
        
        for user in task.users.all():
            status.append((user.username, task.get_status_for_user(user)))
        
        scores = None
        result_data = []
        raw_result_data = Counter()
        users = list(task.users.all())
        
        for item in RankingTask.objects.filter(task=task):
            results = []
            for user in users:
                qset = RankingResult.objects.filter(user=user, item=item)
                if qset.exists():
                    category = str(qset[0].results)
                    results.append((user.id, item.id, category))
                    raw_result_data[qset[0].raw_result] += 1
            
            if len(results) == len(users):
                result_data.extend(results)
        
        _raw_results = []
        _keys = raw_result_data.keys()
        _total_results = float(sum(raw_result_data.values()))
        for key in sorted(_keys):
            value = raw_result_data[key]
            _raw_results.append((key, value, 100 * value / _total_results))
        
        try:
            # Computing inter-annotator agreement only makes sense for more
            # than one coder -- otherwise, we only display result_data...
            if len(users) > 1:
                # Check if we can safely use NLTK's AnnotationTask class.
                try:
                    from nltk.metrics.agreement import AnnotationTask
                    chk = AnnotationTask(data=[('b', '1', 'k'),
                      ('a', '1', 'k')])
                    assert(chk == 1.0)
                
                except AssertionError:
                    LOGGER.debug('Fixing outdated version of AnnotationTask.')
                    from appraise.utils import AnnotationTask

                # We have to sort annotation data to prevent StopIterator errors.
                result_data.sort()
                annotation_task = AnnotationTask(result_data)
                
                scores = (
                  annotation_task.alpha(),
                  annotation_task.kappa(),
                  annotation_task.S(),
                  annotation_task.pi()
                )
        
        except ZeroDivisionError:
            scores = None
        
        except ImportError:
            scores = None
        
        dictionary = {
          'combined': task.get_status_for_users(),
          'commit_tag': COMMIT_TAG,
          'headers': headers,
          'scores': scores,
          'raw_results': _raw_results,
          'status': status,
          'task_id': task.hit_id,
          'task_name': task.task_name,
          'title': 'Evaluation Task Status',
        }

        return render(request, 'evaluation/status_task.html', dictionary)
    
    else:
        evaluation_tasks = {}
        for task_type_id, task_type in APPRAISE_TASK_TYPE_CHOICES:
            # We collect a list of task descriptions for this task_type.
            evaluation_tasks[task_type] = []
        
            # Super users see all HIT items, even non-active ones.
            if request.user.is_superuser:
                _tasks = HIT.objects.filter(task_type=task_type_id)
        
            else:
                _tasks = HIT.objects.filter(task_type=task_type_id,
                  active=True)
        
            # Loop over the QuerySet and compute task description data.
            for _task in _tasks:
                _task_data = None
                
                # Append new task description to current task_type list.
                evaluation_tasks[task_type].append(_task_data)
            
            # If there are no tasks descriptions for this task_type, we skip it.
            if len(evaluation_tasks[task_type]) == 0:
                evaluation_tasks.pop(task_type)

        dictionary = {
          'active_page': "STATUS",
          'commit_tag': COMMIT_TAG,
          'evaluation_tasks': evaluation_tasks,
          'title': 'Evaluation Task Status',
        }

        return render(request, 'evaluation/status.html', dictionary)

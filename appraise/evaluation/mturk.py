# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>
"""
import logging

from random import randint, seed, shuffle

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from appraise.evaluation.models import APPRAISE_TASK_TYPE_CHOICES, \
  EvaluationTask, EvaluationItem, EvaluationResult
from appraise.settings import LOG_LEVEL, LOG_HANDLER, COMMIT_TAG


# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('appraise.evaluation.mturk')
LOGGER.addHandler(LOG_HANDLER)


def _find_next_item_to_process(items, user, random_order=False):
    """
    Computes the next item the current user should process or None, if done.
    """
    user_results = EvaluationResult.objects.filter(user=user)
    
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
    
    left_context = EvaluationItem.objects.filter(task=item.task, pk=item.id-1)
    right_context = EvaluationItem.objects.filter(task=item.task, pk=item.id+1)
    
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


def _handle_ranking(request, task, items):
    """
    Handler for Ranking tasks.
    
    Finds the next item belonging to the given task, renders the page template
    and creates an EvaluationResult instance on HTTP POST submission.
    
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
        current_item = get_object_or_404(EvaluationItem, pk=int(item_id))
        
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
        
        # Save results for this item to the Django database.
        _save_results(current_item, request.user, duration, _raw_result)
    
    # Find next item the current user should process or return to overview.
    item = _find_next_item_to_process(items, request.user, task.random_order)
    if not item:
        return redirect('appraise.evaluation.views.overview')

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
    
    if task.random_order:
        shuffle(order)
    
    for index in order:
        translations.append(item.translations[index])
    
    dictionary = {
      'action_url': request.path,
      'commit_tag': COMMIT_TAG,
      'description': task.description,
      'item_id': item.id,
      'order': ','.join([str(x) for x in order]),
      'reference_text': reference_text,
      'source_text': source_text,
      'task_progress': '{0:03d}/{1:03d}'.format(finished_items, total_items),
      'title': 'Ranking',
      'translations': translations,
    }
    
    return render(request, 'evaluation/mturk_ranking.html', dictionary)


def task_handler(request, task_id):
    """
    Task handler integrating with Amazon's Mechanical Turk.
    
    Does NOT require a logged in user but will check that the task specified
    by the given task_id does actually allow external MTurk usage.
    
    """
    LOGGER.info('Rendering MTurk task handler view for user "{0}".'.format(
      request.user.username or "Anonymous"))
    
    task = get_object_or_404(EvaluationTask, task_id=task_id)
    items = EvaluationItem.objects.filter(task=task)
    if not items:
        return HttpResponseForbidden("MTurk access forbidden")
    
    _task_type = task.get_task_type_display()
    if _task_type == 'Ranking':
        return _handle_ranking(request, task, items)
    
    _msg = 'No MTurk handler for task type: "{0}"'.format(_task_type)
    raise NotImplementedError, _msg


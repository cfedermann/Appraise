# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
"""
import logging
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.utils import simplejson
from datetime import datetime
from random import shuffle
from time import mktime
from traceback import format_exc
from appraise.evaluation.models import RankingTask, RankingItem, RankingResult
from appraise.evaluation.models import ClassificationResult
from appraise.evaluation.models import EditingTask, EditingItem, EditingResult
from appraise.evaluation.models import LucyTask, LucyItem, LucyResult
from appraise.evaluation.models import QualityTask, QualityItem, QualityResult

from appraise.evaluation.models import APPRAISE_TASK_TYPE_CHOICES
from appraise.evaluation.models import EvaluationTask, EvaluationItem
from appraise.settings import LOG_LEVEL, LOG_HANDLER

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('appraise.evaluation.views')
LOGGER.addHandler(LOG_HANDLER)

@login_required
def _handle_quality_checking(request, task, items):
    now = datetime.now()
    
    if request.method == "POST":
        item_id = request.POST.get('item_id')
        quality = request.POST.get('submit_button')
        _now = request.POST.get('now')
        if _now:
            duration = now - datetime.fromtimestamp(float(_now))
            print "duration: {}".format(duration)
        
        print "item_id: {0}".format(item_id)
        print "quality: {0}".format(quality)
        
        # TODO:
        #
        # 1) create suitable result container type instance
        # 2) serialise result data into XML format
        # 3) create (or update) result instance and save it
    
    # TODO: add loop to find "next item to edit" based on items
    
    item = items[0]
    dictionary = {'title': 'Translation Quality Checking',
      'task_progress': '{0:03d}/{1:03d}'.format(1, len(items)),
      'source_text': item.source, 'translation_text': item.translations[0],
      'context_text': item.reference, 'item_id': item.id,
      'now': mktime(datetime.now().timetuple())}
    
    return render_to_response('evaluation/quality_checking.html', dictionary,
      context_instance=RequestContext(request))

@login_required
def _handle_ranking(request, task, items):
    pass

@login_required
def _handle_postediting(request, task, items):
    pass

@login_required
def _handle_error_classification(request, task, items):
    pass

@login_required
def task_handler(request, task_id):
    LOGGER.info('Rendering task handler view for user "{0}".'.format(
      request.user.username or "Anonymous"))
    
    now = datetime.now()
    task = get_object_or_404(EvaluationTask, task_id=task_id)
    items = EvaluationItem.objects.filter(task=task)
    if not items:
        return redirect('appraise.evaluation.views.overview')
    
    _task_type = task.get_task_type_display()
    if _task_type == 'Quality Checking':
        return _handle_quality_checking(request, task, items)
    
    elif _task_type == 'Ranking':
        return _handle_ranking(request, task, items)
    
    elif _task_type == 'Post-editing':
        return _handle_postediting(request, task, items)
    
    elif _task_type == 'Error classification':
        return _handle_error_classification(request, task, items)
    
    _msg = 'No handler for task type: "{0}"'.format(_task_type)
    raise NotImplementedError, _msg


@login_required
def overview(request):
    """Renders the evaluation tasks overview."""
    LOGGER.info('Rendering evaluation task overview for user "{0}".'.format(
      request.user.username or "Anonymous"))
    
    if request.user.is_staff:
        
        evaluation_tasks = {}
        for task_type_id, task_type in APPRAISE_TASK_TYPE_CHOICES:
            _tasks = EvaluationTask.objects.filter(task_type=task_type_id)
            evaluation_tasks[task_type] = []
            
            for _task in _tasks:
                _url = reverse('appraise.evaluation.views.task_handler',
                  kwargs={'task_id': _task.task_id})
                _task_data = {'url': _url, 'task_name': _task.task_name,
                  'header': _task.get_status_header,
                  'status': _task.get_status_for_user(request.user)}
                evaluation_tasks[task_type].append(_task_data)
        
        ranking_tasks = RankingTask.objects.all()
        editing_tasks = EditingTask.objects.all()
        lucy_tasks = LucyTask.objects.all()
    
    else:
        ranking_tasks = RankingTask.objects.filter(users=request.user)
        editing_tasks = EditingTask.objects.filter(users=request.user)
        lucy_tasks = LucyTask.objects.filter(users=request.user)
    
    quality_tasks = QualityTask.objects.filter(users=request.user)
      
    dictionary = {'title': 'Evaluation Task Overview',
    
      'evaluation_tasks': evaluation_tasks,
    
      'ranking_tasks': ranking_tasks.order_by('shortname'),
      'editing_tasks': editing_tasks.order_by('shortname'),
      'lucy_tasks': lucy_tasks.order_by('shortname'),
      'quality_tasks': quality_tasks.order_by('shortname')}
    return render_to_response('evaluation/overview.html', dictionary,
      context_instance=RequestContext(request))

@login_required
def ranking(request, task_id):
    """Renders the task 1: ranking and error classification view."""
    LOGGER.info('Rendering ranking view for user "{0}".'.format(
      request.user.username or "Anonymous"))

    task = get_object_or_404(RankingTask, task_id=task_id)
    items = RankingItem.objects.filter(task=task, edited=False)
    if not items:
        return redirect('appraise.evaluation.views.overview')

    if request.is_ajax():
        if request.method == "POST":
            mode = request.POST.get('mode')
            
            if mode == "RANKING":
                LOGGER.info('AJAX: received ranking, sending sentence id.')

                item_id = request.POST.get('item_id')
                order = request.POST.get('order')
                ranks = request.POST.get('ranks')
                system_id = -1
                
                if item_id and order and ranks:
                    _order = [int(k.split('=')[1]) for k in order.split(',')]
                    _rank = [int(k.split('=')[1]) for k in ranks.split(',')]
                    item = get_object_or_404(RankingItem, pk=int(item_id))
                    
                    print "ORDER: {0}".format(_order)
                    print "RANKS: {0}".format(_rank)

                    try:
                        existing_result = RankingResult.objects.get(item=item)
                        existing_result.user = request.user
                        existing_result.rankA = _rank[_order[0]]
                        existing_result.rankB = _rank[_order[1]]
                        existing_result.rankC = _rank[_order[2]]
                        existing_result.rankD = _rank[_order[3]]
                        existing_result.save()
                    
                    except RankingResult.DoesNotExist:
                        new_result = RankingResult(item=item,
                          user=request.user, rankA=_rank[_order[0]],
                          rankB=_rank[_order[1]], rankC=_rank[_order[2]],
                          rankD=_rank[_order[3]])
                        new_result.save()
                    
                    # cfedermann: We have the user classify errors on the best
                    #   translation from the previous ranking.
                    for k in range(4):
                        print "_r[_o[k]] = {0}".format(_rank[_order[k]])
                        if _rank[_order[k]] == 1:
                            system_id = _order[k]

                json = simplejson.dumps({'system_id': system_id})
                return HttpResponse(json, mimetype="text/plain")
            
            elif mode == "CLASSIFICATION":
                LOGGER.info('AJAX: received classfication, sending new data.')

                item_id = request.POST.get('item_id')
                system_id = request.POST.get('system_id')
                errors = request.POST.get('errors')
                comments = request.POST.get('comments')

                if item_id and system_id:
                    item = get_object_or_404(RankingItem, pk=int(item_id))
                    if errors:
                        _errors = [int(x) for x in errors.split(',')]
                    else:
                        _errors = []

                    existing_result = ClassificationResult.objects.filter(
                      item=item)

                    if existing_result:
                        existing = existing_result[0]
                        existing.user = request.user
                        existing.system = chr(65 + int(system_id))
                        existing.missing_content_words = 0 in _errors
                        existing.content_words_wrong = 1 in _errors
                        existing.wrong_functional_words = 2 in _errors
                        existing.incorrect_word_forms = 3 in _errors
                        existing.incorrect_word_order = 4 in _errors
                        existing.incorrect_punctuation = 5 in _errors
                        existing.other_error = 6 in _errors
                        existing.comments = comments
                        existing.save()

                    else:
                        new_result = ClassificationResult(item=item,
                          user=request.user, system=chr(65 + int(system_id)))
                        new_result.missing_content_words = 0 in _errors
                        new_result.content_words_wrong = 1 in _errors
                        new_result.wrong_functional_words = 2 in _errors
                        new_result.incorrect_word_forms = 3 in _errors
                        new_result.incorrect_word_order = 4 in _errors
                        new_result.incorrect_punctuation = 5 in _errors
                        new_result.other_error = 6 in _errors
                        new_result.comments = comments
                        new_result.save()

                item.edited = True
                item.save()

            elif mode == "FLAG_ERROR":
                LOGGER.info('AJAX: received flag error, skipping sentence.')

                item_id = request.POST.get('item_id')

                if item_id:
                    item = get_object_or_404(RankingItem, pk=int(item_id))
                    item.edited = True
                    item.save()

        else:
            LOGGER.info('AJAX: sending ranking data.')
        
        items = RankingItem.objects.filter(task=task, edited=False)
        if not items:
            json = simplejson.dumps({'item_id': -1})
            return HttpResponse(json, mimetype="text/plain")

        item = items[0]

        _shuffled = range(4)
        shuffle(_shuffled)
        
        # cfedermann: we need to store the mapping from original id [0-3] to
        #   shuffled id.  E.g., 0=2 would mean that system A will be displayed
        #   as system C in the interface.
        _order = ','.join(['{0}={1}'.format(k, _shuffled[k])
          for k in range(4)])
    
        _status = task.get_status()

        systems = {
          'task_progress': '{0:03d}/{1:03d}'.format(_status[0], _status[1]),
          'source_text': item.source, 'order': _order, 'item_id': item.id
        }

        # Insert system translations in randomized order.
        systems.update({'system_{0}_text'.format(_shuffled[0]): item.systemA})
        systems.update({'system_{0}_text'.format(_shuffled[1]): item.systemB})
        systems.update({'system_{0}_text'.format(_shuffled[2]): item.systemC})
        systems.update({'system_{0}_text'.format(_shuffled[3]): item.systemD})
    
        # Encode systems' output as JSON data and create HTTP response.
        json = simplejson.dumps(systems)
        return HttpResponse(json, mimetype="text/plain")

    dictionary = {'title': 'Task 1: Ranking and Error Classification'}
    return render_to_response('evaluation/ranking.html', dictionary,
      context_instance=RequestContext(request))


@login_required
def editing(request, task_id):
    """Renders the task 2: manual post-editing view."""
    LOGGER.info('Rendering manual post-editing view for user "{0}".'.format(
      request.user.username or "Anonymous"))

    task = get_object_or_404(EditingTask, task_id=task_id)
    items = EditingItem.objects.filter(task=task, edited=False)
    if not items:
        return redirect('appraise.evaluation.views.overview')

    if request.is_ajax():
        LOGGER.info('Entering AJAX mode.')
        
        if request.method == "POST":
            item_id = request.POST.get('item_id')
            system_id = request.POST.get('system_id')
            order = request.POST.get('order')
            postedited = request.POST.get('text')

            if item_id and system_id and order and postedited:
                _order = [int(k.split('=')[1]) for k in order.split(',')]
                system_code = chr(65+_order[int(system_id)])
                item = get_object_or_404(EditingItem, pk=int(item_id))

                existing_result = EditingResult.objects.filter(item=item)
                if existing_result:
                    existing = existing_result[0]
                    existing.user = request.user
                    existing.system = system_code
                    existing.postedited = postedited
                    existing.save()
                
                else:
                    new_result = EditingResult(item=item, user=request.user,
                      system=system_code, postedited=postedited)
                    new_result.save()

                item.edited = True
                item.save()

        items = EditingItem.objects.filter(task=task, edited=False)
        if not items:
            json = simplejson.dumps({'item_id': -1})
            return HttpResponse(json, mimetype="text/plain")

        item = items[0]

        _shuffled = range(3)
        shuffle(_shuffled)
        
        # cfedermann: applied fix suggested by Lefteris.
        #
        #   This seems rather the wrong way of fixing the random order bugs?
        #   For ranking, the reversal of (k, _shuffled[k]) lead to problems;
        #   Will have to check what exactly goes wrong for post-editing...
        _order = ','.join(['{0}={1}'.format(_shuffled[k], k)
          for k in range(3)])
        
        _status = task.get_status()

        systems = {
          'task_progress': '{0:03d}/{1:03d}'.format(_status[0], _status[1]),
          'source_text': item.source, 'order': _order, 'item_id': item.id
        }

        # Insert system translations in randomized order.
        systems.update({'system_{0}_text'.format(_shuffled[0]): item.systemA})
        systems.update({'system_{0}_text'.format(_shuffled[1]): item.systemB})
        systems.update({'system_{0}_text'.format(_shuffled[2]): item.systemC})

        # Encode systems' output as JSON data and create HTTP response.
        json = simplejson.dumps(systems)
        return HttpResponse(json, mimetype="text/plain")

    dictionary = {'title': 'Task 2: Manual Post-Editing'}
    return render_to_response('evaluation/editing.html', dictionary,
      context_instance=RequestContext(request))


@login_required
def lucy_ranking(request, task_id):
    """Renders the task 3: Lucy ranking view."""
    LOGGER.info('Rendering manual Lucy ranking view for user "{0}".'.format(
      request.user.username or "Anonymous"))

    task = get_object_or_404(LucyTask, task_id=task_id)
    items = LucyItem.objects.filter(task=task, edited=False)
    if not items:
        return redirect('appraise.evaluation.views.overview')

    if request.is_ajax():
        LOGGER.info('Entering AJAX mode.')
        
        if request.method == "POST":
            item_id = request.POST.get('item_id')
            order = request.POST.get('order')
            ranks = request.POST.get('ranks')

            if item_id and order and ranks:
                _order = [int(k.split('=')[1]) for k in order.split(',')]
                if _order[0] and ranks != '==':
                    if 'W' in ranks:
                        ranks = ranks.replace('W', 'B')
                    else:
                        ranks = ranks.replace('B', 'W')
                
                print "RESULTING RANKING", ranks
                item = get_object_or_404(LucyItem, pk=int(item_id))

                try:
                    existing_result = LucyResult.objects.filter(item=item,
                      user=request.user)
                    if existing_result:
                        existing = existing_result[0]
                        existing.ranking = ranks
                        existing.save()
                
                    else:
                        new_result = LucyResult(item=item, user=request.user,
                          ranking=ranks)
                        new_result.save()
                except Exception:
                    print format_exc()

        completed = 0
        items = LucyItem.objects.filter(task=task).order_by('id')
        item = None
        for _item in items:
            if LucyResult.objects.filter(item=_item, user=request.user):
                completed += 1
                continue
            
            item = _item
            break
        
        if not item:
            json = simplejson.dumps({'item_id': -1})
            return HttpResponse(json, mimetype="text/plain")

        _shuffled = range(2)
        shuffle(_shuffled)
        _order = ','.join(['{0}={1}'.format(k, _shuffled[k])
          for k in range(2)])
        
        _status = task.get_status()

        systems = {
          'task_progress': '{0:03d}/{1:03d}'.format(completed, _status[1]),
          'source_text': item.source, 'reference_text': item.reference,
          'order': _order, 'item_id': item.id
        }

        # Insert system translations in randomized order.
        system_a = item.systemA.replace('<', '&lt;').replace('>', '&gt;')
        system_b = item.systemB.replace('<', '&lt;').replace('>', '&gt;')
        systems.update({'system_{0}_text'.format(_shuffled[0]): system_a})
        systems.update({'system_{0}_text'.format(_shuffled[1]): system_b})

        # Encode systems' output as JSON data and create HTTP response.
        json = simplejson.dumps(systems)
        return HttpResponse(json, mimetype="text/plain")

    dictionary = {'title': 'Task 3: Lucy Evaluation for EM+'}
    return render_to_response('evaluation/lucy_ranking.html', dictionary,
      context_instance=RequestContext(request))


def quality_checking(request, task_id):
    """Renders the 'Quality acceptable?' assessment view."""
    LOGGER.info('Rendering "Quality acceptable?" assessment view for user ' \
      '"{0}".'.format(request.user.username or "Anonymous"))
    
    now = datetime.now()
    task = get_object_or_404(QualityTask, task_id=task_id)
    items = QualityItem.objects.filter(task=task, edited=False).order_by('id')
    if not items:
        return redirect('appraise.evaluation.views.overview')
    
    item_id = None
    if request.method == "POST":
        item_id = request.POST.get('item_id')
        quality = request.POST.get('submit_button')
        
        if item_id and quality:
            item = get_object_or_404(QualityItem, pk=int(item_id))
            
            _now = request.POST.get('now')
            if _now:
                duration = now - datetime.fromtimestamp(float(_now))
            
            try:
                existing_result = QualityResult.objects.filter(item=item,
                  user=request.user)
                if existing_result:
                    existing = existing_result[0]
                    existing.quality = quality[0].upper()
                    
                    if duration:
                        existing.duration = duration
                    
                    existing.save()
                
                else:
                    new_result = QualityResult(item=item, user=request.user,
                      quality=quality[0].upper())
                    
                    if duration:
                        new_result.duration = duration
                    
                    new_result.save()
            
            except Exception:
                print format_exc()
            
            item.edited = True
            item.save()
    
    items = QualityItem.objects.filter(task=task, edited=False).order_by('id')
    if not items:
        return redirect('appraise.evaluation.views.overview')
    
    item = items[0]
    _status = task.get_status()
    dictionary = {'title': 'Translation Quality Checking',
      'task_progress': '{0:03d}/{1:03d}'.format(_status[0] + 1, _status[1]),
      'source_text': item.source, 'translation_text': item.translation,
      'context_text': item.context, 'item_id': item.id,
      'now': mktime(datetime.now().timetuple())}
    
    return render_to_response('evaluation/quality_checking.html', dictionary,
      context_instance=RequestContext(request))

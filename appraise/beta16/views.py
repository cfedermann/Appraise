from datetime import datetime
from random import shuffle
from traceback import format_exc

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from appraise.beta16.models import AbsoluteScoringTask, AbsoluteScoringData
from appraise.beta16.models import MetaData
from appraise.settings import COMMIT_TAG, STATIC_URL

# Base context for all views.
BASE_CONTEXT = {
  'commit_tag': COMMIT_TAG,
  'title': 'Appraise evaluation system',
  'installed_apps': ['absolut'],
  'static_url': STATIC_URL,
}

@login_required
def overview(request):
    """
    Renders the evaluation tasks overview.
    """
    # For now, just render the scoring handler to get a random scoring task...
    return scoring_handler(request)


@login_required
def scoring_handler(request):
    """
    Renders a random AbsoluteScoringTask for testing.
    """
    if request.method == "POST":
        try:
            score = int(request.POST['score'])
            if score != -1:
                user = request.user
                task_id = request.POST['task_id']
                task = AbsoluteScoringTask.objects.get(id=task_id)

                # Create new AbsoluteScoringData object
                scoring_data = AbsoluteScoringData()
                scoring_data.user = request.user
                scoring_data.task = task
                scoring_data.score = score
                scoring_data.save()

                scoring_data.metadata.completed = True
                scoring_data.metadata.end_time = datetime.now()
                scoring_data.metadata.save()

        except:
            print format_exc()
            pass

    scoring_task_ids = list(AbsoluteScoringTask.objects.filter(metadata__isnull=True).values_list('id', flat=True))
    shuffle(scoring_task_ids)

    try:
        current_task = AbsoluteScoringTask.objects.get(id=scoring_task_ids[0])
    except:
        current_task = None

    if not current_task:
        return HttpResponse("No scoring task available yet...")

    if current_task.metadata:
        current_meta = current_task.metadata
    else:
        current_meta = MetaData()
        current_meta.save()
        current_meta.users.add(request.user)

    current_meta.assigned = datetime.now()

    current_task.metadata = current_meta
    current_task.save()

    dictionary = {
      'action_url': request.path,
      'task_id': current_task.id,
      'segment_id': current_task.segment_id,
      'language_pair': '{0}&rarr;{1}'.format(current_task.source_language, current_task.target_language),
      'reference_text': current_task.reference,
      'candidate_text': current_task.candidate,
      'title': 'Scoring'
    }
    dictionary.update(BASE_CONTEXT)

    return render(request, 'beta16/scoring.html', dictionary)

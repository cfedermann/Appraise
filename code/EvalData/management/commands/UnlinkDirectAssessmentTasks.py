"""
Appraise evaluation framework
"""
# pylint: disable=W0611
from datetime import datetime, timedelta
from os import path
from django.contrib.auth.models import User

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q
from django.db.utils import OperationalError, ProgrammingError
from django.utils.timezone import utc
from EvalData.models import Market, Metadata, DirectAssessmentTask, \
  DirectAssessmentResult, TextPair, MultiModalAssessmentTask, \
  MultiModalAssessmentResult, TextPairWithImage


INFO_MSG = 'INFO: '
WARNING_MSG = 'WARN: '

# pylint: disable=C0111,C0330
class Command(BaseCommand):
    help = 'Unlinks DirectAssessmentTask instances as needed'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        _msg = '\n[{0}]\n\n'.format(path.basename(__file__))
        self.stdout.write(_msg)
        self.stdout.write('\n[INIT]\n\n')

        active_tasks = DirectAssessmentTask.objects.filter(
          activated=True
        )

        user_instances = {}
        for active_task in active_tasks:
            annotators = list(active_task.evaldata_directassessmentresult_task.values_list('createdBy__id', flat=True))
            for unique_annotator in set(annotators):
                if annotators.count(unique_annotator) >= 100:
                    if unique_annotator in user_instances:
                        user = user_instances[unique_annotator]

                    else:
                        user = User.objects.get(pk=unique_annotator)
                        user_instances[unique_annotator] = user

                    if not active_task.assignedTo.filter(id=unique_annotator).exists():
                        print("Adding user {0} to task {1} due to annotation count {2}".format(
                          user.username, active_task.id, annotators.count(unique_annotator)
                        ))
                        active_task.assignedTo.add(user)
                        active_task.save()

            assigned_users = active_task.assignedTo.all()
            for assigned_user in assigned_users:
                completed_annotations = active_task.evaldata_directassessmentresult_task.filter(
                  createdBy=assigned_user
                ).count()

                if completed_annotations >= 100:
                    continue

                last_user_annotation = DirectAssessmentResult.objects.filter(
                  createdBy=assigned_user,
                ).order_by(
                  '-dateCreated'
                ).first()

                print("\nactive task ID:", active_task.id, active_task.items.first().metadata.market)
                print(assigned_user.username)
                print(completed_annotations)

                if last_user_annotation is None:
                    active_task.assignedTo.remove(assigned_user)
                    print("no last user annotation, removing user")
                    continue

                print(assigned_user, last_user_annotation.dateCreated)

                utc_now = datetime.utcnow().replace(tzinfo=utc)
                delta = utc_now-last_user_annotation.dateCreated
                if delta > timedelta(hours=1):
                    active_task.assignedTo.remove(assigned_user)
                    print("time delta > 1h, removing user")
                    print(delta)
                    continue

                results_for_current_task = DirectAssessmentResult.objects.filter(
                  createdBy=assigned_user,
                  task=active_task
                ).count()

                if results_for_current_task == 0:
                    active_task.assignedTo.remove(assigned_user)
                    print("no results for current task, removing user")

        self.stdout.write('\n[DONE]\n\n')

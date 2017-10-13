"""
Appraise evaluation framework
"""
# pylint: disable=W0611
from datetime import datetime
from os import path
from django.contrib.auth.models import User

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q
from django.db.utils import OperationalError, ProgrammingError
from EvalData.models import Market, Metadata, DirectAssessmentTask, \
  DirectAssessmentResult, TextPair, MultiModalAssessmentTask, \
  MultiModalAssessmentResult, TextPairWithImage


INFO_MSG = 'INFO: '
WARNING_MSG = 'WARN: '

# pylint: disable=C0111,C0330
class Command(BaseCommand):
    help = 'Updates object instances required for EvalData app'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        _msg = '\n[{0}]\n\n'.format(path.basename(__file__))
        self.stdout.write(_msg)
        self.stdout.write('\n[INIT]\n\n')

        # News Task language pairs
        news_task_languages = (
          'ces', 'deu', 'fin', 'lav', 'rus', 'trk', 'zho'
        )
        news_task_pairs = [(x, 'eng') for x in news_task_languages] \
          + [('eng', x) for x in news_task_languages]

        # Find super user
        superusers = User.objects.filter(is_superuser=True)
        if not superusers.exists():
            _msg = 'Failure to identify superuser'
            self.stdout.write(_msg)
            return

        # Ensure that all Market and Metadata instances exist.
        for source, target in news_task_pairs:
            try:
                # Create NewsTask Market instance, if needed
                market = Market.objects.filter(
                  sourceLanguageCode=source,
                  targetLanguageCode=target,
                  domainName='NewsTask'
                )

                if not market.exists():
                    new_market = Market(
                      sourceLanguageCode=source,
                      targetLanguageCode=target,
                      domainName='NewsTask',
                      createdBy=superusers[0]
                    )
                    new_market.save()
                    market = new_market

                else:
                    market = market[0]

                metadata = Metadata.objects.filter(market=market)

                if not metadata.exists():
                    new_metadata = Metadata(
                      market=market,
                      corpusName='NewsTest2017',
                      versionInfo='1.0',
                      source='official',
                      createdBy=superusers[0]
                    )
                    new_metadata.save()

            except (OperationalError, ProgrammingError):
                _msg = 'Failure processing source={0}, target={1}'.format(
                  source, target
                )

            finally:
                _msg = 'Success processing source={0}, target={1}'.format(
                  source, target
                )

            self.stdout.write(_msg)

#        tr1 = datetime.now()
#        active_items = TextPair.objects.filter(activated=True)
#        print(active_items.count())
#        active_items.update(activated=False)
#        tr2 = datetime.now()
#        print('reset', tr2-tr1)

        t1 = datetime.now()
        results = DirectAssessmentResult.objects.filter(completed=False)
        results.update(activated=False, completed=True)
        t2 = datetime.now()
        print('Processed DirectAssessmentResult instances', t2-t1)

        bad_results = DirectAssessmentResult.objects.filter(
          Q(item=None) | Q(task=None)
        )
        print('Identified bad DirectAssessmentResult instances', bad_results.count())

        # Check which DirectAssessmentTask instances can be activated.
        #
        # Iterate over all tasks
        # If completed_items >= 100, complete task
        # Otherwise, if campagin active, activate items and task
        activated_items = 0
        completed_tasks = 0

        tasks_to_complete = []
        tasks_to_activate = []
        items_to_activate = []

        t1 = datetime.now()
        task_data = DirectAssessmentTask.objects.values(
          'id', 'activated', 'completed', 'requiredAnnotations'
        )
        task_data = task_data.annotate(
          results=Count('evaldata_directassessmentresults')
        )
        for task in task_data:
            if task['results'] >= 100 * task['requiredAnnotations']:
                if task['activated']:
                    tasks_to_complete.append(task['id'])
                    completed_tasks += 1

            elif task['completed']:
                tasks_to_activate.append(task['id'])

        ttc = DirectAssessmentTask.objects.filter(id__in=tasks_to_complete)
        ttc.update(activated=False, completed=True)

        tta = DirectAssessmentTask.objects.filter(id__in=tasks_to_activate)
        tta.update(activated=True, completed=False)

        t2 = datetime.now()
        print('Processed DirectAssessmentTask instances', t2-t1)

        item_data = TextPair.objects.filter(
          evaldata_directassessmenttasks__campaign__activated=True,
          activated=False
        )
        item_data.update(activated=True)

        t3 = datetime.now()
        print('Processed TextPair instances', t3-t2)

        task_ids = DirectAssessmentTask.objects.filter(campaign__activated=True)
        task_ids.update(activated=True)

        t4 = datetime.now()
        print('Processed related DirectAssessmentTask instances', t4-t3)

        # Metrics Task language pairs
        metrics_task_languages = (
          'ces', 'deu', 'fin', 'lav', 'trk', 'zho'
        )
        metrics_task_pairs = [('eng', x) for x in metrics_task_languages]

        # Ensure that all Market and Metadata instances exist.
        for source, target in metrics_task_pairs:
            try:
                # Create MetricsTask Market instance, if needed
                market = Market.objects.filter(
                  sourceLanguageCode=source,
                  targetLanguageCode=target,
                  domainName='MetricsTask'
                )

                if not market.exists():
                    new_market = Market(
                      sourceLanguageCode=source,
                      targetLanguageCode=target,
                      domainName='MetricsTask',
                      createdBy=superusers[0]
                    )
                    new_market.save()
                    market = new_market

                else:
                    market = market[0]

                metadata = Metadata.objects.filter(market=market)

                if not metadata.exists():
                    new_metadata = Metadata(
                      market=market,
                      corpusName='MetricsTest2017',
                      versionInfo='1.0',
                      source='official',
                      createdBy=superusers[0]
                    )
                    new_metadata.save()

            except (OperationalError, ProgrammingError):
                _msg = 'Failure processing source={0}, target={1}'.format(
                  source, target
                )

            finally:
                _msg = 'Success processing source={0}, target={1}'.format(
                  source, target
                )

            self.stdout.write(_msg)


        # MultiModal Task language pairs
        multimodal_task_languages = (
          'deu', 'fra'
        )
        multimodal_task_pairs = [('eng', x) for x in multimodal_task_languages]

        # Ensure that all Market and Metadata instances exist.
        for source, target in multimodal_task_pairs:
            try:
                # Create MultiModalTask Market instance, if needed
                market = Market.objects.filter(
                  sourceLanguageCode=source,
                  targetLanguageCode=target,
                  domainName='MultiModalTask'
                )

                if not market.exists():
                    new_market = Market(
                      sourceLanguageCode=source,
                      targetLanguageCode=target,
                      domainName='MultiModalTask',
                      createdBy=superusers[0]
                    )
                    new_market.save()
                    market = new_market

                else:
                    market = market[0]

                metadata = Metadata.objects.filter(market=market)

                if not metadata.exists():
                    new_metadata = Metadata(
                      market=market,
                      corpusName='MultiModalTest2017',
                      versionInfo='1.0',
                      source='official',
                      createdBy=superusers[0]
                    )
                    new_metadata.save()

            except (OperationalError, ProgrammingError):
                _msg = 'Failure processing source={0}, target={1}'.format(
                  source, target
                )

            finally:
                _msg = 'Success processing source={0}, target={1}'.format(
                  source, target
                )

            self.stdout.write(_msg)

        t1 = datetime.now()
        task_data = MultiModalAssessmentTask.objects.values(
          'id', 'activated', 'completed', 'requiredAnnotations'
        )
        task_data = task_data.annotate(
          results=Count('evaldata_multimodalassessmentresults')
        )
        for task in task_data:
            if task['results'] >= 100 * task['requiredAnnotations']:
                if task['activated']:
                    tasks_to_complete.append(task['id'])
                    completed_tasks += 1

            elif task['completed']:
                tasks_to_activate.append(task['id'])

        ttc = MultiModalAssessmentTask.objects.filter(id__in=tasks_to_complete)
        ttc.update(activated=False, completed=True)

        tta = MultiModalAssessmentTask.objects.filter(id__in=tasks_to_activate)
        tta.update(activated=True, completed=False)

        t2 = datetime.now()
        print('Processed MultiModalAssessmentTask instances', t2-t1)

        item_data = TextPairWithImage.objects.filter(
          evaldata_multimodalassessmenttasks__campaign__activated=True,
          activated=False
        )
        item_data.update(activated=True)

        t3 = datetime.now()
        print('Processed TextPairWithImage instances', t3-t2)

        task_ids = MultiModalAssessmentTask.objects.filter(campaign__activated=True)
        task_ids.update(activated=True)

        t4 = datetime.now()
        print('Processed related MultiModalAssessmentTask instances', t4-t3)

        # Appen language pairs
        appen_languages = (
          'ara', 'deu', 'spa', 'fra', 'ita', 'jpn', 'kor', 'por', 'rus', 'zho',
          'cat', 'swe', 'nob', 'dan', 'trk', 'ces', 'nld', 'plk'
        )
        appen_pairs = [(x, 'eng') for x in appen_languages] \
          + [('eng', x) for x in appen_languages]

        # Ensure that all Market and Metadata instances exist.
        for source, target in appen_pairs:
            try:
                # Create NewsTask Market instance, if needed
                market = Market.objects.filter(
                  sourceLanguageCode=source,
                  targetLanguageCode=target,
                  domainName='AppenFY17'
                )

                if not market.exists():
                    new_market = Market(
                      sourceLanguageCode=source,
                      targetLanguageCode=target,
                      domainName='AppenFY17',
                      createdBy=superusers[0]
                    )
                    new_market.save()
                    market = new_market

                else:
                    market = market[0]

                metadata = Metadata.objects.filter(market=market)

                if not metadata.exists():
                    new_metadata = Metadata(
                      market=market,
                      corpusName='AppenFY17',
                      versionInfo='1.0',
                      source='official',
                      createdBy=superusers[0]
                    )
                    new_metadata.save()

            except (OperationalError, ProgrammingError):
                _msg = 'Failure processing source={0}, target={1}'.format(
                  source, target
                )

            finally:
                _msg = 'Success processing source={0}, target={1}'.format(
                  source, target
                )

            self.stdout.write(_msg)

        # Appen language pairs
        appen_languages = (
          'ara', 'deu', 'spa', 'fra', 'ita', 'por', 'rus', 'zho'
        )
        appen_pairs = [(x, 'eng') for x in appen_languages] \
          + [('eng', x) for x in appen_languages]

        # Ensure that all Market and Metadata instances exist.
        for source, target in appen_pairs:
            try:
                # Create NewsTask Market instance, if needed
                market = Market.objects.filter(
                  sourceLanguageCode=source,
                  targetLanguageCode=target,
                  domainName='AppenFY18'
                )

                if not market.exists():
                    new_market = Market(
                      sourceLanguageCode=source,
                      targetLanguageCode=target,
                      domainName='AppenFY18',
                      createdBy=superusers[0]
                    )
                    new_market.save()
                    market = new_market

                else:
                    market = market[0]

                metadata = Metadata.objects.filter(market=market)

                if not metadata.exists():
                    new_metadata = Metadata(
                      market=market,
                      corpusName='AppenFY18',
                      versionInfo='1.0',
                      source='official',
                      createdBy=superusers[0]
                    )
                    new_metadata.save()

            except (OperationalError, ProgrammingError):
                _msg = 'Failure processing source={0}, target={1}'.format(
                  source, target
                )

            finally:
                _msg = 'Success processing source={0}, target={1}'.format(
                  source, target
                )

            self.stdout.write(_msg)

        self.stdout.write('\n[DONE]\n\n')

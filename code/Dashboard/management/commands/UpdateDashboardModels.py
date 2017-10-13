"""
Appraise evaluation framework
"""
# pylint: disable=W0611
from os import path
from django.contrib.auth.models import Group

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError
from Dashboard.models import LANGUAGE_CODES_AND_NAMES


INFO_MSG = 'INFO: '
WARNING_MSG = 'WARN: '

# pylint: disable=C0111,C0330
class Command(BaseCommand):
    help = 'Updates object instances required for Dashboard app'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        _msg = '\n[{0}]\n\n'.format(path.basename(__file__))
        self.stdout.write(_msg)
        self.stdout.write('\n[INIT]\n\n')

        # Ensure that all languages have a corresponding group.
        for code in LANGUAGE_CODES_AND_NAMES:
            try:
                if not Group.objects.filter(name=code).exists():
                    new_language_group = Group(name=code)
                    new_language_group.save()

            except (OperationalError, ProgrammingError):
                _msg = 'Failure processing language code={0}'.format(code)

            finally:
                _msg = 'Success processing language code={0}'.format(code)

            self.stdout.write(_msg)

        self.stdout.write('\n[DONE]\n\n')

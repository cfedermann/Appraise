"""
Appraise evaluation framework
"""
# pylint: disable=W0611
from collections import defaultdict, OrderedDict
from datetime import datetime
from glob import iglob
from os import makedirs, path
from random import seed, shuffle
from shutil import copyfile
from traceback import format_exc
from django.core.management.base import BaseCommand, CommandError

INFO_MSG = 'INFO: '

EXTENSION_FOR_BAD_FILES = 'bad'
EXTENSION_FOR_IDS_FILES = 'ids'

# pylint: disable=C0111
class Command(BaseCommand):
    help = 'Creates ids files'

    # pylint: disable=C0330
    def add_arguments(self, parser):
        parser.add_argument(
          'source_path', type=str,
          help='Path to source text folder'
        )
        parser.add_argument(
          'target_path', type=str,
          help='Path to bad reference text folder'
        )
        parser.add_argument(
          '--filter-expr', type=str, default='*',
          help='Filter expression for file names'
        )
        parser.add_argument(
          '--unicode', action='store_true',
          help='Expects text files in Unicode encoding'
        )

    def handle(self, *args, **options):
        # Initialize random number generator
        source_path = options['source_path']
        target_path = options['target_path']
        filter_expr = options['filter_expr']
        unicode_enc = options['unicode']

        _msg = '\n[{0}]\n\n'.format(path.basename(__file__))
        self.stdout.write(_msg)

        self.stdout.write('source_path: {0}'.format(source_path))
        self.stdout.write('target_path: {0}'.format(target_path))
        self.stdout.write('filter_expr: {0}'.format(filter_expr))

        self.stdout.write('\n[INIT]\n\n')

        if not path.exists(target_path):
            try:
                _msg = '{0}Creating target path {1} ... '.format(
                  INFO_MSG, target_path
                )
                self.stdout.write(_msg, ending='')
                makedirs(target_path)
                self.stdout.write('OK')

            # pylint: disable=W0702
            except:
                self.stdout.write('FAIL')
                self.stdout.write(format_exc())

        source_glob = '{0}{1}{2}'.format(source_path, path.sep, filter_expr)
        for source_file in iglob(source_glob):
            # Check if we are dealing with an .ids file here and skip those
            if source_file.endswith(EXTENSION_FOR_IDS_FILES):
                continue

            _msg = '{0}Creating ids file for source file {1} ... '.format(
              INFO_MSG, path.basename(source_file)
            )
            self.stdout.write(_msg, ending='')

            try:
                # Compute target file path, which is a copy of the source file
                target_file = Command._create_target_file_name(
                  source_file, target_path, path.splitext(source_file)[1].strip('.')
                )

                # If target file already exists, skip and continue
                if path.exists(target_file):
                    self.stdout.write('EXISTS')

                else:
                    copyfile(source_file, target_file)

                # If ids file already exists in source folder, copy to target
                # pylint: disable=W0101
                source_ids_file = Command._create_target_file_name(
                  source_file, source_path
                )
                target_ids_file = Command._create_target_file_name(
                  source_file, target_path
                )

                if path.exists(target_ids_file):
                    continue

                if path.exists(source_ids_file):
                    copyfile(source_ids_file, target_ids_file)

                else:
                    # Otherwise, process file, creating bad refs and ids file
                    encoding = 'utf16' if unicode_enc else 'utf8'
                    Command.create_ids_for_file(source_file, target_ids_file, encoding=encoding)

                self.stdout.write('OK')

            # pylint: disable=W0702
            except:
                self.stdout.write('FAIL')
                self.stdout.write(format_exc())

        self.stdout.write('\n[DONE]\n\n')


    @staticmethod
    def _create_target_file_name(source_file, target_path, file_ext=EXTENSION_FOR_IDS_FILES):
        # pylint: disable=W0612
        source_name, source_ext = path.splitext(path.basename(source_file))
        target_name = '{0}.{1}'.format(source_name, file_ext)
        target_file = path.join(target_path, target_name)
        return target_file

    @staticmethod
    def create_ids_for_file(source_file, target_file, encoding='utf8'):
        with open(source_file, encoding=encoding) as input_file:
            with open(target_file, mode='w', encoding=encoding) as output_file:
                segment_id = 1
                # pylint: disable=W0612
                for current_line in input_file:
                    output_file.write(str(segment_id))
                    output_file.write('\r\n')
                    segment_id += 1

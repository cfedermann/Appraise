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
    help = 'Creates fake bad references data'

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
          '--random-seed', type=int,
          help='Random generator seed value'
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
        random_seed = options['random_seed'] \
          if options['random_seed'] is not None \
          else int(datetime.now().timestamp()*10**6)
        filter_expr = options['filter_expr']
        unicode_enc = options['unicode']

        _msg = '\n[{0}]\n\n'.format(path.basename(__file__))
        self.stdout.write(_msg)

        self.stdout.write('source_path: {0}'.format(source_path))
        self.stdout.write('target_path: {0}'.format(target_path))
        self.stdout.write('random_seed: {0}'.format(random_seed))
        self.stdout.write('filter_expr: {0}'.format(filter_expr))

        self.stdout.write('\n[INIT]\n\n')

        seed(random_seed)
        _msg = '{0}Seeded random number generator with seed={1}'.format(
          INFO_MSG, random_seed
        )
        self.stdout.write(_msg)

        if not path.exists(target_path):
            try:
                _msg = '{0}Creating target path {1} ... '.format(
                  INFO_MSG, target_path
                )
                self.stdout.write(_msg, ending='')
                makedirs(target_path)
                self.stdout.write('OK')

                # Write random number generator seed value to file.
                seed_value_file = path.join(target_path, "seed_value.txt")
                with open(seed_value_file, mode='w') as output_file:
                    output_file.write('{0}\n'.format(random_seed))

            # pylint: disable=W0702
            except:
                self.stdout.write('FAIL')
                self.stdout.write(format_exc())

        source_glob = '{0}{1}{2}'.format(source_path, path.sep, filter_expr)
        for source_file in iglob(source_glob):
            # Check if we are dealing with an .ids file here and skip those
            if source_file.endswith(EXTENSION_FOR_IDS_FILES) \
              or source_file.endswith(EXTENSION_FOR_BAD_FILES):
                continue

            _msg = '{0}Creating bad reference for source file {1} ... '.format(
              INFO_MSG, path.basename(source_file)
            )
            self.stdout.write(_msg, ending='')

            try:
                # Compute target file path
                target_file = Command._create_target_file_name(
                  source_file, target_path
                )

                # If target file already exists, skip and continue
                if path.exists(target_file):
                    self.stdout.write('EXISTS')
                    continue

                # If ids file already exists in source folder, copy to target
                source_ids_file = Command._create_target_file_name(
                  source_file, source_path, EXTENSION_FOR_IDS_FILES
                )
                if path.exists(source_ids_file):
                    target_ids_file = Command._create_target_file_name(
                      source_file, target_path, EXTENSION_FOR_IDS_FILES
                    )
                    copyfile(source_ids_file, target_ids_file)

                # Otherwise, process file, creating bad refs and ids file
                encoding = 'utf16' if unicode_enc else 'utf8'
                Command.create_bad_refs_for_file(source_file, target_file, encoding)
                self.stdout.write('OK')

            # pylint: disable=W0702
            except:
                self.stdout.write('FAIL')
                self.stdout.write(format_exc())

        self.stdout.write('\n[DONE]\n\n')


    @staticmethod
    def _create_target_file_name(source_file, target_path, file_ext=EXTENSION_FOR_BAD_FILES):
        # pylint: disable=W0612
        source_name, source_ext = path.splitext(path.basename(source_file))
        target_name = '{0}.{1}'.format(source_name, file_ext)
        target_file = path.join(target_path, target_name)
        return target_file

    @staticmethod
    def create_bad_refs_for_file(source_file, target_file, encoding='utf8'):
        segment_ids = []
        with open(source_file, encoding=encoding) as input_file:
            with open(target_file, mode='w', encoding=encoding) as output_file:
                segment_id = 1
                for current_line in input_file:
                    segment_ids.append(segment_id)
                    bad_ref = Command.create_bad_ref_for_segment(current_line.strip())
                    output_file.write(bad_ref)
                    output_file.write('\n')
                    segment_id += 1

        target_ids_file = Command._create_target_file_name(
          source_file, path.dirname(target_file), EXTENSION_FOR_IDS_FILES
        )
        if not path.exists(target_ids_file):
            with open(target_ids_file, mode='w', encoding='utf8') as ids_file:
                ids_file.writelines(['{0}\n'.format(x) for x in segment_ids])


    @staticmethod
    def create_bad_ref_for_segment(segment_text):
        tokens = segment_text.split()
        ids = list(range(len(tokens)))
        shuffle(ids)

        if len(tokens) < 3:
            tokens.append('BAD')
            tokens.append('REF')

        else:
            tokens[ids[0]] = 'BAD'
            tokens[ids[1]] = 'REF'
            tokens[ids[2]] = tokens[ids[2]].capitalize()

        return ' '.join(tokens)

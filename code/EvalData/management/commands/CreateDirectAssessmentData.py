"""
Appraise evaluation framework
"""
# pylint: disable=W0611
import json
from django.core.management.base import BaseCommand, CommandError
from collections import defaultdict, OrderedDict
from math import floor
from os.path import basename
from random import seed, shuffle

# pylint: disable=C0111
class Command(BaseCommand):
    help = 'Creates JSON file containing DirectAssessmentTask data'

    # pylint: disable=C0330
    def add_arguments(self, parser):
        parser.add_argument(
          'batch_size', type=int,
          help='Total batch size'
        )
        parser.add_argument(
          'source_language', type=str,
          help='Source language code'
        )
        parser.add_argument(
          'target_language', type=str,
          help='Target language code'
        )
        parser.add_argument(
          'source_file', type=str,
          help='Path to source text file'
        )
        parser.add_argument(
          'reference_file', type=str,
          help='Path to reference text file'
        )
        parser.add_argument(
          'systems_path', type=str,
          help='Path to systems text folder'
        )
        parser.add_argument(
          'output_json_file', type=str,
          help='Path to JSON output file'
        )
        parser.add_argument(
          '--block-definition', type=str, default="7:1:1:1",
          help='Defines (candidates, redundant, reference, bad reference) per block'
        )
        parser.add_argument(
          '--required-annotations', type=int, default=1,
          help='Specifies required annotations per batch (default: 1)'
        )
        parser.add_argument(
          '--random-seed', type=int, # required=False,
          help='Random generator seed value'
        )
        parser.add_argument(
          '--randomize', action='store_false',
          help='Randomize extracted work items'
        )
        parser.add_argument(
          '--batch-no', type=int, default=1,
          help='Specifies desired batch no (default: 1)'
        )
        parser.add_argument(
          '--max-batches', type=int,
          help='Specifies max number of batches to create'
        )
        parser.add_argument(
          '--all-batches', action='store_true',
          help='Produces all possible batches at once'
        )
        parser.add_argument(
          '--source-based', action='store_true',
          help='Creates source-based work items'
        )
        parser.add_argument(
          '--unicode', action='store_true',
          help='Expects text files in Unicode encoding'
        )
        parser.add_argument(
          '--local-src', action='store_true',
          help='Loads source text from local .src files'
        )
        parser.add_argument(
          '--local-ref', action='store_true',
          help='Loads reference text from local .ref files'
        )
        parser.add_argument(
          '--create-ids', action='store_true',
          help='Creates segment ids without local .ids files'
        )
        # TODO: add optional parameters to set source, reference and system IDs

        # TODO: add exclude argument which prevents creation of redundant data?

###
#
# Fake BAD REF generation
# Simply insert "BAD" and "REF" somewhere into the reference text
#
# We end up having three folders:
# 1) for candidate translations
# 2) for bad references
# 3) for segment ids
#
# We should think about using one folder, allowing two special files:
# - $fileName.badRef
# - $fileName.segmentIds
#
# We operate on k files, one per submitted system.
#
# When sampling data, we need to read in candidate translations in a stable order.
# This works by creating a sorted list of file names and then shuffling it once.
# Given the random seed value, this should be reproducible.
#
# For this to work, we have to ALWAYS seed the RNG. By default, we should use msec after midnight.
# This also means that we have to expose/print the seed value every time so that users know it.
#
# Once the random order of file names has been created, we read in candidate translations.
# For each, we compute the MD5 hash of the .strip()ed Unicode text, preserving case information.
# The MD5 hash will act as unique key for the segment text. If multiple segments share the same
# segment text, they will end up being mapped to the same key. In this case, the only difference
# is (potentially) in the bad reference text. This should be identical for identical candidate
# translations but there is no hard guarantee for this. Hence, we agree to always use the bad
# reference text from the first system being mapped to the respective MD5 key. The segment ID
# will always be the same and hence is not an issue. Should the segment ID not match, we have
# an inconsistent state and should abort sampling. It is fine if files do not align wrt. the
# number of translations contained within each of the files as long as identical candidate text
# has identical segment IDs. There is a potential problem if multiple translations map to the
# different source segments, thus ending up with different IDs. I have no idea what we can do
# about this case.
#
# Number of blocks = d
# distance for checks = (d/2)
# default number d = 10
#
# Block defined as 10 items
# Randomly ordered
# 7 candidate translations
# 2 reference translations
# 1 bad reference (specific to candiate translation)
#
# 7,2,1 specification
# Can be different for other scenarios
# --block-spec="7S2R1B"
#
# Question for Yvette:
#
# DO BAD REFERENCES HAVE TO BE IDENTICAL FOR IDENTICAL SYSTEM TRANSLATIONS?
#
# Requirement for Christian:
#
# I WANT THE SAMPLING TO BE REPRODUCIBLE GIVEN THE SAME RANDOM SEED VALUE
#
###

    def handle(self, *args, **options):
        # Initialize random number generator
        # Extract batch size number of pairs, randomizing order if requested
        # Serialize pairs into JSON format
        # Write out JSON output file

        batch_size = options['batch_size']
        unicode_enc = options['unicode']
        use_local_src = options['local_src']
        use_local_ref = options['local_ref']
        create_ids = options['create_ids']

        block_size = 10
        block_annotations = 7
        block_redundants = 1
        block_references = 1
        block_badrefs = 1

        # IF BLOCK DEF IS GIVEN, DO SOMETHING WITH IT
        if options['block_definition'] is not None:
            print("WOOHOO") 

        if (batch_size % block_size) > 0:
            self.stdout.write('Batch size needs to be divisible by block size!')
            return
        
        # CHECK THAT WE END UP WITH EVEN NUMBER OF BLOCKS

        print('We will create {0} blocks'.format(int(batch_size / block_size)))

        # TODO: add parameter to set encoding
        # TODO: need to use OrderedDict to preserve segment IDs' order!
        encoding = 'utf16' if unicode_enc else 'utf8'

        source_file = []
        if not use_local_src:
            source_file = Command._load_text_from_file(options['source_file'], encoding)
            print('Loaded {0} source segments'.format(len(source_file.keys())))

        reference_file = []
        if not use_local_ref:
            reference_file = Command._load_text_from_file(options['reference_file'], encoding)
            print('Loaded {0} reference segments'.format(len(reference_file.keys())))

        systems_files = []
        systems_path = options['systems_path']
        from glob import iglob
        import os.path
        for system_file in iglob('{0}{1}{2}'.format(systems_path, os.path.sep, "*.txt")):
            systems_files.append(system_file)

        random_seed_value = 123456

        systems_files.sort()
        seed(random_seed_value)
        shuffle(systems_files)
        # ADD RANDOMIZED SHUFFLING HERE?

        import hashlib
        hashed_text = {}

        for system_path in systems_files:
            system_txt = Command._load_text_from_file(system_path, encoding)
            system_bad = Command._load_text_from_file(system_path.replace('.txt', '.bad'), encoding)

            if not create_ids:
                system_ids = Command._load_text_from_file(system_path.replace('.txt', '.ids'), encoding)
            else:
                system_ids = [x+1 for x in range(len(system_txt))]
            # BASICALLY: add support for local system_src and system_ref files here.
            #   If such files are present, this will overwrite the global src/ref values.
            #   However, this does not fully resolve the issue as we still have to give
            #   a source text file, while is assumed to be shared...
            #
            # IN A SENSE, using these local files makes better sense. It is wasteful, though.
            #   MAYBE, it is better to simply generate a simple JSON config file?!
            local_src = []
            local_ref = []

            if use_local_src:
                local_src_path = system_path.replace('.txt', '.src')
                if os.path.exists(local_src_path):
                    local_src = Command._load_text_from_file(local_src_path, encoding)

            if use_local_ref:
                local_ref_path = system_path.replace('.txt', '.ref')
                if os.path.exists(local_ref_path):
                    local_ref = Command._load_text_from_file(local_src_path, encoding)

            for segment_id, segment_text in system_txt.items():
                md5hash = hashlib.new('md5', segment_text.encode(encoding)).hexdigest()
                _src = local_src[segment_id] if use_local_src else source_file[segment_id]
                _ref = local_src[segment_id] if use_local_ref else reference_file[segment_id]
                if not md5hash in hashed_text.keys():
                    hashed_text[md5hash] = {
                      'segment_id': segment_id,
                      'segment_text': segment_text,
                      'segment_bad': system_bad[segment_id],
                      'segment_ref': _ref,
                      'segment_src': _src,
                      'systems': [os.path.basename(system_path)]
                    }
                else:
                    hashed_text[md5hash]['systems'].append(os.path.basename(system_path))

            print('Loaded {0} system {1} segments'.format(
              len(system_txt.keys()), os.path.basename(system_path))
            )

        all_keys = list(hashed_text.keys())
        all_keys.sort()
        shuffle(all_keys)

        items_per_batch = 10 * 7

        missing_items = items_per_batch - len(all_keys) % items_per_batch
        print('Missing items is {0}/{1}'.format(missing_items, items_per_batch))

        all_keys.extend(all_keys[0:missing_items])
        print('Added {0} missing items rotating keys'.format(missing_items))

        total_batches = int(floor(len(all_keys) / items_per_batch))
        print('Total number of batches is {0}'.format(total_batches))

        batch_no = options['batch_no']
        max_batches = options['max_batches']
        all_batches = options['all_batches']
        source_based = options['source_based']

        # If we don't produce all batches, our batch_id will be batch_no-1.
        # This is because batch numbers are one-based, ids zero-indexed.
        #
        # If we produce all batches, we just use range(total_batches).
        # This implicitly gives us zero-indexed ids already.
        batch_nos = [batch_no-1] if not all_batches \
          else list(range(total_batches))
        if max_batches:
            batch_nos = batch_nos[:max_batches]

        json_data = []
        for batch_id in batch_nos: # range(batch_no):
            block_data = []
            block_offset = batch_id * 10 * 7

            num_blocks = int(batch_size/block_size)
            for block_id in range(num_blocks):
                # Human readable ids are one-based, hence +1
                print('Creating batch {0:05}/{1:05}, block {2:02}'.format(
                  batch_id+1, total_batches, block_id+1)
                )

                # Get 7 random system outputs
                block_start = block_offset + 7 * (block_id)
                block_end = block_start + 7
                block_hashes = all_keys[block_start:block_end]

                current_block = {
                  'systems': block_hashes
                }

                block_data.append(current_block)

            # Compute redundant, reference, bad reference bits
            for block_id in range(num_blocks):
                check_id = int((block_id + (num_blocks/2)) % num_blocks)
                # Human readable ids are one-based, hence +1
                print('Add checks for batch {0:05}/{1:05}, ' \
                  'block {2:02} to block {3:02}'.format(
                    batch_id+1, total_batches, check_id+1, block_id+1
                  )
                )

                check_systems = block_data[check_id]['systems']
                check_systems.sort()
                shuffle(check_systems)

                block_data[block_id]['redundant'] = check_systems[0]
                block_data[block_id]['reference'] = check_systems[1]
                block_data[block_id]['badref'] = check_systems[2]

            # Direct assessment is reference-based for WMT17
            if source_based:
                sourceID = 'LOCAL_SRC' if use_local_src else basename(options['source_file'])
            else:
                sourceID = 'LOCAL_REF' if use_local_ref else basename(options['reference_file'])

            # Remember, batch numbers are one-based
            taskData = OrderedDict({
              'batchNo': batch_id+1,
              'batchSize': options['batch_size'],
              'sourceLanguage': options['source_language'],
              'targetLanguage': options['target_language'],
              'requiredAnnotations': options['required_annotations'],
              'randomSeed': random_seed_value
            })
            itemsData = []
            _item = 0

            for block_id in range(num_blocks):
                all_items = [(x, 'TGT') for x in block_data[block_id]['systems']]
                all_items.append((block_data[block_id]['redundant'], 'CHK'))
                all_items.append((block_data[block_id]['reference'], 'REF'))
                all_items.append((block_data[block_id]['badref'], 'BAD'))
                shuffle(all_items)

                for current_item, current_type in all_items:
                    item_data = hashed_text[current_item]

                    item_id = item_data['segment_id']
                    item_text = item_data['segment_text']
                    item_bad = item_data['segment_bad']
                    item_ref = item_data['segment_ref']
                    item_src = item_data['segment_src']
                    item_systems = item_data['systems']

                    targetID = '+'.join(item_systems)
                    targetText = item_text
                    if current_type == 'REF':
                        targetID = basename(options['reference_file'])
                        targetText = item_ref
                    elif current_item == 'BAD':
                        targetText = item_bad

                    obj = OrderedDict()
                    obj['_item'] = _item
                    obj['_block'] = block_id + (10 * batch_id)
                    obj['sourceID'] = sourceID
                    obj['sourceText'] = item_ref if not source_based else item_src
                    obj['targetID'] = targetID
                    obj['targetText'] = targetText
                    obj['itemID'] = item_id
                    obj['itemType'] = current_type

                    itemsData.append(obj)
                    _item += 1

            outputData = OrderedDict({
              'task': taskData,
              'items': itemsData
            })

            json_data.append(outputData)

        print(json.dumps(json_data, indent=2))
        json_data = json.dumps(json_data, indent=2)

        with open(options['output_json_file'], mode='w', encoding='utf8') as output_file:
            self.stdout.write('Creating {0} ... '.format(options['output_json_file']), ending='')
            output_file.write(str(json_data))
            self.stdout.write('OK')


    @staticmethod
    def _load_text_from_file(file_path, encoding='utf8'):
        segment_id = 0
        file_text = OrderedDict()

        with open(file_path, encoding=encoding) as input_file:
            for current_line in input_file:
                segment_id += 1
                file_text[segment_id] = current_line.strip()

        return file_text

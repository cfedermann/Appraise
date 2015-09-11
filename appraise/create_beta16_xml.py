#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import math
import random
import hashlib
import argparse
from random import shuffle

PARSER = argparse.ArgumentParser(description="Build evaluation task input file.")
PARSER.add_argument('-seed', type=int, default=None, help='random seed')
PARSER.add_argument("output", type=str, help="output file")
PARSER.add_argument("source", type=file, help="source language file")
PARSER.add_argument("reference", type=file, nargs="?", help="reference language file")
PARSER.add_argument("system", metavar="system", nargs="*", type=file, help="parallel files to compare")
PARSER.add_argument("-source", type=str, default="spa", dest="sourceLang", help="the source language")
PARSER.add_argument("-target", type=str, default="eng", dest="targetLang", help="the target language")
PARSER.add_argument("-numsegments", type=int, default=100, help="number of segments in the batch")
PARSER.add_argument('-maxlen', type=int, default=30, help='maximum source sentence length')
PARSER.add_argument("-ids-file", type=file, dest="idsfile", help="segment IDs file")

PARSER.add_argument("-id", type=str, default="none", help="ID name to use for the system name")
PARSER.add_argument("-tasksperhit", type=int, default=3, help="number of HITs in the batch")
PARSER.add_argument("-systemspertask", type=int, default=5, help="number of systems to rerank")
PARSER.add_argument("-redundancy", type=int, default=10, help="number of redundant HITs in the batch")
PARSER.add_argument('-no-sequential', dest='sequential', default=True, action='store_false', help='whether sentences within a HIT should be sequential')
PARSER.add_argument('-controls', type=str, default=None, dest="controlFile", help='file containing controls to use (implies -no-sequential)')
PARSER.add_argument('-control_prob', type=float, default=1.0, dest="control_prob", help='probability of inserting a control into a HIT')
PARSER.add_argument('-save', type=str, default=None, dest="saveDir", help='directory to save reduced corpora to')

def cleanup_translation(input_str):
    """
    Cleans a translation for identity comparison.

    Removes superfluous whitespace.
    """
    import re
    whitespace = re.compile('\s{2,}')
    cleaned_str = whitespace.sub(' ', input_str)
    return cleaned_str


def dump_system(system_file, lines):
    """
    Dump lines to file.
    """
    outfile = os.path.join(args.saveDir, os.path.basename(system_file))
    if not os.path.exists(outfile):
        sys.stderr.write('DUMPING TO %s\n' % (outfile))
        out = open(outfile, 'w')
        for line in lines:
            out.write(u'{0}\n'.format(line).encode('utf-8'))
        out.close()


if __name__ == "__main__":
    args = PARSER.parse_args()

    # Initialize random number generator with given seed
    if args.seed is not None:
        random.seed(args.seed)

    # Load source data
    source = []
    for line in args.source:
        source.append(line.decode("utf8").strip())

    # Load reference data
    reference = []
    if args.reference:
        for line in args.reference:
            reference.append(line.decode("utf8").strip())

    if len(reference) != len(source):
        sys.stderr.write('* FATAL: reference length (%d) != source length (%d)\n' % (len(source), len(reference)))
        sys.exit(1)

    valid_ids = []
    for line in args.idsfile:
        valid_ids.append(int(line))

    # Load systems data
    systems = []
    system_names = []
    if len(args.system):
        for i, system in enumerate(args.system):
            systems.append([])
            system_name = os.path.basename(system.name)
            system_names.append(system_name)
            for line in system:
                systems[i].append(line.decode("utf8").strip())

            if len(systems[i]) != len(source):
                sys.stderr.write('* FATAL: system %s length (%d) != source length (%d)\n' % (system_name, len(source), len(reference)))
                sys.exit(1)

    system_hashes = [hashlib.sha1(x).hexdigest() for x in system_names]

    # Make a list of all eligible sentences
    eligible = []
    for i in range(len(source)):
        if (len(source[i].split()) <= args.maxlen) and (i+1 in valid_ids):
            eligible.append(i)

    # Save corpora if requested and not already existing
    if args.saveDir is not None:
        if not os.path.exists(args.saveDir):
            os.makedirs(args.saveDir)
        dump_system(args.source.name, source)
        dump_system(args.reference.name, reference)
        for i,system in enumerate(args.system):
            dump_system(system.name, systems[i])
        dump_system('line_numbers', [x + 1 for x in eligible])

    shuffle(eligible)
    all_tasks = []

    # We need to avoid duplicate candidate translations.  To do so, we have to check
    # which systems have identical translations -- this may be different across tasks.
    # Hence, our random selection of system IDs might be different inside a HIT.
    #
    # To implement this, we loop over all sentence IDs.
    tasks = []

    for current_id in eligible:
        from collections import defaultdict
        unique_translations_to_system_ids_map = defaultdict(list)

        # Then we iterate over all systems and map unique translations to system IDs.
        for system_id in range(len(systems)):
            try:
                current_translation = cleanup_translation(systems[system_id][eligible[current_id]])
                unique_translations_to_system_ids_map[current_translation].append(system_id)
            except:
                continue

        # To randomize the selection of systems, we have to generate the list of unique translations.
        # Note that this may result in less than five translation candidates...
        deduped_system_ids = [x for x in unique_translations_to_system_ids_map.values()]
        deduped_system_indexes = range(len(deduped_system_ids))
        random.shuffle(deduped_system_indexes)
        # Don't constrain number of systems...
        #deduped_system_indexes = deduped_system_indexes[:args.systemspertask]

        deduped_system_names = []
        deduped_system_output = []
        for deduped_id in deduped_system_indexes:
            deduped_system_names.append(u','.join([system_names[system_id] for system_id in deduped_system_ids[deduped_id]]))
            system_id = deduped_system_ids[deduped_id][0]
            deduped_system_output.append(systems[system_id][eligible[current_id]])

        try:
            reference_text = reference[eligible[current_id]]
        except:
            continue

        for deduped_system_name, deduped_candidate_text in zip(deduped_system_names, deduped_system_output):
            tasks.append(
              u'<segment id="{0}" source-language="{1}" target-language="{2}">\n' \
              u'  <system-id>{3}</system-id>\n  <reference>{4}</reference>\n' \
              u'  <candidate>{5}</candidate>\n</segment>'.format(current_id,
                args.sourceLang, args.targetLang, deduped_system_name,
                reference_text, deduped_candidate_text)
            )

    result_xml = u'<segments>\n{0}\n</segments>'.format(u'\n'.join(tasks))

    out = open(args.output, 'w')
    out.write(result_xml.encode('utf-8'))
    out.close()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Project: Appraise evaluation system
 Author: Matt Post <post@cs.jhu.edu>

This script takes a set of parallel files (source, reference, and system translations) and writes
out the XML file used to setup the corresponding Appraise tasks for WMT reranking. It supports many
options, such as limiting the maximum length of a source sentence (-maxlen, default 30), inserting
controls (-controls file) with a certain probability (-control_prob, default 1.0, meaning every HIT
will have a control), and so on.

"""

import os
import sys
import math
import random
import hashlib
import argparse
from ranking_task import RankingTask,Control

PARSER = argparse.ArgumentParser(description="Build evaluation task input file.")
PARSER.add_argument("source", type=file, help="source language file")
PARSER.add_argument("reference", type=file, nargs="?", help="reference language file")
PARSER.add_argument("system", metavar="system", nargs="*", type=file, help="parallel files to compare")
PARSER.add_argument("-id", type=str, default="none", help="ID name to use for the system name")
PARSER.add_argument("-source", type=str, default="spa", dest="sourceLang", help="the source language")
PARSER.add_argument("-target", type=str, default="eng", dest="targetLang", help="the target language")
PARSER.add_argument("-numhits", type=int, default=100, help="number of HITs in the batch")
PARSER.add_argument("-tasksperhit", type=int, default=3, help="number of HITs in the batch")
PARSER.add_argument("-systemspertask", type=int, default=5, help="number of systems to rerank")
PARSER.add_argument("-redundancy", type=int, default=10, help="number of redundant HITs in the batch")
PARSER.add_argument('-maxlen', type=int, default=30, help='maximum source sentence length')
PARSER.add_argument('-seed', type=int, default=None, help='random seed')
PARSER.add_argument('-no-sequential', dest='sequential', default=True, action='store_false', help='whether sentences within a HIT should be sequential')
PARSER.add_argument('-controls', type=str, default=None, dest="controlFile", help='file containing controls to use (implies -no-sequential)')
PARSER.add_argument('-control_prob', type=float, default=1.0, dest="control_prob", help='probability of inserting a control into a HIT')
PARSER.add_argument('-save', type=str, default=None, dest="saveDir", help='directory to save reduced corpora to')

def cleanup_translation(input_str):
    """Cleans a translation for identity comparison.
    
    Removes punctuation, superfluous whitespace and ignores case.
    
    """
    import re
    punctuation = re.compile('[.,;:!?\'"\-«»<>&()\[\]]+', re.I)
    whitespace = re.compile('\s{2,}')
    cleaned_str = punctuation.sub(' ', input_str)
    cleaned_str = whitespace.sub(' ', cleaned_str)
    return cleaned_str.lower()

def random_from_range(range_max, num_draws, tuple_size = 3, sequential = True):
    """Returns a set of tuples (of size `size') of numbers, representing sentences to use in constructing a HIT. `range_max' is the number of sentences, `num_draws' is the number of HITs to create, `tuple_size' is the number of sentences in each HIT, and `sequential' indicates that we should draw sentences in block groups."""
    
    """Returns a set of 'num' unique integers from the range (0, max-1)."""

    blocks = []
    if sequential is True:
        num_blocks = int(math.ceil(1.0 * range_max / tuple_size))
        sentences = range(num_blocks)
        random.shuffle(sentences)
        blocks = [tuple(range(block, block + tuple_size)) for block in sentences]
    else:
        sentences = range(range_max)
        random.shuffle(sentences)

        blocks = [tuple([sentences.pop(random.randint(0, len(sentences) - 1)) for x in range(tuple_size)]) for x in range(num_draws)]

    return blocks

if __name__ == "__main__":
    args = PARSER.parse_args()

    # SANITY CHECKING AND DEPENDENT VARIABLE SETTING

    if args.seed is not None:
        random.seed(args.seed)

    num_unique_hits = args.numhits - args.redundancy

    controls = []
    if args.controlFile is not None:
        args.sequential = False

        controls = Control.load(args.controlFile)
#        print 'Read %d controls, keeping %d best' % (len(controls), args.numhits - args.redundancy)
        controls = controls[:args.numhits-args.redundancy]

        if len(controls) < num_unique_hits:
            sys.stderr.write('* WARNING: not enough controls (%d < %d)\n' % (len(controls), num_unique_hits))

    # BEGIN 

    source = []
    for line in args.source:
        source.append(line.decode("utf8").strip())
    
    reference = []
    if args.reference:
        for line in args.reference:
            reference.append(line.decode("utf8").strip())

    if len(reference) != len(source):
        sys.stderr.write('* FATAL: reference length (%d) != source length (%d)\n' % (len(source), len(reference)))
        sys.exit(1)

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
        if len(source[i].split()) <= args.maxlen:
            eligible.append(i)

    def dump_system(system_file, lines):
        outfile = os.path.join(args.saveDir, os.path.basename(system_file))
        if not os.path.exists(outfile):
            sys.stderr.write('DUMPING TO %s\n' % (outfile))
            out = open(outfile, 'w')
            for line in lines:
                out.write(u'{0}\n'.format(line).encode('utf-8'))
            out.close()

    # Save corpora if requested and not already existing
    if args.saveDir is not None:
        if not os.path.exists(args.saveDir):
            os.makedirs(args.saveDir)
        dump_system(args.source.name, source)
        dump_system(args.reference.name, reference)
        for i,system in enumerate(args.system):
            dump_system(system.name, systems[i])
        dump_system('line_numbers', [x + 1 for x in eligible])

    random_blocks = random_from_range(len(eligible), args.numhits - args.redundancy, tuple_size = args.tasksperhit, sequential = args.sequential)
    hits = []
    for sentnos_tuple in random_blocks:

        # We need to avoid duplicate candidate translations.  To do so, we have to check
        # which systems have identical translations -- this may be different across tasks.
        # Hence, our random selection of system IDs might be different inside a HIT.
        #
        # To implement this, we loop over all sentence IDs.
        tasks = []
        
        
        
        #if False:
        for current_id in sentnos_tuple:
            from collections import defaultdict
            unique_translations_to_system_ids_map = defaultdict(list)
            
            # Then we iterate over all systems and map unique translations to system IDs. 
            for system_id in range(len(systems)):
                current_translation = cleanup_translation(systems[system_id][eligible[current_id]])
                unique_translations_to_system_ids_map[current_translation].append(system_id)
            
            # To randomize the selection of systems, we have to generate the list of unique translations.
            # Note that this may result in less than five translation candidates... 
            deduped_system_ids = [x for x in unique_translations_to_system_ids_map.values()]
            deduped_system_indexes = range(len(deduped_system_ids))
            random.shuffle(deduped_system_indexes)
            deduped_system_indexes = deduped_system_indexes[:args.systemspertask]
            
            deduped_system_names = []
            deduped_system_output = []
            for deduped_id in deduped_system_indexes:
                deduped_system_names.append(u','.join([system_names[system_id] for system_id in deduped_system_ids[deduped_id]]))
                system_id = deduped_system_ids[deduped_id][0] 
                deduped_system_output.append(systems[system_id][eligible[current_id]])
            
            tasks.append(
              RankingTask(
                eligible[current_id] + 1,
                source[eligible[current_id]],
                reference[eligible[current_id]],
                deduped_system_names,
                deduped_system_output,
              )
            )

# Matt's old code
#
#        # Randomize the selection of systems
#        system_indexes = range(len(systems))
#        random.shuffle(system_indexes)
#        system_indexes = system_indexes[:args.systemspertask]
#
#        tasks = [RankingTask(eligible[id] + 1, source[eligible[id]], reference[eligible[id]], [system_names[sysid] for sysid in system_indexes], [systems[sysid][eligible[id]] for sysid in system_indexes]) for id in sentnos_tuple]
#
# end of Matt's old code

        # Randomly decided whether to randomly replace one of the tasks with a random control.  That
        # is, we roll a dice to see whether to insert a control (determined by
        # args.control_prob). If so, we randomly choose which HIT to replace, and then randomly
        # choose one of the remaining controls to put there.
        if len(controls):
            if random.random() < args.control_prob:
                tasks[random.randint(0, len(tasks)-1)] = controls.pop(random.randint(0,len(controls)-1))

        # sentnos_str = ",".join([`x.id` for x in tasks])
        sentnos_str = u"-1"
        hit  = u'  <hit block-id="{0}" source-language="{1}" target-language="{2}">'.format(sentnos_str, args.sourceLang, args.targetLang)
        hit += u''.join([task.xml() for task in tasks])
        hit += u'\n  </hit>'

        hits.append(hit)

    # Now create redundant HITs
    if args.redundancy > 0:
        numbers = random_from_range(len(hits), args.redundancy, tuple_size = 1, sequential = False)

        hits += [hits[x[0]] for x in numbers]

    result_xml = u'<hits>\n{0}\n</hits>'.format(u'\n'.join([hit for hit in hits]))
    
    out = open("test-outfile.txt", 'w')
    out.write(result_xml.encode('utf-8'))
    out.close()

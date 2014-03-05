#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Project: Appraise evaluation system Author: Matt Post <post@cs.jhu.edu>

This script allows you to visualize an individual ranking task against the researcher consensus.

"""

import os
import sys
import math
import random
import hashlib
import argparse
from collections import defaultdict
from csv import DictReader
from itertools import combinations
from ranking_task import RankingTask,Control

PARSER = argparse.ArgumentParser(description="Visualize a ranking task.")
PARSER.add_argument('-consensus', type=str, default=None, help='file containing results you trust')
PARSER.add_argument('-judge', type=str, default='researcher', help='prefix that judge IDs must match')

def read_file(filename, list):
    """Read in a file to an array."""
    for line in open(filename):
        list.append(line.rstrip())

def get_rankings(row):
    """Takes a DictReader row and computes all the rankings."""
    rankings = {}
    for pair in combinations(range(5),2):
        rank1 = int(row.get('system%drank' % (pair[0] + 1)))
        rank2 = int(row.get('system%drank' % (pair[1] + 1)))
        sys1 = row.get('system%dId' % (pair[0] + 1))
        sys2 = row.get('system%dId' % (pair[1] + 1))
        if rank1 < rank2:
            syspair = '%s < %s' % (sys1, sys2)
            rankings[syspair] = 1
        elif rank1 > rank2:
            syspair = '%s < %s' % (sys2, sys1)
            rankings[syspair] = 1

    return rankings

if __name__ == "__main__":
    args = PARSER.parse_args()

    LANGS = { 'Czech': 'cs',
              'Russian': 'ru',
              'German': 'de',
              'Spanish': 'es',
              'English': 'en',
              'French': 'fr' }

    # Read source, reference, and system sentences
    sources = defaultdict(dict)
    refs = {}
    systems = {}
    for pair in 'cs-en es-en fr-en de-en ru-en en-cs en-es en-fr en-de en-ru'.split(' '):
        source,target = pair.split('-')
        sources[pair] = []
        refs[pair] = []
        systems[pair] = defaultdict(list)
        dir = '/Users/post/expts/wmt13/data/maxlen30/%s' % (pair)
        read_file('%s/newstest2013-src.%s' % (dir, source), sources[pair])
        read_file('%s/newstest2013-ref.%s' % (dir, target), refs[pair])
        for system in os.listdir(dir):
            if system.startswith('newstest2013.%s' % (pair)):
                read_file('%s/%s' % (dir, system), systems[pair][system])

    # Read in the controls
    RANKINGS = {}
    if args.consensus is not None:
        # print >> sys.stderr, 'will read from', args.consensus
        for row in DictReader(open(args.consensus)):
            if row.get('srcIndex') is None:
                print >> sys.stderr, 'bad line', row
                continue
            if not row.get('judgeId').startswith(args.judge):
                continue
            sentno = int(row.get('srcIndex'))
            langpair = '%s-%s' % (LANGS[row.get('srclang')], LANGS[row.get('trglang')])
            if not RANKINGS.has_key(langpair):
                RANKINGS[langpair] = {}
            if not RANKINGS[langpair].has_key(sentno):
                RANKINGS[langpair][sentno] = {}
            this_rankings = get_rankings(row)
            for key in this_rankings.keys():
                RANKINGS[langpair][sentno][key] = RANKINGS[langpair][sentno].get(key,0) + 1

    # Read in input
    for line in sys.stdin:
        # Skip the header if seen
        if line.startswith('srclang'):
            continue

        # Hard-code this, so the header isn't required on STDIN
        srclang,trglang,srcIndex,documentId,segmentId,judgeId,system1Number,system1Id,system2Number,system2Id,system3Number,system3Id,system4Number,system4Id,system5Number,system5Id,system1rank,system2rank,system3rank,system4rank,system5rank = line.rstrip().split(',')

        srcIndex = int(srcIndex)
                  
        pair = '%s-%s' % (LANGS[srclang], LANGS[trglang])

        print 'SENTENCE', srcIndex
        print 'SOURCE', sources[pair][srcIndex-1]
        print 'REFERENCE', refs[pair][srcIndex-1]
        print 'USER', judgeId

        system_list = [(system1rank, system1Id, systems[pair][system1Id][srcIndex-1]),
                       (system2rank, system2Id, systems[pair][system2Id][srcIndex-1]),
                       (system3rank, system3Id, systems[pair][system3Id][srcIndex-1]),
                       (system4rank, system4Id, systems[pair][system4Id][srcIndex-1]),
                       (system5rank, system5Id, systems[pair][system5Id][srcIndex-1])]

        system_list.sort(key=lambda x: x[0])

        def score(langpair,sentno,system1,system2):
            score = 0
            try:
                pair = '%s < %s' % (system1, system2)
                revpair = '%s < %s' % (system2, system1)
                score = RANKINGS[langpair][sentno].get(pair,0) - RANKINGS[langpair][sentno].get(revpair,0)
            except KeyError:
                # print 'ERROR ON KEY', langpair,sentno,pair,revpair
                return 0

            # print 'SCORE(%s, %d, %s < %s) = %d' % (langpair, sentno, system1, system2, score)
            return score

        s = [[score(pair,srcIndex,system_list[y][1],system_list[x][1]) for x in range(5)] for y in range(5)]
        # print s

        print '%s | %2d %2d %2d %2d | %s [%s]' % (system_list[0][0], s[0][1], s[0][2], s[0][3], s[0][4], system_list[0][2], system_list[0][1])
        print '%s |    %2d %2d %2d | %s [%s]' % (system_list[1][0],           s[1][2], s[1][3], s[1][4], system_list[1][2], system_list[1][1])
        print '%s |       %2d %2d | %s [%s]' % (system_list[2][0],                     s[2][3], s[2][4], system_list[2][2], system_list[2][1])
        print '%s |          %2d | %s [%s]' % (system_list[3][0],                       s[3][4], system_list[3][2], system_list[3][1])
        print '%s |             | %s [%s]' % (system_list[4][0],                                     system_list[4][2], system_list[4][1])

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Computes author meta data that is then dumped into a file. Useful for the evaluation script,
evaluate_mturk_results.py.

Usage:

python $APPRAISE/appraise/author_meta.py $(find . -name mturk-results.txt) > turkers.meta.txt
"""

import csv
import sys
from collections import defaultdict

class Turker:
    def __init__(self):
        self.id = -1
        self.hittimes = []
        self.langs = {}

    def __str__(self):
        return '%s,%d,%d,%s' % (self.id, len(self.hittimes), self.avgtime(), self.langs)

    def avgtime(self):
        if len(self.hittimes) > 0:
            return sum(self.hittimes) / len(self.hittimes)

TURKERS = defaultdict(Turker)

for file in sys.argv[1:]:
    for row in csv.DictReader(open(file), delimiter = '\t'):
        if row.get('hitstatus') != 'Reviewable':
            continue
        id = row.get('workerid')
        end = row.get('Answer.end_timestamp')
        start = row.get('Answer.start_timestamp')
        if id is None or end is None or start is None:
            next

        langpair = '%s-%s' % (row.get('Answer.srclang'), row.get('Answer.trglang'))

        TURKERS[id].id = id
        try:
            TURKERS[id].hittimes.append(float(end) - float(start))
            TURKERS[id].langs[langpair] = TURKERS[id].langs.get(langpair,0) + 1
        except ValueError:
            # if len(TURKERS[id].hittimes) == 0:
            #     TURKERS[id].hittimes.append(0)
            pass

print 'judgeId,numhits,meantime,langs'
for turker in TURKERS.values():
    if len(turker.hittimes) > 0:
        print turker
    else:
        print "%s,?,?" % (turker.id)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>

usage: python compute_agreement_scores.py [-h] results-file

Computes agreement scores for the given results file in WMT format.

positional arguments:
  results-file          Comma-separated results file in WMT format

optional arguments:
  -h, --help            Show this help message and exit.
  --processes PROCESSES
                        Sets the number of parallel processes.

"""
import argparse
from collections import defaultdict
from itertools import combinations
from multiprocessing import Pool, cpu_count
from appraise.utils import AnnotationTask

PARSER = argparse.ArgumentParser(description="Computes agreement scores " \
  "for the given results file in WMT format.")
PARSER.add_argument("results_file", type=file, metavar="results-file",
  help="Comma-separated results file in WMT format.")
PARSER.add_argument("--processes", action="store", default=cpu_count(),
  dest="processes", help="Sets the number of parallel processes.", type=int)

def compute_agreement_scores(data):
    """
    Computes agreement scores for the given data set.
    """
    _task = AnnotationTask(data=data)
    
    try:
        _alpha = _task.alpha()
        _kappa = _task.kappa()
        _pi = _task.pi()
        # pylint: disable-msg=C0103
        _S = _task.S()
        return (_alpha, _kappa, _pi, _S)
    
    except ZeroDivisionError, msg:
        return (0, 0, 0, 0)


if __name__ == "__main__":
    args = PARSER.parse_args()
    
    # TODO: use proper CSV reader instead...
    results_data = defaultdict(lambda: defaultdict(list))
    line_no = 0
    
    for line in args.results_file:
        line_no = line_no + 1
        
        # The first line defines the header field names, we simply skip it.
        if line_no == 1:
            continue
        
        else:
            field_data = line.strip().split(',')
            language_pair = '{0}-{1}'.format(*field_data[0:2])
            segment_id = int(field_data[4])
            judge_id = field_data[5]
            
            # Filter out results where a user decided to "skip" ranking.
            results = [int(x) for x in field_data[16:21]]
            if all([x == -1 for x in results]):
                continue
            
            # Compute individual ranking decisions for this users.
            for a, b in combinations(range(5), 2):
                _c = judge_id
                _i = '{0}.{1}.{2}'.format(segment_id, a+1, b+1)
                
                if results[a] < results[b]:
                    _v = '{0}>{1}'.format(chr(65+a), chr(65+b))
                elif results[a] > results[b]:
                    _v = '{0}<{1}'.format(chr(65+a), chr(65+b))
                else:
                    _v = '{0}={1}'.format(chr(65+a), chr(65+b))
                
                # Append ranking decision in Artstein and Poesio format.
                results_data[language_pair][segment_id].append((_c, _i, _v))
    
    # We allow to use multi-processing.
    pool = Pool(processes=args.processes)
    print 'Language pair        Alpha   Kappa   Pi      S'
    for language_pair, segments_data in results_data.items():
        scores = []
        handles = []
        
        for segment_id, judgements in segments_data.items():
            _judgements = judgements
            _judgements.sort()
            
            handle = pool.apply_async(compute_agreement_scores,
              args=(_judgements,), callback=scores.append)
            handles.append(handle)
        
        # Block until all async computation processes are completed.
        while any([not x.ready() for x in handles]):
            continue
        
        # Compute average scores, ignoring any "empty" results.
        average_scores = []
        for i in range(4):
            _aggregate_score = sum([x[i] for x in scores if x[i]])
            _total_scores = float(len([x[i] for x in scores if x[i]]) or 1)
            average_scores.append(_aggregate_score/_total_scores)
        
        # Print out average agreement scores for current language pair.
        print '{0:>20} {1:.5} {2:.5} {3:.5} {4:.5}'.format(language_pair,
          *average_scores)

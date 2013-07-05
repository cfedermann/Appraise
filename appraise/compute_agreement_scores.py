#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>

usage: python compute_agreement_scores.py  [-h] [--processes PROCESSES]
                                           [--inter] [--intra] results-file

Computes agreement scores for the given results file in WMT format.

positional arguments:
  results-file          Comma-separated results file in WMT format.

optional arguments:
  -h, --help            Show this help message and exit.
  --processes PROCESSES
                        Sets the number of parallel processes.
  --inter               Compute inter-annotator agreement.
  --intra               Compute intra-annotator agreement.

"""
from __future__ import print_function, unicode_literals

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
PARSER.add_argument("--inter", action="store_true", default=False,
  dest="inter_annotator_agreement", help="Compute inter-annotator agreement.")
PARSER.add_argument("--intra", action="store_true", default=False,
  dest="intra_annotator_agreement", help="Compute intra-annotator agreement.")

def compute_agreement_scores(data):
    """
    Computes agreement scores for the given data set.
    """
    _task = AnnotationTask(data=data)
    _names = list(set([c[0] for c in data]))
    
    # Computer coder "name".  This is either a pair of two coders (cA, cB)
    # or just a single coder cA in case of intra-annotator agreement scores.
    if _names[0].split('-')[0] == _names[1].split('-')[0]:
        _key = _names[0].split('-')[0]
    else:
        _key = '{0}-{1}'.format(_names[0], _names[1])
    
    try:
        _kappa = _task.kappa()
        # pylint: disable-msg=E1101
        _multi_kappa = _task.multi_kappa()
        return (_kappa, _multi_kappa, _key)
    
    except (ZeroDivisionError):
        return (None, None, _key)


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
    print('Language pair        kappa   m-kappa c-kappa')
    
    language_pairs = ('English-Czech', 'English-German', 'English-Spanish',
      'English-French', 'Czech-English', 'German-English', 'Spanish-English',
      'French-English', 'English-Russian', 'Russian-English')
    
    for language_pair in language_pairs:
        segments_data = results_data[language_pair]
        scores = []
        handles = []
        
        per_coder_data = defaultdict(list)
        
        for segment_id, _judgements in segments_data.items():
            # Collect judgements on a per-coder-level.
            _coders = defaultdict(list)
            for _c, _i, _l in _judgements:
                _coders[_c].append((_c, _i, _l))
            
            # Inter-annotator agreement is computed for all pairs of coders
            # (cA, cB).  We collect these in the per_coder_data dictionary,
            # reducing the number of calls to compute_agreement_scores().
            if args.inter_annotator_agreement:
                # Skip segments with only a single annotation.
                if len(_coders.keys()) < 2:
                    continue
                
                # Extract pairwise judgements for all possible coder pairs.
                _coders_names = list(_coders.keys())
                _coders_names.sort()
                for a, b in combinations(range(len(_coders_names)), 2):
                    _cA = _coders_names[a]
                    _cB = _coders_names[b]
                    _coder = '{0}-{1}'.format(_cA, _cB)
                    
                    # Update per_coder_data dictionary with judgements.
                    per_coder_data[_coder].extend(_coders[_cA])
                    per_coder_data[_coder].extend(_coders[_cB])
            
            # Intra-annotator agreement is solely computed on items for which
            # an annotator has generated two or more annotations.
            elif args.intra_annotator_agreement:
                # Check that we have at least one annotation item with two or
                # more annotations from the current coder.
                for _coder, _coder_judgements in _coders.items():
                    _items = defaultdict(list)
                    for _, _i, _l in _coder_judgements:
                        _items[_i].append(_l)
                    
                    # If no item has two or more annotations, skip coder.
                    if all([len(x)<2 for x in _items.values()]):
                        continue
                    
                    # In order to avoid getting problems with NLTK, we have
                    # to rename the judgements for the current coder...
                    renamed_judgements = []
                    for _i, _ls in _items.items():
                        for d in range(len(_ls)):
                            _c = '{0}-{1}'.format(_coder, d)
                            renamed_judgements.append((_c, _i, _ls[d]))
                    
                    # Pool compute_agreement_scores() call and save handle.
                    handle = pool.apply_async(compute_agreement_scores,
                      args=(renamed_judgements,), callback=scores.append)
                    handles.append(handle)
            
            # Naive implementation calling compute_agreement_scores() on all
            # judgements which are available for the current item. Very slow.
            else:
                handle = pool.apply_async(compute_agreement_scores,
                  args=(_judgements,), callback=scores.append)
                handles.append(handle)
        
        # For inter-annotator agreement, we pool compute_agreement_scores()
        # now to minimise the number of AnnotationTask instances used.
        #
        # This greatly speeds up processing time.
        if args.inter_annotator_agreement:
            for _pairwise_judgements in per_coder_data.values():
                # Pool compute_agreement_scores() call and save handle.
                handle = pool.apply_async(compute_agreement_scores,
                  args=(_pairwise_judgements,), callback=scores.append)
                handles.append(handle)
        
        # Block until all async computation processes are completed.
        while any([not x.ready() for x in handles]):
            continue
        
        # Compute average scores, normalising on per-item level.
        average_scores = []
        for i in range(2):
            _aggregate_score = sum([x[i] for x in scores if x[i] is not None])
            _total_scores = len([x[i] for x in scores if x[i] is not None])
            average_scores.append(_aggregate_score/float(_total_scores or 1))
        
        # Compute average scores, normalising on per-coder level.
        per_coder = defaultdict(list)
        for score in scores:
            per_coder[score[-1]].append(score[1])
        
        average = []
        for coder, coder_data in per_coder.items():
            _aggregate_score = sum([x for x in coder_data if x is not None])
            _total_scores = len([x for x in coder_data if x is not None])
            average.append(_aggregate_score/float(_total_scores or 1))
        
        average_scores.append(sum(average)/float(len(average) or 1))
        
        # Print out average agreement scores for current language pair.
        print('{0:>20} {1:.5} {2:.5} {3:.5}'.format(language_pair,
          *average_scores))

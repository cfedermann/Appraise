#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>

usage: python convert_mturk_results.py [-h] mturk-file

Converts MTurk results to WMT13 export CSV format.

positional arguments:
  mturk-file  Tab-separated results file exported from MTurk

optional arguments:
  -h, --help  Show this help message and exit.

"""
import argparse

PARSER = argparse.ArgumentParser(description="Converts MTurk results to " \
  "WMT13 export CSV format.")
PARSER.add_argument("mturk_file", type=file, metavar="mturk-file",
  help="Tab-separated results file exported from MTurk.")


def convert_mturk_to_csv(mturk_data, mturk_header):
    _results = []
    
    # Add a default value for non-existing field names.
    mturk_data.append('-1')
    
    # We construct CSV output for three sentences.
    for sentence in (1, 2, 3):
        _answer_var = 'Answer.order_{0}'.format(sentence)
        order_x = mturk_data[mturk_header.get(_answer_var, -1)]
        order_x = [int(x) for x in order_x.split(',')]
        
        _answer_var = 'Answer.systems_{0}'.format(sentence)
        systems_x = mturk_data[mturk_header.get(_answer_var, -1)]
        systems_x = systems_x.split(',')
        
        values = []
        values.append(mturk_data[mturk_header.get('Answer.srclang', -1)])
        values.append(mturk_data[mturk_header.get('Answer.trglang', -1)])
        _answer_var = 'Answer.srcIndex_{0}'.format(sentence)
        _src_index = mturk_data[mturk_header.get(_answer_var, -1)]
        # If we could successfully extract the sentence id from the answer
        # data, we have to increment it by 1 as the WMT format is 1-indexed
        if _src_index != -1:
            _src_index += 1
        values.append(_src_index)
        values.append('-1') # documentId
        values.append(_src_index)
        values.append(mturk_data[mturk_header.get('Answer.workerId', -1)])
        values.append('-1') # system1Number
        values.append(systems_x[0])
        values.append('-1') # system2Number
        values.append(systems_x[1])
        values.append('-1') # system3Number
        values.append(systems_x[2])
        values.append('-1') # system4Number
        values.append(systems_x[3])
        values.append('-1') # system5Number
        values.append(systems_x[4])
        
        ranks = [-1] * 5
        for index in range(5):
            _answer_var = 'Answer.rank_{0}_{1}'.format(index, sentence)
            rank_x_y = int(mturk_data[mturk_header.get(_answer_var, -1)])
            ranks[order_x[index]] = rank_x_y
        
        for rank in ranks:
            values.append(str(rank))
        
        # Skip results which do not contain ranks for all candidates?
        # if -1 in ranks:
        #     continue
        
        _results.append(u','.join(values))
    
    return _results

if __name__ == "__main__":
    args = PARSER.parse_args()
    
    MTURK_HEADER = {}
    line_no = 0
    results = [u'srclang,trglang,srcIndex,documentId,segmentId,judgeId,' \
      'system1Number,system1Id,system2Number,system2Id,system3Number,' \
      'system3Id,system4Number,system4Id,system5Number,system5Id,' \
      'system1rank,system2rank,system3rank,system4rank,system5rank']
    
    for line in args.mturk_file:
        line_no = line_no + 1
        
        # The first line defines the header field names.
        if line_no == 1:
            _field_index = 0
            for field_name in line.strip().split('\t'):
                MTURK_HEADER[eval(field_name)] = _field_index
                _field_index = _field_index + 1
        
        else:
            # MTurk stores values encoded as "string values"; we use eval()
            # to convert them into Python Strings, skipping empty Strings "".
            _field_data = [eval(k) for k in line.strip().split('\t') if k]
            _hitstatus = MTURK_HEADER['hitstatus']
            if len(MTURK_HEADER.keys()) != len(_field_data) \
              or _field_data[_hitstatus] != 'Reviewable':
                continue
            
            results.extend(convert_mturk_to_csv(_field_data, MTURK_HEADER))
    
    print u'\n'.join(results)

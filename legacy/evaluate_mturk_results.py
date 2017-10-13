#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>

usage: python evaluate_mturk_results [-h] mturk-file appraise-file

Evaluates MTurk results by comparing to researchers' rankings.

positional arguments:
  mturk-file     MTurk results in WMT13 export CSV format
  appraise-file  Appraise results in WMT13 export CSV format

optional arguments:
  -h, --help     Show this help message and exit.

"""
from itertools import combinations
import argparse

PARSER = argparse.ArgumentParser(description="Evaluates MTurk results by " \
  "comparing to researchers' rankings.")
PARSER.add_argument("mturk_file", type=file, metavar="mturk-file",
  help="MTurk results in WMT13 export CSV format")
PARSER.add_argument("appraise_file", type=file, metavar="appraise-file",
  help="Appraise results in WMT13 export CSV format")


def compare_data_point_to_dict(_data_point, target_dict):
    """
    Compares the given _data_point tuple to the "truth" in target_dict.
    """
    _language_pair, _sentence_no, _ranking_decision = _data_point
    
    if not target_dict.has_key(_language_pair) or \
      not target_dict[language_pair].has_key(_sentence_no):
        return False
    
    # pylint: disable-msg=W0612
    inverted_decision = '{1}>{0}'.format(*_ranking_decision.split('>'))
    _store = target_dict[_language_pair][_sentence_no]
    _score = _store.get('ranking_decision', 0)
    _inverted = _store.get('inverted_decision', 0)
    
    return _score >= _inverted


def add_data_point_to_dict(_data_point, target_dict):
    """
    Adds the given _data_point tuple to dictionary target_dict.
    
    A suitable _data_point tuple contains the following information:
    - language pair;
    - sentence number;
    - ranking decision (sysX > sysY).
    
    If the given target_dict does not contain any of the required keys, these
    will be created on demand.  If the given ranking decision (sysX > sysY) is
    already contained within target_dict, its count will be incremented.
    
    """
    _language_pair, _sentence_no, _ranking_decision = _data_point
    
    if not target_dict.has_key(_language_pair):
        target_dict[_language_pair] = {}
    
    if not target_dict[_language_pair].has_key(_sentence_no):
        target_dict[_language_pair][_sentence_no] = {}
    
    _store = target_dict[_language_pair][_sentence_no]
    if not _ranking_decision in _store.keys():
        _store[_ranking_decision] = 1
    else:
        _store[_ranking_decision] = _store[_ranking_decision] + 1


if __name__ == "__main__":
    args = PARSER.parse_args()
    
    LANGUAGE_MAP = {'czech': 'ces', 'ces': 'ces', 'cze': 'ces', 'deu': 'deu',
      'german': 'deu', 'ger': 'deu', 'spa': 'spa', 'spanish': 'spa',
      'eng': 'eng', 'english': 'eng', 'french': 'fra', 'fra': 'fra',
      'fre': 'fra', 'russian': 'rus', 'rus': 'rus'}
    
    MTURK_DATA = {}
    APPRAISE_DATA = {}
    line_no = 0
    results = []
    
    for line in args.mturk_file:
        line_no = line_no + 1
        
        # Skip first line containing header.
        if line_no == 1:
            continue
        
        line_data = line.strip().split(',')
        src_lang = LANGUAGE_MAP[line_data[0].lower()]
        trg_lang = LANGUAGE_MAP[line_data[1].lower()]
        language_pair = '{0}2{1}'.format(src_lang, trg_lang)
        sentence_no = int(line_data[2])
        judge_id = line_data[5]
        sysIds = line_data[7:17:2]
        sysRanks = line_data[-5:]
        
        if not judge_id in MTURK_DATA.keys():
            MTURK_DATA[judge_id] = {}
        
        decisions = []
        for a, b in combinations(range(5), 2):
            if sysRanks[a] > sysRanks[b]:
                decisions.append('{0}>{1}'.format(sysIds[a], sysIds[b]))
            elif sysRanks[a] < sysRanks[b]:
                decisions.append('{0}>{1}'.format(sysIds[b], sysIds[a]))
        
        for ranking_decision in decisions:
            data_point = (language_pair, sentence_no, ranking_decision)
            add_data_point_to_dict(data_point, MTURK_DATA[judge_id])
    
    line_no = 0
    for line in args.appraise_file:
        line_no = line_no + 1
        
        # Skip first line containing header.
        if line_no == 1:
            continue
        
        line_data = line.strip().split(',')
        src_lang = LANGUAGE_MAP[line_data[0].lower()]
        trg_lang = LANGUAGE_MAP[line_data[1].lower()]
        language_pair = '{0}2{1}'.format(src_lang, trg_lang)
        sentence_no = int(line_data[2])
        sysIds = line_data[7:17:2]
        sysRanks = line_data[-5:]
        
        decisions = []
        for a, b in combinations(range(5), 2):
            if sysRanks[a] > sysRanks[b]:
                decisions.append('{0}>{1}'.format(sysIds[a], sysIds[b]))
            elif sysRanks[a] < sysRanks[b]:
                decisions.append('{0}>{1}'.format(sysIds[b], sysIds[a]))
        
        for ranking_decision in decisions:
            data_point = (language_pair, sentence_no, ranking_decision)
            add_data_point_to_dict(data_point, APPRAISE_DATA)
    
    user_agreement = []
    
    for user_id in MTURK_DATA.keys():
        rankings = 0
        overlap = 0
        for language_pair, sentence_nos in MTURK_DATA[user_id].items():
            for sentence_no, ranking_decisions in sentence_nos.items():
                for decision, _ in ranking_decisions.items():
                    rankings = rankings + 1
                    data_point = (language_pair, sentence_no, decision)
                    if compare_data_point_to_dict(data_point, APPRAISE_DATA):
                        overlap = overlap + 1
        
        _data = (overlap / float(rankings or 1), overlap, rankings, user_id)
        user_agreement.append(_data)
    
    print
    user_agreement.sort()
    user_agreement.reverse()
    print 'Username         Overlap  Total    Percentage'
    for user_data in user_agreement:
        print '{0:>15}:    {1:05d}    {2:05d}    {3:.5f}'.format(user_data[3],
          user_data[1], user_data[2], user_data[0])
    
    print u'\n'.join(results)

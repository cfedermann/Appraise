#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>

usage: export_wmt15_ranking_csv.py

Exports WMT15 results for all language pairs, in ranking CSV format.

"""
from datetime import datetime
import os
import sys


if __name__ == "__main__":
    # Properly set DJANGO_SETTINGS_MODULE environment variable.
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    PROJECT_HOME = os.path.normpath(os.getcwd() + "/..")
    sys.path.append(PROJECT_HOME)

    # We have just added appraise to the system path list, hence this works.
    from appraise.wmt15.models import RankingResult

    # Print out results in CSV WMT format.
    headers = 'ID,srcLang,tgtLang,user,duration,rank_1,word_count_1,rank_2,word_count_2,rank_3,word_count_3,rank_4,word_count_5,rank_1,word_count_5'
    print headers
    for result in RankingResult.objects.filter(item__hit__completed=True):
        result.reload_dynamic_fields()
        try:
            print u','.join([unicode(x) for x in result.export_to_ranking_csv()])
        except:
            pass


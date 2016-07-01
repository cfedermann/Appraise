#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>

usage: export_wmt15_results.py

Exports WMT15 results for all language pairs, in CSV WMT format.

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
    from django.contrib.auth.models import Group
    from appraise.wmt15.models import RankingResult

    ces2eng = Group.objects.filter(name="ces2eng")
    
    # Print out results in CSV WMT format.
    headers = [u'srclang,trglang,srcIndex,documentId,segmentId,judgeId,' \
      'system1Number,system1Id,system2Number,system2Id,system3Number,' \
      'system3Id,system4Number,system4Id,system5Number,system5Id,' \
      'system1rank,system2rank,system3rank,system4rank,system5rank']
    print u",".join(headers)
    for result in RankingResult.objects.filter(item__hit__completed=True,item__hit__active=True,item__hit__language_pair="ces2eng"):
        result.reload_dynamic_fields()
        try:
#            igroups = list(result.item.hit.groups.all())
#            if ces2eng in igroups:
            print result.export_to_csv()
        except:
            pass


#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>

usage: export_wmt16_results.py

Exports WMT16 results for all language pairs, in CSV WMT format.

"""
from datetime import datetime
import os
import sys

from django.shortcuts import get_object_or_404

if __name__ == "__main__":
    # Properly set DJANGO_SETTINGS_MODULE environment variable.
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    PROJECT_HOME = os.path.normpath(os.getcwd() + "/..")
    sys.path.append(PROJECT_HOME)
    
    # We have just added appraise to the system path list, hence this works.
    from appraise.wmt16.models import RankingResult, Project
    
    # Print out results in CSV WMT format.
    annotation_project = get_object_or_404(Project, name=project)
    
    queryset = RankingResult.objects.filter(item__hit__completed=True)

    results = [u'srclang,trglang,srcIndex,segmentId,judgeId,' \
      'system1Id,system1rank,system2Id,system2rank,rankingID']
    
    for result in queryset:
        if isinstance(result, RankingResult):
            if result.item.hit.project_set.filter(id=annotation_project.id):
                try:
                    current_csv = result.export_to_pairwise_csv()
                    if current_csv is None:
                        continue
                    
                    print current_csv
                except:
                    pass

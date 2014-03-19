#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>

usage: export_wmt14_status.py

Exports HIT status for all language pairs.

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
    from appraise.wmt14.models import HIT, LANGUAGE_PAIR_CHOICES
    
    remaining_hits = {}
    for language_pair in [x[0] for x in LANGUAGE_PAIR_CHOICES]:
        remaining_hits[language_pair] = HIT.compute_remaining_hits(
          language_pair=language_pair)
    
    print
    print '[{0}]'.format(datetime.now().strftime("%c"))
    for k, v in remaining_hits.items():
        print '{0}: {1:03d}'.format(k, v)
    print

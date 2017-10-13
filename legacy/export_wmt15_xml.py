#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>

usage: export_wmt15_xml.py

Exports WMT15 results for all language pairs, in XML format.

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
    from appraise.wmt15.models import HIT

    for result in HIT.objects.filter(completed=True):
        result.reload_dynamic_fields()
        try:
            print result.export_to_xml()
        except:
            pass


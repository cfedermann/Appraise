#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>

usage: export_wmt14_userstats.py

Exports user statistics for all users.  This lists:

- username
- email
- research group
- number of completed HITs
- total annotation time

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
    from django.contrib.auth.models import User, Group
    from appraise.wmt14.models import HIT
    
    # Compute user statistics for all users.
    user_stats = []
    wmt14 = Group.objects.get(name='WMT14')
    users = wmt14.user_set.all()
    
    for user in users:
        _user_stats = HIT.compute_status_for_user(user)
        _name = user.username
        _email = user.email
        
        _group = "UNDEFINED"
        for _g in user.groups.all():
            if _g.name.startswith("eng2") \
              or _g.name.endswith("2eng") \
              or _g.name == "WMT14":
                continue
            
            _group = _g.name
            break
        
        _data = (_name, _email, _group, _user_stats[0], _user_stats[2])
        user_stats.append(_data)
    
    # Sort by research group.
    user_stats.sort(key=lambda x: x[2])
    
    # Print out CSV list.
    for user_data in user_stats:
        print u",".join([unicode(x) for x in user_data])

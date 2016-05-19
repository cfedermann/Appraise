#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>

usage: export_wmt16_userstats.py

Exports user statistics for all users.  This lists:

- username
- email
- research groups
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
    from appraise.wmt16.models import HIT, Project
    from appraise.wmt16.views import _identify_groups_for_user
    
    # Compute user statistics for all users.
    user_stats = []
    wmt16 = Group.objects.get(name='WMT16')
    users = wmt16.user_set.all()
    
    # Iterate over all users and collect stats for all projects
    for user in users:
        for project in Project.objects.all():
            _user_stats = HIT.compute_status_for_user(user, project)
            _name = user.username
            _email = user.email
            _project = project.name
        
            groups = _identify_groups_for_user(user)
            _group = "UNDEFINED"
            if len(groups) > 0:
                _group = ';'.join([g.name for g in groups])
        
        
           
            _data = (_name, _email, _project, _group, _user_stats[0], _user_stats[2])
            user_stats.append(_data)
    
    # Sort by research group.
    user_stats.sort(key=lambda x: x[2])
    
    # Print out CSV list.
    for user_data in user_stats:
        print u",".join([unicode(x) for x in user_data])

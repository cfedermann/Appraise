#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>

usage: create_wmt14_invites.py [-h] group-name number-of-tokens

Creates the requested number of invite tokens for the given group.

positional arguments:
  group-name        Name of the user group the invites belong to.
  number-of-tokens  Total number of invite tokens to generate.

optional arguments:
  -h, --help        show this help message and exit

"""
import argparse
import os
import sys

PARSER = argparse.ArgumentParser(description="Creates the requested number " \
  "of invite tokens for the given group.")
PARSER.add_argument("group_name", metavar="group-name", help="Name of the " \
  "user group the invites belong to.")
PARSER.add_argument("number_of_tokens", metavar="number-of-tokens",
  help="Total number of invite tokens to generate.")


if __name__ == "__main__":
    args = PARSER.parse_args()
    
    # Properly set DJANGO_SETTINGS_MODULE environment variable.
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    PROJECT_HOME = os.path.normpath(os.getcwd() + "/..")
    sys.path.append(PROJECT_HOME)
    
    # We have just added appraise to the system path list, hence this works.
    from appraise.wmt14.models import UserInviteToken
    from django.contrib.auth.models import Group
    
    # Check if the given group name is valid.
    group = Group.objects.filter(name=args.group_name)
    if not group.exists():
        print 'ERROR: unknown group name "{0}"...'.format(args.group_name)
        sys.exit(-1)

    else:
        group = group[0]
    
    # Check if the requested number of tokens is sane.
    try:
        number = int(args.number_of_tokens)
        assert(number > 0 and number < 50)

    except:
        print "ERROR: requested number of tokens is insane..."
        sys.exit(-2)
    
    # Generate user invite tokens.
    generated_tokens = []
    for _ in range(number):
        new_token = UserInviteToken(group=group)
        new_token.save()
        generated_tokens.append(new_token.token)
    
    # Print user invite tokens to screen.
    for token in generated_tokens:
        print token


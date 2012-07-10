#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Matt Post <post@cs.jhu.edu>

This script takes a set of parallel files and writes out the XML file used to
setup the corresponding Appraise tasks.

# TODO: fix usage help String.
Usage:
    $ build-xml.py -s SOURCE -

"""

import argparse

parser = argparse.ArgumentParser(description="Build evaluation task input " \
  "file.")
parser.add_argument('source', type=file, help='source language file')
parser.add_argument('system', metavar='system', nargs='+', type=file,
  help="parallel files to compare")
parser.add_argument('-id', type=str, default='none', help='ID name to use " \
  "for the system name')
parser.add_argument('-source', type=str, default='spa', dest='sourceLang',
  help='the source language')
parser.add_argument('-target', type=str, default='eng', dest='targetLang',
  help='the target language')

args = parser.parse_args()

source = []
for line in args.source:
    source.append(line.strip())

systems = []
for i, system in enumerate(args.system):
    systems.append([])
    for line in system:
        systems[i].append(line.strip())

# TODO: change to use of .format() calls. Check that it works with UTF-8 data.
print u'<set id="%s" source-language="%s" target-language="%s">' % (args.id, args.sourceLang, args.targetLang)
for i, sentence in enumerate(systems[0]):
    print u'  <seg id="%d" doc-id="%s">' % (i+1, args.source.name)
    print u'    <source>%s</source>' % (source[i])
    for j, system in enumerate(systems):
        print u'    <translation system="%s">%s</translation>' % (args.system[j].name, system[i])
    print u'  </seg>'
print u'</set>'


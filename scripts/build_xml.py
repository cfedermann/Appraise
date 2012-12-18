#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Matt Post <post@cs.jhu.edu>

This script takes a set of parallel files and writes out the XML file used to
setup the corresponding Appraise tasks.

usage:
    $ build_xml.py [-h] [-id ID] [-source SOURCELANG] [-target TARGETLANG] \
      source system [system ...]

where
  -id is a system ID (e.g., "wmt-2012")
  -source is a source language identifier (e.g., "es")
  -target is a source language identifier (e.g., "en")
  -diff-documents will mark each sentence as from a different document
   (as opposed to sequential sentences in the same document)
  source is the source language file
  system[1..N] are system outputs parallel to the source file

"""

import argparse

PARSER = argparse.ArgumentParser(description="Build evaluation task input " \
  "file.")
PARSER.add_argument("source", type=file, help="source language file")
PARSER.add_argument("reference", type=file, nargs="?", help="reference language file")
PARSER.add_argument("system", metavar="system", nargs="+", type=file,
  help="parallel files to compare")
PARSER.add_argument("-id", type=str, default="none", help="ID name to use " \
  "for the system name")
PARSER.add_argument("-source", type=str, default="spa", dest="sourceLang",
  help="the source language")
PARSER.add_argument("-target", type=str, default="eng", dest="targetLang",
  help="the target language")
PARSER.add_argument("-diff-documents", action="store_false", default=True,
  dest="sameDocument", help="sentences are from different documents")


if __name__ == "__main__":
    args = PARSER.parse_args()

    source = []
    for line in args.source:
        source.append(line.strip())
    
    reference = []
    for line in args.reference:
        reference.append(line.strip())

    systems = []
    for i, system in enumerate(args.system):
        systems.append([])
        for line in system:
            systems[i].append(line.strip())

    print '<set id="%s" source-language="%s" target-language="%s">' \
      % (args.id, args.sourceLang, args.targetLang)

    # TODO: change to use of .format() calls. Check that it works with UTF-8 data.
    for i, sentence in enumerate(systems[0]):

        # If the sentences are from different documents, we give each of them a
        # different document name so that they will not be presented with context.
        docid = args.source.name if args.sameDocument else '{}-{}'.format(
          args.source.name, i+1)

        print '  <seg id="%d" doc-id="%s">' % (i+1, docid)
        print '    <source>%s</source>' % (source[i])
        if len(reference) >= i+1:
            print '    <reference>%s</reference>' % (reference[i])
        for j, system in enumerate(systems):
            print '    <translation system="%s">%s</translation>' \
              % (args.system[j].name, system[i])
        print '  </seg>'
    print '</set>'

    
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>

usage: python repair_wmt14_xml.py
               [-h] [--dry-run]
               hits-file

Checks and repairs a given XML file containing HITs for WMT14. Uses
appraise.wmt14.validators.validate_hits_xml_file() for validation.

positional arguments:
  hits-file             XML file(s) containing HITs. Can be multiple files
                        using patterns such as '*.xml' or similar.

optional arguments:
  -h, --help            Show this help message and exit.
  --dry-run             Enable dry run to simulate repair.

"""
from django.core.exceptions import ValidationError

from time import sleep
import argparse
import os
import re
import sys

from xml.etree.ElementTree import fromstring, tostring

PARSER = argparse.ArgumentParser(description="Checks and repairs a given " \
  "XML file containing HITs for WMT14. Uses\nappraise.wmt14.validators." \
  "validate_hits_xml_file() for validation.")
PARSER.add_argument("hits_file", metavar="hits-file", help="XML file " \
  "containing HITs.")
PARSER.add_argument("--dry-run", action="store_true", default=False,
  dest="dry_run_enabled", help="Enable dry run to simulate repair.")


XML_REPAIR_PATTERNS = [
  (u'& ', u'&amp; '),
  (u'&amp ', u'&amp; '),
  (u'&quot ', u'&quot; '),
  (u'R&D', u'R&amp;D'),
  (u'R & D', u'R &amp; D'),
  (u'A&E', u'A&amp;E'),
  (u'CD&V', u'CD&amp;V'),
  (u'CD & V', u'CD &amp; V'),
  (u'>Grub<', u'&gt;Grub&lt;'),
  (u'S&P', u'S&amp;P'),
  (u'S & P', u'S &amp; P'),
  (u'&Poor ', u'&amp;Poor '),
  (u'&.', u'&amp;.'),
  (u'<службе', u'&lt;службе'),
  (u'<security', u'&lt;security'),
  (u'< ', u'&lt; '),
]


if __name__ == "__main__":
    args = PARSER.parse_args()
    
    # Properly set DJANGO_SETTINGS_MODULE environment variable.
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    PROJECT_HOME = os.path.normpath(os.getcwd() + "/..")
    sys.path.append(PROJECT_HOME)
    
    # We have just added appraise to the system path list, hence this works.
    from appraise.wmt14.validators import validate_hits_xml_file

    with open(args.hits_file) as infile:
        hits_xml_string = unicode(infile.read(), "utf-8")
        loop_counter = 0
        
        while loop_counter < 10:
            print "loop counter: ", loop_counter
            loop_counter += 1

            try:
                # Validate XML before trying to import anything from the given file.
                validate_hits_xml_file(hits_xml_string)
                break

            except ValidationError, msg:
                print msg
                for key, value in XML_REPAIR_PATTERNS:
                    print repr(key), "-->", repr(value)
                    patched_hits_xml_string = unicode.replace(hits_xml_string, key, value)
                    hits_xml_string = patched_hits_xml_string
                    
                continue

    if not args.dry_run_enabled:
        fixed_filename = '{0}.fixed'.format(args.hits_file)
        print 'Writing fixed file to "{0}"...'.format(fixed_filename)
        with open(fixed_filename, 'w') as outfile:
            outfile.write(hits_xml_string.encode('utf-8'))


#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>

usage: python import_wmt14_xml.py
               [-h] [--wait SLEEP_SECONDS] [--dry-run] [--mturk-only]
               hits-file [hits-file ...]

Imports HITs from a given XML file into the Django database. Uses
appraise.wmt14.validators.validate_hits_xml_file() for validation.

positional arguments:
  hits-file             XML file(s) containing HITs. Can be multiple files
                        using patterns such as '*.xml' or similar.

optional arguments:
  -h, --help            Show this help message and exit.
  --wait SLEEP_SECONDS  Amount of seconds to wait between individual files.
  --dry-run             Enable dry run to simulate import.
  --mturk-only          Enable MTurk-only flag for all HITs.

"""
from time import sleep
import argparse
import os
import sys

from xml.etree.ElementTree import fromstring, tostring

PARSER = argparse.ArgumentParser(description="Imports HITs from a given " \
  "XML file into the Django database.\nUses appraise.wmt14.validators." \
  "validate_hits_xml_file() for validation.")
PARSER.add_argument("hits_file", metavar="hits-file", help="XML file(s) " \
  "containing HITs.  Can be multiple files using patterns such as '*.xml' " \
  "or similar.", nargs='+')
PARSER.add_argument("--wait", action="store", default=5, dest="sleep_seconds",
  help="Amount of seconds to wait between individual files.", type=int)
PARSER.add_argument("--dry-run", action="store_true", default=False,
  dest="dry_run_enabled", help="Enable dry run to simulate import.")
PARSER.add_argument("--mturk-only", action="store_true", default=False,
  dest="mturk_only", help="Enable MTurk-only flag for all HITs.")


if __name__ == "__main__":
    args = PARSER.parse_args()
    
    # Properly set DJANGO_SETTINGS_MODULE environment variable.
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    PROJECT_HOME = os.path.normpath(os.getcwd() + "/..")
    sys.path.append(PROJECT_HOME)
    
    # We have just added appraise to the system path list, hence this works.
    from appraise.wmt14.models import HIT
    from appraise.wmt14.validators import validate_hits_xml_file
    
    # We might potentially be dealing with more than a single input file.
    first_run = True
    for _hits_file in args.hits_file:
        if not first_run and args.sleep_seconds > 0:
            print 'Waiting {0} second(s)'.format(args.sleep_seconds),
            for i in range(args.sleep_seconds):
                print ' .',
                sys.stdout.flush()
                sleep(1)
            print
            print
        
        else:
            first_run = False
        
        hits_xml_string = None
        with open(_hits_file) as infile:
            hits_xml_string = unicode(infile.read(), "utf-8")
        
        # Validate XML before trying to import anything from the given file.
        validate_hits_xml_file(hits_xml_string)
    
        _errors = 0
        _total = 0
        _tree = fromstring(hits_xml_string.encode("utf-8"))
    
        for _child in _tree:        
            block_id = _child.attrib["block-id"]
            language_pair = '{0}2{1}'.format(_child.attrib["source-language"],
              _child.attrib["target-language"])
        
            # Hotfix potentially wrong ISO codes;  we are using ISO-639-3.
            iso_639_2_to_3_mapping = {'cze': 'ces', 'fre': 'fra', 'ger': 'deu'}
            for part2_code, part3_code in iso_639_2_to_3_mapping.items():
                language_pair = language_pair.replace(part2_code, part3_code)
        
            try:
                _total = _total + 1
                _hit_xml = tostring(_child, encoding="utf-8").decode('utf-8')
            
                if args.dry_run_enabled:
                    _ = HIT(block_id=block_id, hit_xml=_hit_xml,
                      language_pair=language_pair, mturk_only=args.mturk_only)
            
                else:
                    # Use get_or_create() to avoid exact duplicates.  We do allow
                    # them for WMT14 to measure intra-annotator agreement...
                    h = HIT(block_id=block_id, hit_xml=_hit_xml,
                      language_pair=language_pair, mturk_only=args.mturk_only)
                    h.save()
        
            # pylint: disable-msg=W0703
            except Exception, msg:
                print msg
                _errors = _errors + 1
    
        print
        print '[{0}]'.format(_hits_file)
        print 'Successfully imported {0} HITs, encountered errors for ' \
          '{1} HITs.'.format(_total, _errors)
        print

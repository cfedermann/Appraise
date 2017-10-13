#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>
"""
import argparse
import os
import sys

from xml.etree.ElementTree import fromstring, tostring

PARSER = argparse.ArgumentParser(description="Imports tasks from a given " \
  "XML file into the Django database.")
PARSER.add_argument("tasks_file", metavar="tasks-file", help="XML file(s) " \
  "containing tasks.  Can be multiple files using patterns such as '*.xml' " \
  "or similar.", nargs='+')
PARSER.add_argument("--dry-run", action="store_true", default=False,
  dest="dry_run_enabled", help="Enable dry run to simulate import.")


if __name__ == "__main__":
    args = PARSER.parse_args()

    # Properly set DJANGO_SETTINGS_MODULE environment variable.
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    PROJECT_HOME = os.path.normpath(os.getcwd() + "/..")
    sys.path.append(PROJECT_HOME)

    # We have just added appraise to the system path list, hence this works.
    from appraise.beta16.models import AbsoluteScoringTask, MetaData

    ###
    # <segments>
    #   <segment id="1492" source-language="de" target-language="en">
    #    <system-id>newstest2015.online-F.0.de-en.txt</system-id>
    #    <reference>The president deserves everyone's respect, he deserves our loyality, he deserves our support.</reference>
    #    <candidate>The president earned everyone respect, it earns our loyalty, it earns our support.</candidate>
    #   </segment>
    #   ...
    # </segments>
    ###

    for _tasks_file in args.tasks_file:
        tasks_xml_string = None
        with open(_tasks_file) as infile:
            tasks_xml_string = unicode(infile.read(), "utf-8")

        _tree = fromstring(tasks_xml_string.encode("utf-8"))
        for _child in _tree:
            segment_id = _child.attrib["id"]
            source_language = _child.attrib["source-language"]
            target_language = _child.attrib["target-language"]
            system_id = _child.findall("system-id")[0].text
            reference_text = _child.findall("reference")[0].text
            for candidate in _child.findall("candidate"):
                candidate_text = candidate.text
                print candidate_text.encode('utf-8')

            new_meta = MetaData()
            new_meta.save()

            new_task = AbsoluteScoringTask()
            new_task.segment_id = segment_id
            new_task.source_language = source_language
            new_task.target_language = target_language
            new_task.system_id = system_id
            new_task.reference = reference_text
            new_task.candidate = candidate_text
            new_task.save()

# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
"""
import sys
from xml.etree.ElementTree import ElementTree
from evaluation.models import EditingTask, EditingItem

# export DJANGO_SETTINGS_MODULE=settings
# PYTHONPATH=../ /opt/local/bin/python2.7 import_editing_task.py

def usage (scriptname):
    """Prints usage instructions to screen."""
    print "\n\tusage: {0} <editing-data.xml>\n".format(scriptname)

def main(xml_file):
    """Imports a editing task and corresponding items from an XML file."""
    
    # Create ElementTree from the given XML file.
    xml_tree = ElementTree()
    xml_tree.parse(xml_file)
    
    _attrib = xml_tree.getroot().attrib
    if not 'source_language' in _attrib.keys() \
      or not 'target_language' in _attrib.keys() \
      or not 'id' in _attrib.keys():
        print "Invalid XML file, aborting..."
        sys.exit(-1)
    
    # Collect all sentences in memory and check that they are valid.
    invalid = False
    sentences = xml_tree.findall('sentence')
    for sentence in sentences:
        _names = [c.tag for c in sentence.getchildren()]
        _names.sort()
        if not _names == ['source', 'target', 'target', 'target']:
            print "<sentence id='{0}'>: invalid children...".format(
              sentence.attrib['id'])
            invalid = True
    
    if invalid:
        print "At least one sentence is invalid, aborting..."
        sys.exit(-1)
    
    new_task = EditingTask(shortname=u"{0}-{1}-{2}".format(_attrib['id'],
      _attrib['source_language'], _attrib['target_language']))
    new_task.save()
    print "Created new editing task: '{0}'.".format(new_task)
    
    for sentence in sentences:
        source = None
        target = {}
        for child in sentence.getchildren():
            if child.tag == 'source':
                source = child.text.strip()
            elif child.tag == 'target':
                target[child.attrib['system']] = child.text.strip()
        
        _target = target.keys()
        _target.sort()
        new_item = EditingItem(task=new_task, source=source,
          systemA=target[_target[0]], systemB=target[_target[1]],
          systemC=target[_target[2]], edited=False)
        new_item.save()
        print "Created new editing item: '{0}'.".format(new_item)
    
    print "Done."
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage(sys.argv[0])
        sys.exit(-1)
    
    XML_FILE = sys.argv[1]
    main(XML_FILE)

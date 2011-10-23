# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
"""
import sys
from evaluation.models import LucyTask, LucyItem

# export DJANGO_SETTINGS_MODULE=settings
# PYTHONPATH=../ /opt/local/bin/python2.7 import_evaluation_data.py

def usage (scriptname):
    """Prints usage instructions to screen."""
    print "\n\tusage: {0} <data-file>\n".format(scriptname)

def main(data_file):
    """Imports evalation data items from the given data file."""
    
    # Create task for current data file.
    new_task = LucyTask(shortname=data_file)
    new_task.save()
    
    data = []
    with open(data_file, 'r') as source:
        for line in source:
            if not len(line.strip('\n-')):
                new_item = LucyItem(task=new_task, source=data[0],
                  reference=data[1], systemA=data[2], systemB=data[3])
                new_item.save()
                data = []
                continue
            
            item = unicode(line, 'utf-8').strip('\n]')
            data.append(u' '.join(item.split()[1:]))

        if len(data) == 4:
            new_item = LucyItem(task=new_task, source=data[0],
              reference=data[1], systemA=data[2], systemB=data[3])
            new_item.save()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage(sys.argv[0])
        sys.exit(-1)
    
    main(sys.argv[1])
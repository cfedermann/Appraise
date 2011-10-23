# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
"""
import sys
import os
import re
import traceback
from django.template.loader import render_to_string

SYSTEM_NAMES = {'A': 'lucy', 'B': 'moses', 'C': 'trados', 'D': 'google'}

try:
    import settings # Assumed to be in the same directory.

except ImportError:
    sys.stderr.write("Error: Can't find the file 'settings.py' in the " \
      "directory containing %r. It appears you've customized things.\n" \
      "You'll have to run django-admin.py, passing it your settings " \
      "module.\n(If the file settings.py does indeed exist, it's causing" \
      " an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    PROJECT_HOME = os.path.normpath(os.getcwd() + "/../")
    sys.path.append(PROJECT_HOME)

    from evaluation.models import RankingTask, RankingItem, RankingResult, \
      ClassificationResult, EditingTask, EditingItem, EditingResult

    try:
        for task in RankingTask.objects.all():
            items = []
            errors = []
            start_id = 0
            
            for item in RankingItem.objects.filter(task=task).order_by('id'):
                try:
                    result = RankingResult.objects.filter(item=item)[0]
                
                except IndexError:
                    continue
                
                if not start_id:
                    start_id = item.id
                
                sentence_id = item.id - start_id + 1

                items.append({'id': item.id, 'user': result.user.username,
                  'source': item.source, 'sentence_id': sentence_id,
                  'rankA': result.rankA, 'systemA': item.systemA,
                  'rankB': result.rankB, 'systemB': item.systemB,
                  'rankC': result.rankC, 'systemC': item.systemC,
                  'rankD': result.rankD, 'systemD': item.systemD})
                 
                try:
                    error = ClassificationResult.objects.filter(item=item)[0]
                
                except IndexError:
                    continue
                
                errors.append({'id': item.id, 'user': error.user.username,
                  'source': item.source, 'system': error.system,
                  'system_text': getattr(item, 'system' + error.system),
                  'system_name': SYSTEM_NAMES[error.system],
                  'sentence_id': sentence_id,
                  'missing_content_words': error.missing_content_words,
                  'content_words_wrong': error.content_words_wrong,
                  'wrong_functional_words': error.wrong_functional_words,
                  'incorrect_word_forms': error.incorrect_word_forms,
                  'incorrect_word_order': error.incorrect_word_order,
                  'incorrect_punctuation': error.incorrect_punctuation,
                  'other_error': error.other_error,
                  'comments': error.comments})

            if items:
                data = {'shortname': task.shortname, 'items': items}
                xml = render_to_string('evaluation/ranking_item.xml', data)
                
                filename = '{0}-{1}-ranking.xml'.format(task.id,
                  task.shortname.encode('utf-8'))
                with open(filename, 'w') as xml_file:
                    xml_file.write(xml.encode('utf-8'))
                    print "Wrote {0}".format(filename)

            if errors:
                data = {'shortname': task.shortname, 'items': errors}
                xml = render_to_string('evaluation/classification_item.xml',
                  data)
                
                multiple_linebreaks = re.compile(r'(\n|\r\n)+', re.S)
                xml = multiple_linebreaks.sub('\n', xml)
                
                no_errors = re.compile(r'    <errors>\n    </errors>\n', re.S)
                xml = no_errors.sub('    <no-errors/>\n', xml)

                filename = '{0}-{1}-classification.xml'.format(task.id,
                  task.shortname.encode('utf-8'))
                with open(filename, 'w') as xml_file:
                    xml_file.write(xml.encode('utf-8'))
                    print "Wrote {0}".format(filename)

        for task in EditingTask.objects.all():
            items = []
            start_id = 0

            for item in EditingItem.objects.filter(task=task).order_by('id'):
                try:
                    result = EditingResult.objects.filter(item=item)[0]
                
                except IndexError:
                    continue
                
                if not start_id:
                    start_id = item.id
                
                sentence_id = item.id - start_id + 1

                items.append({'id': item.id, 'user': result.user.username,
                  'source': item.source, 'system': result.system,
                  'system_text': getattr(item, 'system' + result.system),
                  'system_name': SYSTEM_NAMES[result.system],
                  'sentence_id': sentence_id,
                  'postedited': result.postedited})

            if items:
                data = {'shortname': task.shortname, 'items': items}
                xml = render_to_string('evaluation/editing_item.xml', data)

                filename = '{0}-{1}-editing.xml'.format(task.id,
                  task.shortname.encode('utf-8'))
                with open(filename, 'w') as xml_file:
                    xml_file.write(xml.encode('utf-8'))
                    print "Wrote {0}".format(filename)
        
    except:
        print sys.stderr, "Exception in user code:"
        print sys.stderr, '-'*60
        traceback.print_exc(file=sys.stderr)
        print sys.stderr, '-'*60

    print

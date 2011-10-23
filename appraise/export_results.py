# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
"""
import sys
import os
import traceback

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

    from evaluation.models import RankingTask, RankingItem, RankingResult

    GLOBAL_RANKS = [0, 0, 0, 0, 0]
    GLOBAL_ITEMS = 0

    for task in RankingTask.objects.all():
        try:
            ranks = [0, 0, 0, 0, 0]
            items = len(RankingItem.objects.filter(task=task))
            for result in RankingResult.objects.filter(item__task=task):
                ranks[0] += result.rankA
                ranks[1] += result.rankB
                ranks[2] += result.rankC
                ranks[3] += result.rankD
                ranks[4] += 1
            
            if not ranks[4]:
                continue
            
            total_ranks = float(ranks[4])
            
            print "\nTask '{0}'\n".format(task.shortname.encode('utf-8'))
            print "Average rankA: {0:.5f}".format(ranks[0]/total_ranks)
            print "Average rankB: {0:.5f}".format(ranks[1]/total_ranks)
            print "Average rankC: {0:.5f}".format(ranks[2]/total_ranks)
            print "Average rankD: {0:.5f}".format(ranks[3]/total_ranks)
            print "     Rankings: {0}".format(ranks[4])
            print "        Items: {0}".format(items)
            print "    Completed: {0:.0f}%".format(100*ranks[4]/float(items))
            
            for i in range(5):
                GLOBAL_RANKS[i] += ranks[i]
            
            GLOBAL_ITEMS += items
        
        except:
            print "Exception in user code:"
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60

            continue
    
    TOTAL_GLOBAL = float(GLOBAL_RANKS[4])
    ITEMS_GLOBAL = float(GLOBAL_ITEMS)
    
    print "\nOverall Result\n"
    print "Average rankA: {0:.5f}".format(GLOBAL_RANKS[0]/TOTAL_GLOBAL)
    print "Average rankB: {0:.5f}".format(GLOBAL_RANKS[1]/TOTAL_GLOBAL)
    print "Average rankC: {0:.5f}".format(GLOBAL_RANKS[2]/TOTAL_GLOBAL)
    print "Average rankD: {0:.5f}".format(GLOBAL_RANKS[3]/TOTAL_GLOBAL)
    print "     Rankings: {0}".format(GLOBAL_RANKS[4])
    print "        Items: {0}".format(GLOBAL_ITEMS)
    print "    Completed: {0:.0f}%".format(100*GLOBAL_RANKS[4]/ITEMS_GLOBAL)
    
    print

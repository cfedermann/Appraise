# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
"""
import sys
import os
import traceback
from decimal import *

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
    
    def _create_category_label(ranking):
        """Returns the category label for the given ranking."""
        return '{0}{1}{2}{3}'.format(chr(65+ranking[0]), chr(65+ranking[1]),
          chr(65+ranking[2]), chr(65+ranking[3]))

    RANKS = [
      [0,1,2,3], [0,1,3,2],
      [0,2,1,3], [0,2,3,1],
      [0,3,1,2], [0,3,2,1],

      [1,0,2,3], [1,0,3,2],
      [1,2,0,3], [1,2,3,0],
      [1,3,0,2], [1,3,2,0],

      [2,0,1,3], [2,0,3,1],
      [2,1,0,3], [2,1,3,0],
      [2,3,0,1], [2,3,1,0],

      [3,0,1,2], [3,0,2,1],
      [3,1,0,2], [3,1,2,0],
      [3,2,0,1], [3,2,1,0]
    ]
    
    CATEGORY_PER_ITEM = {}
    for rank in RANKS:
        _label = _create_category_label(rank)
        CATEGORY_PER_ITEM[_label] = 0
    
    RANKS_PER_SYSTEM = {'DCU': [], 'DFKI-A': [], 'DFKI-B': [], 'MANY': []}
    KAPPA_DATA = []
    N_BEST = 146
    
    KAPPA_FOUR_DATA = []
    
    for i in range(N_BEST):
        KAPPA_DATA.append({})
        KAPPA_FOUR_DATA.append({'A': 0, 'B': 0, 'C': 0, 'D': 0})
        for rank in RANKS:
            _label = _create_category_label(rank)
            KAPPA_DATA[i][_label] = 0

    for task in RankingTask.objects.all():
        try:
            for key in ('DCU', 'DFKI-A', 'DFKI-B', 'MANY'):
                RANKS_PER_SYSTEM[key].append([0, 0, 0, 0])
            
            ranks = [0, 0, 0, 0, 0]
            items = len(RankingItem.objects.filter(task=task))
            for result in RankingResult.objects.filter(item__task=task).order_by('item__id'):
                ranks[0] += result.rankA
                ranks[1] += result.rankB
                ranks[2] += result.rankC
                ranks[3] += result.rankD
                ranks[4] += 1
                
                if ranks[4] < N_BEST+1:
                    _label = _create_category_label([result.rankA-1,
                      result.rankB-1,result.rankC-1,result.rankD-1])
                    
                    KAPPA_DATA[ranks[4]-1][_label] += 1
                    
                    _allowed_ranks = [1]
                    if result.rankA in _allowed_ranks:
                        KAPPA_FOUR_DATA[ranks[4]-1]['A'] += 1
                    if result.rankB in _allowed_ranks:
                        KAPPA_FOUR_DATA[ranks[4]-1]['B'] += 1
                    if result.rankC in _allowed_ranks:
                        KAPPA_FOUR_DATA[ranks[4]-1]['C'] += 1
                    if result.rankD in _allowed_ranks:
                        KAPPA_FOUR_DATA[ranks[4]-1]['D'] += 1
                    
                    CATEGORY_PER_ITEM[_label] += 1
                    
                    RANKS_PER_SYSTEM['DCU'][-1][result.rankA-1] += 1
                    RANKS_PER_SYSTEM['DFKI-A'][-1][result.rankB-1] += 1
                    RANKS_PER_SYSTEM['DFKI-B'][-1][result.rankC-1] += 1
                    RANKS_PER_SYSTEM['MANY'][-1][result.rankD-1] += 1
            
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
    
    for key in ('DCU', 'DFKI-A', 'DFKI-B', 'MANY'):
        _ranks = [0, 0, 0, 0]
        for ranks in RANKS_PER_SYSTEM[key]:
            for i in range(4):
                _ranks[i] += ranks[i]
        print '{0}:\t{1}'.format(key, _ranks)
        print '\t\t{0}'.format(RANKS_PER_SYSTEM[key])
    
    _keys = '\t'.join([str(x) for x in CATEGORY_PER_ITEM.keys()])
    _values = '\t'.join([str(CATEGORY_PER_ITEM[x]) for x in CATEGORY_PER_ITEM.keys()])
    _probs = '\t'.join(['{0:.5f}'.format(CATEGORY_PER_ITEM[x]/315.) for x in CATEGORY_PER_ITEM.keys()])
    
    print '-' * 24*8
    print _keys
    print _values
    print _probs
    print '-' * 24*8

    _pj = {}
    for rank in RANKS:
        _label = _create_category_label(rank)
        _pj[_label] = 0
    _pj_red = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    _pj_four = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    
    _pi = []
    _pi_red = []
    _pi_four = []
    
    for i in range(N_BEST):
        _pi.append(0)
        _pi_red.append(0)
        _pi_four.append(Decimal(0))
        
        for k,v in KAPPA_DATA[i].items():
            _pj[k] += v
            _pi[-1] += v*v
            
            _pj_red[k[0].upper()] += v
        
        for k,v in KAPPA_FOUR_DATA[i].items():
            _pj_four[k] += Decimal(v)
            _pi_four[-1] += Decimal(v)*Decimal(v)
        
        _red = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        for k,v in KAPPA_DATA[i].items():
            _red[k[0].upper()] += v
        
        _pi_red[-1] = _red['A'] * _red['A'] + _red['B'] * _red['B'] \
                    + _red['C'] * _red['C'] + _red['D'] * _red['D']
        
        _pi[-1] -= 3
        _pi[-1] /= 6.
        
        _pi_red[-1] -= 3
        _pi_red[-1] /= 6.
        
        _pi_four[-1] -= Decimal(3)
        _pi_four[-1] /= Decimal(6)

        _keys = '\t'.join([str(x) for x in KAPPA_FOUR_DATA[i].keys()])
        _values = '\t'.join([str(KAPPA_FOUR_DATA[i][x]) for x in KAPPA_FOUR_DATA[i].keys()])
        
        _keys += '\tPi'
        _values += '\t{0:.5f}'.format(_pi_four[-1])
        
#        print _keys
        print _values

    _pjs = '\t'.join(['{0:.5f}'.format(_pj_four[x]/Decimal(N_BEST * 3.)) for x in _pj_four.keys()])
    print '-' * 24*8
    print _pjs
    
    PE = 0
    for x in _pj.keys():
        _pe = _pj[x]/(N_BEST * 3.)
        PE += _pe * _pe
    
    P = 0
    for i in range(N_BEST):
        P += _pi[i]
    
    P /= float(N_BEST)
    
    K = (P - PE) / (1.0 - PE)

    PE_red = 0
    for x in _pj_red.keys():
        _pe_red = Decimal(_pj_red[x])/Decimal(N_BEST * 3.)
        PE_red += _pe_red * _pe_red
    
    P_red = 0
    for i in range(N_BEST):
        P_red += Decimal(_pi_red[i])
    
    P_red /= Decimal(N_BEST)
    
    K_red = (P_red - PE_red) / (Decimal(1) - PE_red)
    
    PE_four = 0
    for x in _pj_four.keys():
        
        _pe_four = _pj_four[x]/Decimal(N_BEST * 3.)
        PE_four += _pe_four * _pe_four
    
    P_four = 0
    for i in range(N_BEST):
        P_four += _pi_four[i]
    
    P_four /= Decimal(N_BEST)
    
    K_four = (P_four - PE_four) / (Decimal(1) - PE_four)
    
    print
    print "PE: {0:.10f}".format(PE)
    print " P: {0:.10f}".format(P)
    print "-" * 16
    print " K: {0:.10f}".format(K)
    print
    print "PE_red: {0:.10f}".format(PE_red)
    print " P_red: {0:.10f}".format(P_red)
    print "-" * 20
    print " K_red: {0:.10f}".format(K_red)
    print
    print "PE_four: {0:.10f}".format(PE_four)
    print " P_four: {0:.10f}".format(P_four)
    print "-" * 20
    print " K_four: {0:.10f}".format(K_four)
    
    print 'data = numpy.array(['
    for i in range(N_BEST):
        print '{0},'.format(KAPPA_DATA[i].values())
    print '])'

    print 'data = numpy.array(['
    for i in range(N_BEST):
        print '{0},'.format(KAPPA_FOUR_DATA[i].values())
    print '])'
    
    
    # cfedermann: we also can directly compute K for four categories, "A is best", "B is best", etc.
    # This means k=4, n=3, N=105 and _should_ result in a score similar to K_red
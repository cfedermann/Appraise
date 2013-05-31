# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>
"""
import logging
from datetime import timedelta
from nltk.metrics.agreement import AnnotationTask

log = logging.getLogger(__file__)

def datetime_to_seconds(value):
    """
    Converts the given datetime value to seconds.
    """
    seconds = value.hour * 3600 + value.minute * 60 \
      + value.second + (value.microsecond / 1000000.0)
    return seconds


def seconds_to_timedelta(value):
    """
    Converst the given value in secodns to datetime.timedelta.
    """
    _days =  value / 86400
    _hours = (value / 3600) % 24
    _mins = (value / 60) % 60
    _secs = value % 60
    return timedelta(days=_days, hours=_hours, minutes=_mins, seconds=_secs)

# pylint: disable-msg=E0102
class AnnotationTask(AnnotationTask):
    """
    Makes sure that agr() works correctly for unordered input.
    
    This would have returned a wrong value (0.0) in @785fb79 as coders are in
    the wrong order. Subsequently, all values for pi(), S(), and kappa() would
    have been wrong as they are computed with avg_Ao().
    >>> t1 = AnnotationTask(data=[('b','1','stat'),('a','1','stat')])
    >>> t1.avg_Ao()
    1.0
    
    """
    # pylint: disable-msg=C0103,W0221
    def agr(self, cA, cB, i, data=None):
        """Agreement between two coders on a given item
        
        """
        data = data or self.data
        k1 = (x for x in data if x['coder'] in (cA, cB) and x['item']==i).next()
        if k1['coder'] == cA:
            k2 = (x for x in data if x['coder']==cB and x['item']==i).next()
        else:
            k2 = (x for x in data if x['coder']==cA and x['item']==i).next()

        ret = 1.0 - float(self.distance(k1['labels'], k2['labels']))
        log.debug("Observed agreement between %s and %s on %s: %f",
                      cA, cB, i, ret)
        log.debug("Distance between \"%r\" and \"%r\": %f",
                      k1['labels'], k2['labels'], 1.0 - ret)
        return ret

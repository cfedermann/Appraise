# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
"""
def datetime_to_seconds(value):
    """
    Converts the given datetime value to seconds.
    """
    seconds = value.hour * 3600 + value.minute * 60 \
      + value.second + (value.microsecond / 1000000.0)
    return seconds
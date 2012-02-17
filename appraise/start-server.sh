#!/bin/bash
#
# Project: Appraise evaluation system
#  Author: Christian Federmann <cfedermann@dfki.de>

PROJECT_ROOT=`pwd`
DJANGO_PID="$PROJECT_ROOT/django.pid"
LIGHTTPD_PID="$PROJECT_ROOT/lighttpd.pid"

if [ -f $DJANGO_PID ]; then
    kill -9 `cat -- $DJANGO_PID`
    rm -f -- $DJANGO_PID
fi

if [ -f $LIGHTTPD_PID ]; then
    kill -9 `cat -- $LIGHTTPD_PID`
    rm -f -- $LIGHTTPD_PID
fi

/share/emplus/website/python26/bin/python manage.py runfcgi host=134.96.187.245 port=7070 method=threaded pidfile=$DJANGO_PID
/share/emplus/website/lighttpd/sbin/lighttpd -f /share/emplus/website/lighttpd/etc/appraise.conf

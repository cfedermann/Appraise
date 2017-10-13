#!/bin/bash
#
# Project: Appraise evaluation system
#  Author: Christian Federmann <cfedermann@gmail.com>

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

# Adapt and uncomment the following two lines to actually start the server.
# An example appraise.conf can be found in examples/appraise-lighttpd.conf
#
# /path/to/bin/python manage.py runfcgi host=127.0.0.1 port=1234 method=threaded pidfile=$DJANGO_PID
# /path/to/sbin/lighttpd -f /path/to/lighttpd/etc/appraise.conf

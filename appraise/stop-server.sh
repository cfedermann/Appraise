#!/bin/bash
#
# Project: Appraise evaluation system
#  Author: Christian Federmann <cfedermann@gmail.com>

PROJECT_ROOT=`pwd`
DJANGO_PID="$PROJECT_ROOT/django.pid"
LIGHTTPD_PID="$PROJECT_ROOT/lighttpd.pid"

if [ -f $DJANGO_PID ]; then
    kill -9 `cat $DJANGO_PID`
    rm -f $DJANGO_PID
fi

if [ -f $LIGHTTPD_PID ]; then
    kill -9 `cat $LIGHTTPD_PID`
    rm -f $LIGHTTPD_PID
fi

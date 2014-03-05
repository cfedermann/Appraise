#!/usr/bin/env python

import sys

for fileno,file in enumerate(sys.argv[1:]):
    for i,line in enumerate(open(file)):
        if i == 0 and fileno > 0:
            continue
        print line,

            

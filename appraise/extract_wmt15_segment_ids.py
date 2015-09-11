#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>
"""
import argparse

PARSER = argparse.ArgumentParser(description="Extracts segment IDs from a " \
  "given CSV file in WMT15 format.")
PARSER.add_argument("csv_file", metavar="csv-file", help="CSV file(s) " \
  "containing WMT15 results.  Can be multiple files using patterns such as " \
  " '*.xml' or similar.", nargs='+')
PARSER.add_argument("output", type=str, help="output file")


if __name__ == "__main__":
    args = PARSER.parse_args()

    all_segment_ids = set()

    for _csv_file in args.csv_file:
        results_csv_string = None
        with open(_csv_file) as infile:
            first_line = unicode(infile.readline(), 'utf-8')
            if not 'segmentid' in first_line.lower():
                print 'Unknown CSV format, cannot process: {0}'.format(_csv_file)

            header_fields = first_line.lower().split(',')
            segment_index = header_fields.index('segmentid')

            for current_line in infile:
                current_fields = current_line.split(',')
                current_segment_id = current_fields[segment_index]
                all_segment_ids.add(current_segment_id)

    sorted_segment_ids = list([int(x) for x in all_segment_ids])
    sorted_segment_ids.sort()

    out = open(args.output, 'w')
    out.write(u'\n'.join([str(x) for x in sorted_segment_ids]).encode('utf-8'))
    out.close()

    print 'Wrote {0} IDs to {1}'.format(len(sorted_segment_ids), args.output)

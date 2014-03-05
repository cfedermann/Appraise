#!/usr/bin/perl
# Closes batches that have been completely rejected or approved.

use strict;
use warnings;
use File::Basename qw/dirname/;

chomp(my @files = `find . -name '*.success'`);

foreach my $file (@files) {
  my $results_file = dirname($file) . "/mturk-results.txt";
  next unless (-e $results_file);
  chomp(my $remaining = `tail -n+2 $results_file | cut -f21 | grep -v Approved | grep -v Rejected | grep -v "^\$" | wc -l`);
  if ($remaining == 0) {
    print "FINISHED $file -> $file.done\n";
    system("mv $file $file.done");
  }
}

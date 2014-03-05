#!/usr/bin/perl

use strict;
use warnings;

if (@ARGV != 3) {
  print "Usage: make-batch.sh BATCHNO SOURCE TARGET\n";
  exit;
}
my ($batchno,$source,$target) = @ARGV;

my $pair="$source-$target";
mkdir($pair) unless -d $pair;

my $outfile = "$pair/$pair-batch$batchno.txt";
die "Cowardly refusing to create batch $outfile (already exists)" if -e $outfile;

my %langs = (
	en => 'eng',
	ru => 'rus',
	cs => 'cze',
	fr => 'fre',
	de => 'deu',
	es => 'spa' );

my $plaindir = "$ENV{HOME}/expts/wmt13/data/wmt13-data/plain";

my $cmd = "python ~/code/Appraise/scripts/wmt_ranking_task.py $plaindir/sources/newstest2013-src.$source $plaindir/references/newstest2013-ref.$target $plaindir/system-outputs/newstest2013/$pair/newstest2013.$pair.* -source $langs{$source} -target $langs{$target} -no-sequential -controls controls/$pair/controls.txt -control_prob 0.5 -redundancy 0 > $outfile";

#print "$cmd\n";
system($cmd);

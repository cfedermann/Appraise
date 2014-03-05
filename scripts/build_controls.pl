#!/usr/bin/perl

use strict;
use warnings;

my %langs = (
  German => 'de',
  Russian => 'ru',
  Spanish => 'es',
  Czech => 'cs',
  French => 'fr',
);

# Researcher dump file
#my $dump = "~/Dropbox/research/WMT13/wmt13-export-20130604a.txt";
my $dump = "/Users/post/Dropbox/research/WMT13/wmt13-export-20130630.txt";

foreach my $lang (keys(%langs)) {
  my $shortlang = $langs{$lang};

  system("mkdir","-p","controls/$shortlang-en") unless -d "controls/$shortlang-en";
  system("mkdir","-p","controls/en-$shortlang") unless -d "controls/en-$shortlang";

  die "problem with $shortlang-en" if system("perl $ENV{APPRAISE}/scripts/find-agreed-rankings.pl $lang,English $dump ~/expts/wmt13/data/maxlen30/$shortlang-en/newstest2013-src.$shortlang ~/expts/wmt13/data/maxlen30/$shortlang-en/newstest2013-ref.en ~/expts/wmt13/data/maxlen30/$shortlang-en/newstest2013.$shortlang-en.> controls/$shortlang-en/controls.txt");

  die "problem with en-$shortlang" if system("perl $ENV{APPRAISE}/scripts/find-agreed-rankings.pl English,$lang $dump ~/expts/wmt13/data/maxlen30/en-$shortlang/newstest2013-src.en ~/expts/wmt13/data/maxlen30/en-$shortlang/newstest2013-ref.$shortlang ~/expts/wmt13/data/maxlen30/en-$shortlang/newstest2013.en-$shortlang.> controls/en-$shortlang/controls.txt");
}

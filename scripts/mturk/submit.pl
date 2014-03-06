#!/usr/bin/perl

use strict;
use warnings;
use Getopt::Std;

my $MTURK="/Users/post/code/aws-mturk-clt-1.3.1";
my $HOME = $ENV{HOME};

my %opts;
getopts('r:RS', \%opts);

my $REWARD = $opts{r} || '0.25';
if ($REWARD < 0.25 || $REWARD > 0.5) {
  print STDERR "* Invalid reward '$REWARD'\n";
  exit;
}
print "REWARD: $REWARD\n";

if (@ARGV < 2) {
  print STDERR "Usage: submit.pl from to batchno\n";
  exit;
}
my ($from, $to, $batchno) = @ARGV;

my %langs = (
  cs => 'Czech',
  de => 'German',
  en => 'English',
  fr => 'French',
  es => 'Spanish',
  ru => 'Russian',
);

if (! exists $langs{$from}) {
  print STDERR "invalid from lang $from\n";
  exit;
}
if (! exists $langs{$to}) {
  print STDERR "invalid to lang $to\n";
  exit;
}

if (! (exists $opts{S} xor exists $opts{R})) {
  print STDERR "I need exactly one of -R (real turk) or -S (sandbox)\n";
  exit 1;
}

my $pair = "$from-$to";
if (! defined $batchno) {
  chomp(my $lastbatch = `ls $pair | grep batch | perl -pe 's/batch//' | sort -n | tail -n1`);
  $lastbatch = 0 if not defined $lastbatch;
  $batchno = $lastbatch + 1;
  print "auto batch $pair $batchno\n";
}

my $zerobatchno = $batchno - 1;
my $oldbatchfile = "$HOME/Dropbox/research/WMT13/mturk-appraise-ids/mturk.$pair.csv.batch$zerobatchno";
if (! -e $oldbatchfile) {
  print STDERR "* FATAL: No batch of appraise IDs found for $pair/$batchno ($oldbatchfile)\n";
  exit;
}

mkdir($pair) unless -d $pair;
my $dir = "$pair/batch$batchno";
mkdir($dir) unless -d $dir;

my $batchfile = "$dir/$pair.batch$batchno.input";
if (-e $batchfile) {
  print STDERR "Refusing to copy over existing file $batchfile\n";
  exit;
}
system("cat $oldbatchfile | perl -pe 's/,.*//' > $batchfile");

my $prop_file = "$dir/$from-$to.batch$batchno.properties";
system("cat ../input/template.properties | perl -pe 's/<SOURCE>/$langs{$from}/g; s/<TARGET>/$langs{$to}/g; s/<REWARD>/$REWARD/' > $prop_file");

my $question_file = "$dir/$pair.batch$batchno.question";
system("cat ../input/template.question > $question_file");

my $sandbox = $opts{R} ? "" : "-sandbox";
my $cmd = "$MTURK/bin/loadHITs.sh $sandbox -input $batchfile -properties $prop_file -question $question_file";
print "$cmd\n";
system($cmd);

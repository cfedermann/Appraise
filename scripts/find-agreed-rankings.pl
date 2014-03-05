#!/usr/bin/perl

# This script takes the manual judgment data and finds sentences with a high degree of agreement on
# the rankings.  The input data is a summary of the ranking tasks, output by Omar's ranking analysis
# tool in Maise, and having the following format:
# 
#   srclang,trglang,srcIndex,documentId,segmentId,judgeId,system1Number,system1Id,system2Number,system2Id,system3Number,system3Id,system4Number,system4Id,system5Number,system5Id,system1rank,system2rank,system3rank,system4rank,system5rank
#
# The first row is this header row.  From this, we compute a variety of statistics useful for
# embedding controls within Maise.


use strict;
use warnings;

if (@ARGV != 5) {
  print "Usage: find-agreed-rankings.pl <LANG_PAIR> <RANK_FILE> <SOURCE_FILE> <REFERENCE_FILE> <SYSTEMS_PREFIX>\n";
  exit;
}
my ($langpair,$ranking_file,$source_file,$ref_file,$systems_prefix) = @ARGV;

#
# Read in all the sentences
#
my %sentences = (
	source => read_lines($source_file),
	reference => read_lines($ref_file),
);

print STDERR "Found " . scalar(keys %{$sentences{source}}) . " source sentences in '$source_file'.\n";
print STDERR "Found " . scalar(keys %{$sentences{reference}}) . " references in '$ref_file'.\n";

if (scalar(keys %{$sentences{source}}) != scalar(keys %{$sentences{reference}})) {
  print STDERR "* FATAL: source and reference sentence counts don't match\n";
  exit;
}

my @system_files = glob("$systems_prefix*");
foreach my $file (@system_files) {
	my $system = (split(/\//,$file))[-1];
	$sentences{$system} = read_lines($file);
	print STDERR "Found " . scalar(keys %{$sentences{$system}}) . " sentences for $system in '$file'.\n";
}
$sentences{_ref} = $sentences{reference};

# 
# Read in all the rankings.
#
open RANK, $ranking_file or die "ranking_file?";
chomp(my $header = <RANK>);
$header =~ s/\r\n//g;
my @columns = split(',', $header);

# raw_ranks records, for each sentence, the number of times that system A was recorded as being
# better than (= having a lower score than) system B.  The rankings are recorded as paired keys.
my %raw_ranks;

# this counts the number of lines matching the requested language pair.
my $matching_lines = 0;

# this stores the matching HITs as they are read in.  actually, they're not HITs, but ranking tasks.
my %HITS;
while (my $line = <RANK>) {
  last if $line eq "";

	# filter to just the language pair we care about
	next unless $line =~ /^$langpair/;

	# skip references
  # next if $line =~ /_ref/;

	$matching_lines++;

  my %hit = build_hit($line);

  # We only need one instead of each HIT, so enter one as the archetype
  my $hitstr = "$hit{segmentId} $hit{system1Id} $hit{system2Id} $hit{system3Id} $hit{system4Id} $hit{system5Id}";
  $HITS{$hitstr} = \%hit;

  my @systems = ($hit{system1Id},$hit{system2Id},$hit{system3Id},$hit{system4Id},$hit{system5Id});
  my @ranks   = ($hit{system1rank},$hit{system2rank},$hit{system3rank},$hit{system4rank},$hit{system5rank});
	my $sentno = $hit{srcIndex};
#  print "$sentkey " . join("  ", @systems) . "  " . join("-", @ranks) . $/;

  # consider all pairs, mark a vote for each outranking
  for (my $i = 0; $i < @systems; $i++) {
		for (my $j = 0; $j < @systems; $j++) {
			# a lower rank corresponds to a higher rating
			if ($ranks[$i] < $ranks[$j]) {
				$raw_ranks{$sentno}{$systems[$i],$systems[$j]}++;
			}
		}
  }
}
close(RANK);

if ($matching_lines == 0) {
	print "* FATAL: Found no lines matching language pair '$langpair'\n";
	exit;
}

# score the entries so they can be sorted
foreach my $hit (values(%HITS)) {
  my @systems = ($hit->{system1Id},$hit->{system2Id},$hit->{system3Id},$hit->{system4Id},$hit->{system5Id});
  my @ranks   = ($hit->{system1rank},$hit->{system2rank},$hit->{system3rank},$hit->{system4rank},$hit->{system5rank});
	my $sentno = $hit->{srcIndex};

  # Score the HIT using the summed counts over all HIT tokens of this type stored in raw_ranks
	$hit->{score} = 0;
	for my $i (0..4) {
		for my $j (($i+1)..4) {
			my $count1 = $raw_ranks{$sentno}{$systems[$i],$systems[$j]} || 0;
			my $count2 = $raw_ranks{$sentno}{$systems[$j],$systems[$i]} || 0;
			$hit->{score} += abs($count1 - $count2);
		}
	}
}

# now print everything out
HIT: foreach my $hit (sort { $b->{score} <=> $a->{score} } values(%HITS)) {
  my @systems = ($hit->{system1Id},$hit->{system2Id},$hit->{system3Id},$hit->{system4Id},$hit->{system5Id});
  my @ranks   = ($hit->{system1rank},$hit->{system2rank},$hit->{system3rank},$hit->{system4rank},$hit->{system5rank});

  my $langpair = "$hit->{srclang},$hit->{trglang}";
  my $sentno   = $hit->{srcIndex};
  my $sentkey  = "$langpair,$sentno";
  # print "SENTKEY $sentkey " . join("  ", @systems) . "  " . join("-", @ranks) . $/;

  # Skip this HIT if we don't have files for all the systems
  foreach my $system (@systems) {
    if (! defined $sentences{$system}) {
      print STDERR "* SKIPPING HIT with missing system '$system'\n";
      next HIT;
    }
  }

	print "SENTENCE $sentno\n";
	print "SOURCE $sentences{source}{$sentno}\n";
	print "REFERENCE $sentences{reference}{$sentno}\n";
	print "SYSTEMS " . join(" ", @systems) . "\n";
	for my $i (0..4) {
		my $sent = $sentences{$systems[$i]}{$sentno};
		if (! defined $sent) {
			print STDERR "* FATAL: no sentence $sentno for system $systems[$i]\n";
			exit;
		}
		print "$sent\n";
	}

	my $score = 0;
   # consider all pairs, mark a vote for each outranking
  for (my $i = 0; $i < @systems; $i++) {
		for (my $j = 0; $j < @systems; $j++) {
			if ($i == $j) {
				print "- ";
			} else {
				my $count = $raw_ranks{$sentno}{$systems[$i],$systems[$j]} || 0;
				print "$count ";
			}
		}
		print "\n";
	}
}
close(RANK);

print STDERR "Printed statistics for $matching_lines systems\n";

## SUBROUTINES #######################################################

sub build_hit {
  my ($line) = @_;

  $line =~ s/\s+$//;

  my %hit;

  chomp(my @tokens = split(',', $line));
  if (scalar @tokens != scalar @columns) {
		print "* FATAL: wrong number of columns at line $.\n";
		exit;
  }
  for my $i (0..$#tokens) {
		$hit{$columns[$i]} = $tokens[$i];
  }

	return %hit;
}


sub read_lines {
	my ($file) = @_;
	my %hash;

	open READ, $file or die "$file?";
	while (<READ>) {
		chomp;
		$hash{$.} = $_;
	}
	close READ;

	return \%hash;
}

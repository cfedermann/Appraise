#!/usr/bin/perl

open GOOD, "turkers.good" or die;
while (<GOOD>) {
  chomp;
  $good{$_} = 1;
}
close GOOD;

while (my $line = <>) {
  if ($. == 1) {
    print $line;
    next;
  }
  chomp($line);

  my @tokens = split(',', $line);
  my $worker = $tokens[5];

  if (exists $good{$worker}) {
    print $line . $/;
  }
}

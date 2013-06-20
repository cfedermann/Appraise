#!/usr/bin/perl -w

use strict;

my $DEBUG = 0;
my $num_resample = 100;

$|=1;

die("\n\tusage: $0 <srcfile>\n\n") if scalar @ARGV < 1;
my $srcfile = "";
foreach (@ARGV) {
  $srcfile .= $_ . " ";
}

my @LOG_FACTORIAL = (0,0);

# load data
my %TASK_PROB;
my %SENTENCE;
my %INDEX;
&load("cat $srcfile |", \%TASK_PROB);

print "task,cluster_id,exp-win-ratio,exp-rank-range,system_id\n";

# rank
foreach my $l ("Spanish","German","French","Czech","Russian") {
  my $task = "$l-English";
###  print "====\n$task\n====\n";
  die($task) if !defined($TASK_PROB{$task});
  &rank_by_expected_wins($task,$TASK_PROB{$task});

  $task = "English-$l";
###  print "====\n$task\n====\n";
  die($task) if !defined($TASK_PROB{$task});
  &rank_by_expected_wins($task,$TASK_PROB{$task});
}

sub rank_by_expected_wins {
  my ($task,$P) = @_;
  my @SYSTEM = keys %{$P};

  my %SUM_WINS;
  foreach my $p1 (@SYSTEM) {
    foreach my $p2 (@SYSTEM) {
      next if $p1 eq $p2;
      if (defined($$P{$p1}) && defined($$P{$p1}{$p2})) {
        $SUM_WINS{$p1} += $$P{$p1}{$p2};
      }
    }
  }

  my %RANGE;
  &bootstrap($task,\%RANGE);
  my @OUT;
  foreach (@SYSTEM) {
    push @OUT,sprintf("%5.3f (%s): %s",$SUM_WINS{$_}/(scalar(@SYSTEM)-1),$RANGE{$_},$_);
  }
  my $last_rank = 99;
  my $cluster_count = 1;
  foreach (reverse sort @OUT) {
    /^([\d\.]+) \(([\d\-]+)\): (.+)$/;
    my ($from,$to) = split(/\-/,$2);
    if ($from > $last_rank) {
###      print "      ------------------\n";
      $cluster_count++;
    }
    $last_rank = defined($to) ? $to : $from;
###    print $_."\n";
    print "$task,$cluster_count,$1,$2,$3\n";
  }
###  print "number of clusters: $cluster_count (".(scalar(@SYSTEM))." systems)\n";
}

sub bootstrap {
  my ($task,$RANGE) = @_;
  my %RANK;
  
  for(my $i=0;$i<$num_resample;$i++) {
###    print ".";
    my %P;
    &resample($task,\%P);
    my @SYSTEM = keys %{$P{$task}};
    my %SUM_WINS;
    foreach my $p1 (@SYSTEM) {
      foreach my $p2 (@SYSTEM) {
        next if $p1 eq $p2;
        if (defined($P{$task}) && defined($P{$task}{$p1}) && defined($P{$task}{$p1}{$p2})) {
          $SUM_WINS{$p1} += $P{$task}{$p1}{$p2};
        }
      }
    }
    
    my @OUT;
    foreach (@SYSTEM) {
      push @OUT,sprintf("%.4f %s",$SUM_WINS{$_}/(scalar(@SYSTEM)-1),$_);
    }
    my $rank = 1;
    foreach (reverse sort @OUT) {
      my($score,$system) = split;
      $RANK{$system}{$rank}++;
      $rank++;
    }
  }
###  print "\n";
  my @SYSTEM = keys %RANK;
###  print "Bootstrapped ranks:\n";
  foreach my $system (sort @SYSTEM) {
###    printf "%20s: ",substr($system,0,20);
    my ($max_rank,$max_prob) = (-1,0);
    foreach my $rank (sort { $a <=> $b } keys %{$RANK{$system}}) {
      my $prob = $RANK{$system}{$rank};
      if ($prob > $max_prob) {
        $max_prob = $prob;
        $max_rank = $rank;
      }
###      printf(" %d:%.1f%s ",$rank,$RANK{$system}{$rank}/$num_resample*100,'%');
    }
    my $total_prob = $max_prob;
    my ($start,$end) = ($max_rank,$max_rank);
    while($total_prob < $num_resample*.95) {
      if (! defined($RANK{$system}{$start-1})) {
        $end++; 
        $total_prob += $RANK{$system}{$end};
      }
      elsif(! defined($RANK{$system}{$end+1})) {
        $start--;
        $total_prob += $RANK{$system}{$start};
      }
      elsif($RANK{$system}{$start-1} > $RANK{$system}{$end+1}) {
        $start--;
        $total_prob += $RANK{$system}{$start};          
      }
      else {
        $end++; 
        $total_prob += $RANK{$system}{$end};         
      }
    }
    if ($start == $end) {
      $$RANGE{$system} = $start;
    }
    else {
      $$RANGE{$system} = "$start-$end";
    }
###    print " => $start-$end ($total_prob)\n";
  }
###  print "\nRanking (with expected win ratio and rank range):\n";
}

sub compute_probability {
  my ($win,$loss) = @_;
  my $total = $win + $loss;
  return $win / $total;
}

sub load {
  my ($file,$P) = @_;
  
  # get index
  open(FILE,$file);
  my $index = <FILE>;
  $index =~ s/[\t\r\n]//g;
  %INDEX = ();
  foreach (split(/,/,$index)) {
    #print "INDEX{$_} = ".(scalar keys %INDEX)."\n";
    $INDEX{$_} = scalar keys %INDEX;
  }
  
  # read
  my (%WIN,%TOTAL);
  while(<FILE>) {
    next if /^srclang/; # happens when multiple files are loaded
    s/[\t\r\n]//g;
    my @DATA = split(/,/);
    my $task = &get_task(\@DATA);
    push @{$SENTENCE{$task}}, $_;
    &process_judgment($task,\@DATA,\%WIN,\%TOTAL);
  }
  close(FILE);
  
  foreach my $task (sort keys %TOTAL) {
    &compute_win_ratio($task,$P,\%WIN,\%TOTAL);
    &pairwise($task,\%WIN,\%TOTAL);
  }
}

sub resample {
  my ($task,$P) = @_;
  
  my (%WIN,%TOTAL);
  #print "resample ".(scalar @{$SENTENCE{$task}})." times.\n";
  for(my $i=0;$i<scalar @{$SENTENCE{$task}};$i++) {
    my @DATA = split(/,/,$SENTENCE{$task}[rand(scalar @{$SENTENCE{$task}})]);
    &process_judgment($task,\@DATA,\%WIN,\%TOTAL);
  }
  &compute_win_ratio($task,$P,\%WIN,\%TOTAL);
}

sub compute_win_ratio {
  my ($task,$P,$WIN,$TOTAL) = @_;
  foreach my $system1 (sort keys %{$$TOTAL{$task}}) {
    foreach my $system2 (sort keys %{$$TOTAL{$task}{$system1}}) {
      my $win = 0;
      $win = $$WIN{$task}{$system1}{$system2} if defined($$WIN{$task}{$system1}{$system2});
      my $loss = $$TOTAL{$task}{$system1}{$system2}-$win;
      $$P{$task}{$system1}{$system2} = &compute_probability($win,$loss);
    }
  }
}

sub pairwise {
  my ($task,$WIN,$TOTAL) = @_;
  my %DISTINCTION = ( 0 => 0, 1 => 0, 2 => 0, 3 => 0);
###  print "\n=== $task ===\n";
###  printf "%10s ","";
  foreach my $system2 (sort keys %{$$TOTAL{$task}}) {
###    printf " %7s",substr($system2,0,7);
  }
###  print "\n";
  foreach my $system1 (sort keys %{$$TOTAL{$task}}) {
    my (%FIRST,%SECOND);
    foreach my $system2 (sort keys %{$$TOTAL{$task}}) {
      if ($system1 eq $system2) {
        $FIRST{$system2} = sprintf("%7s",substr($system2,0,7));
        $SECOND{$system2} = sprintf("%7s",substr($system2,0,7));
        next;
      }
      my $win = 0;
      $win = $$WIN{$task}{$system1}{$system2} if defined($$WIN{$task}{$system1}{$system2});
      my $loss = 0;
      $loss = $$TOTAL{$task}{$system1}{$system2}-$win if defined($$TOTAL{$task}{$system1}{$system2});
      my $p_value = &compute_p_value($win,$loss);
#print "$task $system1 $system2 $p_value\n" if $ratio == 1;
      my $distinction = "";
      my $symbol = ($win > $loss) ? "*" : "-";
      $distinction .= $symbol if $p_value <= 0.1;
      $distinction .= $symbol if $p_value <= 0.05;
      $distinction .= $symbol if $p_value <= 0.01;
      $FIRST{$system2} = sprintf("%3d/%3d",$win,$loss);
      $SECOND{$system2} = sprintf(".%2d %3s",$win/($win+$loss+0.000001)*100,$distinction);
      $DISTINCTION{length($distinction)} += .5;
    }
###    printf "%10s:",substr($system1,0,10);
    foreach my $system2 (sort keys %{$$TOTAL{$task}}) {
###      print "|".$FIRST{$system2};
    }
###    print "\n";
###    printf "%10s ","";
    foreach my $system2 (sort keys %{$$TOTAL{$task}}) {
###      print "|".$SECOND{$system2};
    }
###    print "\n";
  }
  my $total_distinctions = scalar(keys %{$$TOTAL{$task}}) * (scalar(keys %{$$TOTAL{$task}})-1) / 2;
###  printf "number of pairwise distinctions at p-level <0.01 (***/---): %3d (%2d%s)\n",$DISTINCTION{3},100*$DISTINCTION{3}/$total_distinctions,"%";
###  printf "                                   p-level .01-.05 (**/--): %3d (%2d%s)\n",$DISTINCTION{2},100*$DISTINCTION{2}/$total_distinctions,"%";
###  printf "                                   p-level .05-.1    (*/-): %3d (%2d%s)\n",$DISTINCTION{1},100*$DISTINCTION{1}/$total_distinctions,"%";
###  printf "                                   p-level >.1     (blank): %3d (%2d%s)\n",$DISTINCTION{0},100*$DISTINCTION{0}/$total_distinctions,"%";
}

sub get_task {
  my ($DATA) = @_;
  my $src = &clean_up_language($$DATA[$INDEX{"srclang"}]);
  my $tgt = &clean_up_language($$DATA[$INDEX{"trglang"}]);
  my $task = "$src-$tgt";
  return $task;
}

sub process_judgment {
  my ($task,$DATA,$WIN,$TOTAL) = @_;
  for(my $i=1; $i<5; $i++) {
    for(my $j=$i+1; $j<=5; $j++) {
      my $system1 = &clean_up_system_name($$DATA[$INDEX{"system${i}Id"}]);
      my $system2 = &clean_up_system_name($$DATA[$INDEX{"system${j}Id"}]);
      my $rank1 = $$DATA[$INDEX{"system${i}rank"}];
      my $rank2 = $$DATA[$INDEX{"system${j}rank"}];
      next unless $rank1 != $rank2;
      if ($rank1 < $rank2) {
        $$WIN{$task}{$system1}{$system2}++;
      }
      else {
        $$WIN{$task}{$system2}{$system1}++;
      }
      $$TOTAL{$task}{$system1}{$system2}++;
      $$TOTAL{$task}{$system2}{$system1}++;
    }
  }
}

sub clean_up_system_name {
  my ($name) = @_;
  $name =~ tr/A-Z/a-z/;
  $name =~ s/^newstest2013...-...//;
  $name =~ s/\.\d+$//;
  $name =~ s/_NLP_Groups_Phrasal_Toolkit_-_Primary//i;
  $name =~ s/heafield-unconstrained/heafield/;
  $name =~ s/_/-/g;
  $name =~ s/.primary//i;
  $name =~ s/_multifrontend//;
  $name =~ s/translate_[a-z]+-to-[a-z]+//;
  $name =~ s/uppsala-unviersity//;
  $name =~ s/[\_\:\)\-]+$//;
  return $name;
}

sub clean_up_language {
  my ($language) = @_;
  $language = "German" if $language eq "deu";
  $language = "English" if $language eq "eng";
  $language = "Spanish" if $language eq "spa";
  $language = "French" if $language eq "fre";
  $language = "Czech" if $language eq "cze";
  $language = "Russian" if $language eq "rus";
  return $language;
}

sub compute_p_value {
  my ($win,$loss) = @_;
  return 1 if $win+$loss == 0;
  my $total = $win + $loss;
  my $min = $win < $loss ? $win : $loss;
  my $p = 0;
  for (my $i=0;$i<=$min;$i++) {
    $p += exp(&binomial($i,$total));
  }
  return $p;
}

sub binomial {
  my ($k,$n) = @_;
  my $log_prob = &log_factorial($n) - &log_factorial($n-$k) - &log_factorial($k);
  $log_prob += $n * log(0.5);
#  print "($k,$n) = ".exp($log_prob)."\n";
  return $log_prob;
}

sub log_factorial {
  my ($x) = @_;
  if ($x > $#LOG_FACTORIAL) {
    for(my $i=$#LOG_FACTORIAL;$i<=$x;$i++) {
      $LOG_FACTORIAL[$i] = $LOG_FACTORIAL[$i-1] + log($i);
    }
  }
  return $LOG_FACTORIAL[$x];
}


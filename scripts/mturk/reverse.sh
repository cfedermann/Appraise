#!/bin/bash

set -u

worker=$1
message=$2

unreject=$(pwd)/unreject.txt
grep $worker */*/mturk-results.txt | grep Rejected | cut -f 19 | perl -pe 's/"//g' > $unreject
num=$(cat $unreject | wc -l)

echo "About to reverse $num of $worker's rejections. Hit enter to continue, Ctrl-C to quit"
read j

ant -f $HOME/expts/wmt13/ApproveRejectImplementation/build.xml approverejected -Dinfile=$unreject -Dmessage="$2"

for file in $(find . -name '*.success'); do 
     results=$(dirname $file)/mturk-results.txt; 
	 echo "$file --> $results";  
	 $MTURK/bin/getResults.sh -successfile $file  -outputfile $results;
	 $APPRAISE/appraise/convert_mturk_results.py -rejected $results > $results.wmt
done

python combine_all.py $(find . -name mturk-results.txt.wmt) > mturk-results-combined.txt

python $APPRAISE/appraise/author_meta.py $(find . -name mturk-results.txt) > turkers.meta.txt

export=/Users/post/Dropbox/research/WMT13/wmt13-export-20130623.txt
/Users/post/code/Appraise/appraise/evaluate_mturk_results.py mturk-results-combined.txt \
	$export -meta turkers.meta.txt > report.txt

# Reject users with (a) control rate less than 0.5 (b) having seen at least 10 controls and 
# (c) having done at least 5 HITs
cat report.txt | tail -n+3 | awk '{if ($4 < 0.5 && $3 >= 10 && $6 >= 5) print}' > reject.log

outfile=reject-20130625.txt
    echo -e "assignmentIdToReject\tassignmentIdToRejectComment" > $outfile
    for worker in $(cat reject.log | awk '{print $1}'); do 
      echo "rejecting all of $worker"; grep "$worker" */batch*/mturk-results.txt | grep Submitted; 
    done | awk -F'\t' '{print $19}' | grep -v ^$ | perl -ne 'chomp; print "$_\t\"You failed our internal consistency check.\"\n";' >> $outfile

echo -n "REJECTED HITS: "
wc -l $outfile

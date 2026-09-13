#!/bin/bash
# Watch output and progress of step 2

clear
while :
do
    cat /tmp/getHashes.log
    echo
    echo $(( `cat /tmp/getHashes.log | sed 's|of|* 100 /|'` ))
    sleep 2
    clear
done
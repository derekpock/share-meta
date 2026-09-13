#!/bin/bash
# Generate a list of all directories in dirs.txt.
# Calculate the number of subitems in each folder and print into dirCounts.txt.
# Pass in the directory you want to measure!

cd /share

find -name ".zfs" -prune -o -type d -print  > /share/meta/manyDirs/dirs.txt
cat /share/meta/manyDirs/dirs.txt | wc -l
sleep 1

IFS="
"

(
for line in `cat /share/meta/manyDirs/dirs.txt`
do
  # if [[ "/$line/" != *"/.zfs/"* ]]
  # then
  find "$line" | wc -l | tr -d '\n'
  echo " $line"
  # fi
done
) > /share/meta/manyDirs/dirCounts.txt

cat /share/meta/manyDirs/dirCounts.txt | sort -nr | grep -E '^[0-9]{4,}' > /share/meta/manyDirs/dirCountsOrder.txt

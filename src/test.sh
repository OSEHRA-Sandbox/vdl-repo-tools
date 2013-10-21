#!/bin/bash
cd ~/tmp/mirror/
FILES=`find . -type f | xargs grep "Page Not Found" | grep -v "Binary file" | cut -c 3- | cut -d":" -f1`
for ((n=0;n<10;n++))
do
  files=`find . -type f | xargs grep "Page Not Found" | grep -v "Binary file" | cut -c 3- | cut -d":" -f1`
  echo "$files" | wc -l
  while read -r line; do
    wget -w 1 -x --user-agent="Mozilla/5.0" "http://$line" &> /dev/null
  done <<< "$files"
done 

#!/bin/bash

SCRIPT_DIR=$(cd $(dirname $0); pwd)

echo $SCRIPT_DIR

cd $SCRIPT_DIR
# touch executed.txt
echo "---" >>  scrapingTime.log
date >> scrapingTime.log
cat AutoLoarArticleList.txt  | grep -vF '#' | xargs -I{} /usr/local/bin/python3.7 nicopedy_saver.py {}
date >> scrapingTime.log

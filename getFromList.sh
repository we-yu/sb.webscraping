#!/bin/bash

SCRIPT_DIR=$(cd $(dirname $0); pwd)

# echo $SCRIPT_DIR

cd $SCRIPT_DIR
# touch executed.txt
cat AutoLoadArticleList.txt  | grep -vF '#' | xargs -I{} python3 nicopedy_saver.py {}

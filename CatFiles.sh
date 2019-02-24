#!/bin/bash

tail -n +2 $2 > headerRemoved.tmp
cat $1 headerRemoved.tmp > $3

rm *.tmp

exit 0

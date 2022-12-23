#!/bin/bash
tempDir=$(mktemp -d)
echo "Saving to temporary directory $tempDir"

if [ $# -ne 2 ];
  then 
    echo "Not all requied arguments were given"
    echo "Syntax: 'source general_offload.sh <data_directory> <device_id>"
    return
fi

ceti general_offload $1 $2 $tempDir

ceti s3upload $tempDir

rm -rf $tempDir

echo "( ・◡・)つ━☆  All done" 

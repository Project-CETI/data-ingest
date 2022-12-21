#!/bin/bash
tempDir=$(mktemp -d)

if [ $# -ne 2 ];
  then 
    echo "Not all requied arguments were given"
    echo "Syntax: 'general_offload <data_directory> <device_id>"
    return
fi

ceti general_offload $1 $2 $tempDir

ceti s3upload $tempDir

rm -rf $tempDir

echo "( ・◡・)つ━☆  All done" 

#!/bin/bash
set -e

DATABACKUPDIR="/data-backup"

LOG_FILE="tag-$(date -u +%s).log"
function log() {
  if [ $# -gt 0 ]
  then
    OUTPUT="$1"
    echo "$OUTPUT"
    echo "$OUTPUT" >> $LOG_FILE
  fi
}

function install_latest_ceti {
  if [ -z "$(which aws)" ]
  then
    log "AWS command line tool is missing. Please install it using 'sudo apt install aws'."
    exit 1  
  fi

  if [ -z "$(which pip)" ]
  then
    log "pip tool not found. Please install it using 'sudo apt install python3 python3-pip'."
    exit 1
  fi

  log "Attempting to login into aws codeartifact..."
  aws codeartifact login --tool pip --repository ceti --domain ceti-repo

  log "Checking the ceti command line tool is the latest version, install if necessary..."
  pip install ceti

  if [ -z "$(which ceti)" ]
  then
    log "Could not find properly installed ceti command line tool. Please check https://github.com/Project-CETI/data-ingest/README.md"
    exit 1
  fi
}

function encode {
  if [ -z "$(which flac)" ]
  then
    log "flac command line tool is missing. Please install it using 'sudo apt install flac'."
    exit 1  
  fi

  if [ -z "$(which gzip)" ]
  then
    log "gzip command line tool is missing. Please install it using 'sudo apt install gzip'."
    exit 1  
  fi

  if [ $# -gt 0 ]
  then
    SRCDIR="$1"
  else
    SRCDIR="$(realpath $(pwd))"
  fi  

  for f in "$SRCDIR"/*.raw; do
    IFS='.' read -r -a split_filename <<< "$f"
    log "flac encoding $f into $SRCDIR/${split_filename[0]}.flac"
    flac --channels=3 --bps=16 --sample-rate=96000 --sign=signed --endian=big --force-raw-format "$f" --force --output-name="${split_filename[0]}.flac" &
  done
  wait

  for f in "$SRCDIR"/*.raw; do
    log "removing raw file: $f"
    rm "$f"
  done  

  #gzip all csv files
  for f in "$SRCDIR"/*.csv; do
    log "gzipping $f to $f.gz"
    gzip "$f" -c > "$f.gz" &
  done
  wait

  for f in "$SRCDIR"/*.csv; do
    log "removing csv file: $f"
    rm "$f"
  done  

  log "Done compressing files... success"
}

function encode_all {
  log "Attempting to encode all data found in data/"
  for d in data/wt-*; do
    if [ -d "$d" ]
    then
      log "Encoding files in $d"
      encode "$d"
    fi
  done
}

function set_offload_folder {
  log "creating temporary folder for data offload"

  if [ -d "data" ]
  then
    log "$(realpath data) is already present, reusing the existing folder"
    return
  fi

  export OFFLOADDIR="$(mktemp -d)"
  log "Creating symlink ./data -> $OFFLOADDIR"
  ln -s "$OFFLOADDIR" data
}

function cleanup_offload_folder {
  log "Cleaning up offload folder"
  if [ -L "data" ]
  then
    log "removing symlink ./data -> $OFFLOADDIR"
    unlink "data"
  fi
  log "removing $OFFLOADDIR"
  rm -rf "$OFFLOADDIR" 
}

function backup_uploaded_data {
  DATABACKUPDIR="$DATABACKUPDIR/$(date +'%Y-%m-%d')/"
  if [ -z "$(ls -A $(realpath data))" ]
  then
    log "./data is empty, skipping backup"
  else
    log "copying all files to $DATABACKUPDIR"
    mkdir -p "$DATABACKUPDIR"
    cp -rp data/* "$DATABACKUPDIR"
  fi
}

function offload_all_tags {
  log "Attempting to search for all tags on LAN and offload all data. This may get awhile..."
  log "$(ceti whaletag -a)"
}

function s3upload {
  log "Attempting to upload all offloaded data to s3"
  log "$(ceti s3upload data)"
}

function clean_all_tags {
  log "Attempting to clean all tags"
  log "For now the automated cleaning of the tags is disabled. If everything looks good, please run 'ceti whaletag -ca' to erase all data from all tags."
#  log "$(ceti whaletag -ca)"
}

function main {
  log "$(date -u) UTC"
  install_latest_ceti
  set_offload_folder
  offload_all_tags
  encode_all
  s3upload
  backup_uploaded_data
  cleanup_offload_folder
  clean_all_tags
}

main
#!/bin/bash
set -e

LOG_FILE="tag-$(date -u +%s).log"
function log() {
  if [ $# -gt 0 ]
  then
    echo "$1"
    echo "$1" >> $LOG_FILE
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
    log "flac command line tool is missing. Please install it using 'sudo apt install gzip'."
    exit 1  
  fi

  if [ $# -gt 0 ]
  then
    SRCDIR="$1"
  else
    SRCDIR="$(realpath $(pwd))"
  fi
  
  # Set destination
  OUTDIR="$SRCDIR"
  mkdir -p "$OUTDIR"
  for f in *.raw; do
    IFS='.' read -r -a split_filename <<< "$f"
    log "flac encoding $f to $OUTDIR/${split_filename[0]}.flac"
    flac --channels=3 --bps=16 --sample-rate=96000 --sign=signed --endian=big --force-raw-format "$f" --force --output-name="$OUTDIR/${split_filename[0]}.flac" &
  done
  wait

  for f in *.raw; do
    log "removing raw file: $f"
    rm "$f"
  done  

  #gzip all csv files
  for f in *.csv; do
    log "gzipping $f to $OUTDIR/$f.gz"
    gzip "$f" -c > "$OUTDIR/$f.gz" &
  done
  wait

  #move all other files
  for f in *; do
    log "moving file $f to $OUTDIR/$f"
    mv "$f" "$OUTDIR/$f"
  done

  "Done compressing files... success"
}

function main {
  log "$(date -u) UTC"
  install_latest_ceti

#list all tags
#for each tag 
  #make temp folder
  #offload all data
  #encode it
  #s3 upload it
  #backup a copy
  #clean tag

}

main
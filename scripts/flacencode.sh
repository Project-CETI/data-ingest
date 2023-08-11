#!/bin/bash
OUTDIR="../flac" # make output dir called flac
mkdir -p "$OUTDIR"

# change this to the directory where the raw files are
for f in *.raw; do # for all the files with .raw extension

#  remove.raw from the filename f
  filename="${f%.raw}"
  flac --channels=3 --bps=16 --sample-rate=96000 --sign=signed --endian=big --force-raw-format "$f" --force --output-name="$OUTDIR/$filename.flac" &
done
wait
echo "( ・◡・)つ━☆  All done"

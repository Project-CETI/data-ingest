#!/bin/bash
OUTDIR="../../tag-compressed/${PWD##*/}"
mkdir -p "$OUTDIR"
for f in *.raw; do
  IFS='.' read -r -a split_filename <<< "$f"
  flac --channels=3 --bps=16 --sample-rate=96000 --sign=signed --endian=big --force-raw-format "$f" --force --output-name="$OUTDIR/${split_filename[0]}.flac" &
done

cp sensors.csv $OUTDIR
wait
gzip $OUTDIR/sensors.csv


echo "( ・◡・)つ━☆  All done" 

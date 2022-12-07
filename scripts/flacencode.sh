#!/bin/bash
OUTDIR="../flac"
mkdir -p "$OUTDIR"
for f in *.raw; do
  flac --channels=3 --bps=16 --sample-rate=96000 --sign=signed --endian=big --force-raw-format "$f" --force --output-name="$OUTDIR/$f.flac" &
done
wait
echo "( ・◡・)つ━☆  All done"

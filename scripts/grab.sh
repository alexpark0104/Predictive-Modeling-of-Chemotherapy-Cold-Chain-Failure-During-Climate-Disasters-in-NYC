#!/bin/bash
# Install the NEWEST download of a file into the repo, then tidy Downloads.
#   usage (from the repo root):  scripts/grab.sh outage_events.py scripts
# macOS renames repeat downloads to "name (1).ext"; this always picks the newest one, so you never copy an
# old version by accident. Matching downloads are moved (not deleted) to ~/Downloads/_installed/.
name="$1"; dest="$2"
if [ -z "$name" ] || [ -z "$dest" ]; then echo "usage: scripts/grab.sh <filename> <destination folder>"; exit 1; fi
stem="${name%.*}"; ext="${name##*.}"
dl="${DOWNLOADS_DIR:-$HOME/Downloads}"
newest="$(ls -t "$dl"/"$stem"*."$ext" 2>/dev/null | head -1)"
if [ -z "$newest" ]; then echo "no download found matching $stem*.$ext in $dl"; exit 1; fi
mkdir -p "$dest"
cp "$newest" "$dest/$name" || exit 1
echo "installed: $newest -> $dest/$name"
mkdir -p "$dl/_installed"
for f in "$dl"/"$stem"*."$ext"; do mv "$f" "$dl/_installed/"; done
echo "moved matching downloads to $dl/_installed/ (safe to delete later)"

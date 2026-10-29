#!/bin/bash
# One command: check links -> build pages + pins + CSV -> (ask) -> deploy -> verify.
# Usage:  ./go.sh                  everything
#         ./go.sh --only bathroom  just one topic
#         ./go.sh --start 2026-11-05   first pin date for the CSV
#         ./go.sh --preview        also draw pins for unfinished topics (out/preview/)
cd "$(dirname "$0")" || exit 1
PY=.venv/bin/python
[ -x "$PY" ] || { echo "Missing .venv. Run:  python3 -m venv .venv && .venv/bin/pip install pillow"; exit 1; }

$PY build.py "$@" || { echo; echo "Fix the ERROR lines above in links/*.txt, then run ./go.sh again."; exit 1; }

echo
read -r -p "Deploy to Netlify now (makes the pages and pin images public)? [y/N] " ans
if [[ "$ans" =~ ^[Yy]$ ]]; then
  netlify deploy --prod --dir=site || exit 1
  echo; echo "Checking that every image and page is live..."
  $PY build.py --verify-urls "$@" | tail -5
  echo
  echo "NEXT: upload out/pinterest-upload.csv at Pinterest > Settings > Import content > Upload .csv"
else
  echo "Not deployed. Pinterest needs the images online first, so deploy before uploading the CSV."
fi

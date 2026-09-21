#!/bin/sh
set -e
cd "$(dirname "$0")"
python3 add_levels.py
python3 add_scores.py
python3 build.py

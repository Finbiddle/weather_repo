#!/bin/bash

# absolute path
CRONDIR="/home/ubuntu/cron"

# go to cron dir
cd "$CRONDIR" || exit 1

# activate venv
source "$CRONDIR/venv/bin/activate"

# run fetch_weather.py using ABSOLUTE python path
"$CRONDIR/venv/bin/python" "$CRONDIR/fetch_weather.py"

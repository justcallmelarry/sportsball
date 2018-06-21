#!/bin/bash
cron && tail -f /var/log/cron.log &
python /usr/src/app/google.py &
sleep infinity

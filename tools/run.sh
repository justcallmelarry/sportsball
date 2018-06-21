#!/bin/bash
cron && tail -f /var/log/cron.log &
python /usr/src/app/sportsball.py &
sleep infinity

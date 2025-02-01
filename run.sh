#!/bin/bash
# Use absolute paths from now on
echo "Starting script at $(date)" >> /tmp/cron_log.txt
source /Users/chad/Documents/PythonProject/schoology_scrape/.env
echo "Sourced .env at $(date)" >> /tmp/cron_log.txt
cd /Users/chad/Documents/PythonProject/schoology_scrape
echo "Changed directory to $(pwd) at $(date)" >> /tmp/cron_log.txt
/Users/chad/Documents/PythonProject/schoology_scrape/.venv/bin/python main.py
echo "Finished script at $(date)" >> /tmp/cron_log.txt

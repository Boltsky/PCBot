#!/bin/bash

# Deployment script for PCBot

# Update repository
printf "\n\033[1;34mUpdating source repository...\033[0m\n"
git pull origin main

# Install dependencies
printf "\n\033[1;34mInstalling/updating dependencies...\033[0m\n"
pip install -r requirements.txt

# Run tests
printf "\n\033[1;34mRunning tests...\033[0m\n"
python3 test_focused.py

# Check test result
if [ $? -ne 0 ]; then
    printf "\033[1;31mTests failed. Aborting deployment.\033[0m\n"
    exit 1
fi

# Launch application
printf "\n\033[1;34mStarting PCBot...\033[0m\n"
python3 run_pcbot.py &

# Monitor logs (display last 100 lines)
printf "\n\033[1;34mTailing logs...\033[0m\n"
tail -f -n 100 /var/log/pcbot/pcbot.log

# This script assumes the bot logs to /var/log/pcbot/pcbot.log. Adjust as necessary.
# Ensure that you have permission to run this script and access necessary files and directories.

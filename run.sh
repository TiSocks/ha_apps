#!/usr/bin/env bash

echo "Starting Kia Trip Logger..."

# 1. Run the Python script
python3 /kia_logger.py

# 2. Tell the Supervisor to shut down this add-on
echo "Task complete. Telling Supervisor to stop the add-on..."

curl -s -X POST "http://supervisor/addons/self/stop" \
     -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
     -H "Content-Type: application/json"

echo "Shutdown command sent."
#!/bin/bash
echo "Webhook server starting..."
python3 webhook_server.py &

inotifywait -m -e modify webhook_server.py |
while read path action file; do
    echo "File ${file} changed, restarting server..."
    pkill -f webhook_server.py
    python3 webhook_server.py &
done
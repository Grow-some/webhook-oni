#!/bin/bash
echo "Webhook server starting..."

SCRIPT_PATH="/app/webhook_server.py"

python3 "$SCRIPT_PATH" &

inotifywait -m -e modify "$SCRIPT_PATH" |
while read path action file; do
    echo "File ${file} changed, restarting server..."
    pkill -f "$SCRIPT_PATH"
    python3 "$SCRIPT_PATH" &
done
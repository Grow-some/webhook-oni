#!/bin/bash

echo "Webhook server starting..."
python /podman/Discord_webhook/webhook_server.py &

# ファイルの変更を監視し再起動
while inotifywait -e modify /podman/Discord_webhook/webhook_server.py; do
  echo "Webhook script updated, restarting..."
  pkill -f webhook_server.py
  python /podman/Discord_webhook/webhook_server.py &
done
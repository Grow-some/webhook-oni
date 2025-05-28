#!/bin/bash
SCRIPT_PATH="/app/webhook_server.py"

echo "Webhook server starting..."

while true; do
  # サーバー起動
  python3 "$SCRIPT_PATH" &
  CHILD_PID=$!

  # プロセスが死ぬまで待機
  wait $CHILD_PID
  echo "Process $CHILD_PID exited with code $?. Restarting in 1s..."

  sleep 1
done

import os
import logging
from datetime import datetime

# ログ設定
logging.basicConfig(
    filename='/app/logs/healthcheck.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def check_health():
    try:
        # DBファイルの存在確認
        if os.path.exists('/app/db/voice_chat_usage.json'):
            logging.info("Health check passed: Database file exists")
            return True
        else:
            logging.error("Health check failed: Database file not found")
            return False
    except Exception as e:
        logging.error(f"Health check error: {str(e)}")
        return False

if __name__ == "__main__":
    exit(0 if check_health() else 1)
# filepath: /c:/GitHub/Discord/Noti_VC/LINE_webhook/line_test.py
import logging
from flask import Flask, request, jsonify ,abort
import arrow
from dotenv import load_dotenv
import os
import base64
import hashlib
import hmac
import json

app = Flask(__name__)

# ログ設定
logging.basicConfig(level=logging.INFO, filename='app.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    load_dotenv()
    CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
    data = request.get_json()
    request_body = request.get_data(as_text=True)
    hash = hmac.new(CHANNEL_SECRET.encode('utf-8'), request_body.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(hash).decode('utf-8')
    x_line_signature = request.headers.get('x-line-signature')
    # 署名の検証
    if x_line_signature != signature:
        response = {
            "success": False,
            "timestamp": arrow.utcnow().isoformat(),
            "statusCode": 400,
            "reason": "Bad Request",
            "detail": "400 Bad Request"
        }
        return jsonify(response), 400
    
    data = request.get_json()
    logger.info(data)
    if 'events' in data:
        with open('events.txt', 'a', encoding='utf-8') as f:
            for event in data['events']:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')        
    
    
    response = {
        "success": True,
        "timestamp": arrow.utcnow().isoformat(),
        "statusCode": 200,
        "reason": "OK",
        "detail": "200"
    }
    
    return jsonify(response), 200
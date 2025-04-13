from dotenv import load_dotenv
import discord
import os
import logging
import uuid
import json
import requests

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID"))

LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_GROUP_ID = os.getenv("LINE_GROUP_ID")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_line_message(message):
    url = "https://api.line.me/v2/bot/message/push"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
        "X-Line-Retry-Key": str(uuid.uuid4()),  # 一意のリトライキーを設定
    }

    data = {
        "to": LINE_GROUP_ID,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        logger.info("✅ LINEメッセージ送信成功")
    else:
        logger.info(f"❌ LINEメッセージ送信失敗: {response.status_code}, {response.text}")
        logger.info(f"{json.dumps(data)}")
    
@client.event
async def on_ready():
    logger.info("Bot is ready.")

@client.event
async def on_voice_state_update(user, before, after):
    if before.channel != after.channel:
        if after.channel is not None and after.channel.id == VOICE_CHANNEL_ID:
            message = f"{after.channel.name}に{user.display_name}が参加しました"
            logger.info(message)
            send_line_message(message)
        if before.channel is not None and before.channel.id == VOICE_CHANNEL_ID:
            message = f"{before.channel.name}から{user.display_name}が退出しました"
            logger.info(message)
            send_line_message(message)

client.run(DISCORD_TOKEN)
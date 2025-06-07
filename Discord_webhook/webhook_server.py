from dotenv import load_dotenv
import discord
import os
import logging
import uuid
import json
import requests
import datetime
import time

class discord_bot:
    def __init__(self):
        
        self.USAGE_DATA_FILE = "voice_chat_usage.json"
        self.client = None
        self.logger = None
        self.DISCORD_TOKEN = None
        self.VOICE_CHANNEL_ID = 0
        self.MONTHLY_REPORT_CHANNEL = 0
        self.LINE_ACCESS_TOKEN = None
        self.LINE_GROUP_ID = None
        
        self.env_init()
        self.setup_client()    
    
    def env_init(self):
        if load_dotenv():
            self.DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
            self.VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID") or 0)
            self.MONTHLY_REPORT_CHANNEL = int(os.getenv("MONTHLY_REPORT_CHANNEL") or 0)
            self.LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
            self.LINE_GROUP_ID = os.getenv("LINE_GROUP_ID")
        
        # ログ設定
        log_dir = "./logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
        self.setup_multi_level_logger()
        
    def setup_multi_level_logger(self):
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)  # ロガー自体は最低レベルに設定
        
        # ログディレクトリの確認と作成
        log_dir = "./logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # フォーマッターの作成
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # INFOレベル以上のログ用ハンドラー
        info_handler = logging.FileHandler(f"{log_dir}/discord_info.log", encoding="utf-8")
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(formatter)

        # ERRORレベル以上のログ用ハンドラー
        error_handler = logging.FileHandler(f"{log_dir}/discord_error.log", encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # ハンドラーをロガーに追加
        logger.addHandler(info_handler)
        logger.addHandler(error_handler)
        
        self.logger = logger
    
    def setup_client(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        intents.voice_states = True
        intents.message_content = True
        print(intents.value)
        self.client = discord.Client(intents=intents)
        # イベントハンドラの登録
        @self.client.event
        async def on_ready():
            self.logger.info(f"Bot is ready. Logged in as {self.client.user}")

        @self.client.event
        async def on_message(message):
            if message.author.bot:
                return  # Botのメッセージは無視
            if message.content.lower() == "!report":
                await message.channel.send(message.content.lower())
                self.logger.info(message.content.lower())
                

        @self.client.event
        async def on_voice_state_update(member, before, after):
            if before.channel != after.channel:
                if after.channel and after.channel.id == self.VOICE_CHANNEL_ID:
                    self.logger.info(f"{member.display_name} joined {after.channel.name}")
                    self.send_line_message(f"{member.display_name} joined {after.channel.name}")
                if before.channel and before.channel.id == self.VOICE_CHANNEL_ID:
                    self.logger.info(f"{member.display_name} left {before.channel.name}")
                    self.send_line_message(f"{member.display_name} left {before.channel.name}")
                    
    def send_line_message(self,message):
        url = "https://api.line.me/v2/bot/message/push"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.LINE_ACCESS_TOKEN}",
            "X-Line-Retry-Key": str(uuid.uuid4()),  # 一意のリトライキーを設定
        }

        data = {
            "to": self.LINE_GROUP_ID,
            "messages": [
                {
                    "type": "text",
                    "text": message
                }
            ]
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            self.logger.info("LINEメッセージ送信成功")
        else:
            self.logger.error(f"LINEメッセージ送信失敗: {response.status_code}, {response.text}")
            self.logger.error(f"{json.dumps(data)}")
            
    def send_discord_message(self,message):
        channel = self.client.get_channel(self.MONTHLY_REPORT_CHANNEL)
        channel.send(message)
        self.logger.info(f"Discord message sent to channel {self.MONTHLY_REPORT_CHANNEL}")

# class intime_calculator:
#     def __init__(self):
        

def app_main():
    bot = discord_bot()
    bot.client.run(bot.DISCORD_TOKEN)
 
if __name__ == "__main__":
    app_main()
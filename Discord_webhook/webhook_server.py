from dotenv import load_dotenv
import discord
from discord.ext import commands
import os
import logging
import uuid
import json
import requests
import datetime
import aiohttp
from tinydb import TinyDB, Query

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
        self.db_init()    
    
    def env_init(self):
        if load_dotenv():
            self.DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
            self.VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID") or 0)
            self.MONTHLY_REPORT_CHANNEL = int(os.getenv("MONTHLY_REPORT_CHANNEL") or 0)
            self.LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
            self.LINE_GROUP_ID = os.getenv("LINE_GROUP_ID")
            self.CONSOLE_CHANNEL_ID = int(os.getenv("CONSOLE_CHANNEL_ID") or 0)
        
        # ログ設定
        log_dir = "./logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        # DBファイルの確認と作成
        db_dir = "./db"
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        if not os.path.exists(f"{db_dir}/{self.USAGE_DATA_FILE}"):
            with open(f"{db_dir}/{self.USAGE_DATA_FILE}", 'w') as f:
                json.dump([], f)
        self.setup_multi_level_logger()
    
    def db_init(self):
        # TinyDBの初期化
        self.db = TinyDB(f"./db/{self.USAGE_DATA_FILE}")
        self.UsageData = Query()
        self.logger.info("Database initialized successfully.")
        
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
        
        self.client = commands.Bot(command_prefix="!", intents=intents)
        # イベントハンドラの登録
        @self.client.event
        async def on_ready():
            self.logger.info(f"Bot is ready. Logged in as {self.client.user}")
            await self.send_discord_message("Bot is ready.", channel_id=self.CONSOLE_CHANNEL_ID)

        @self.client.event
        async def on_message(message):
            if not self.search_user_data(message.author.id):
                self.create_user_inital_data(message.author.id)
            if message.author.bot:
                return  # Botのメッセージは無視
            words = message.content.split()
            if words[0].lower() == "!report":
                if len(words) > 1:
                    if len(month) != 6 or not month.isdigit():
                        await message.channel.send("月の形式が正しくありません。例: 202505")
                        return
                    month = words[1]
                    usage = self.get_monthly_usage(message.author.id, month)
                    if usage:
                        usage_table = f"| 月 | 使用時間(時間) |\n|---|---|\n| {month} | {usage/3600} |\n"
                        await message.channel.send(f"{message.author.display_name}の{month}の使用時間:\n{usage_table}")
                    else:
                        await message.channel.send(f"{message.author.display_name}の{month}の使用時間は記録されていません。")
                else:
                    usage = self.get_monthly_usage(message.author.id)
                    if not usage:
                        await message.channel.send(f"{message.author.display_name}の使用時間は記録されていません。")
                        return
                    usage_table = "| 月 | 使用時間(時間) |\n|---|---|\n"
                    for month, seconds in usage.items():
                        usage_table += f"| {month} | {seconds/3600} |\n"
                    usage = f"\n{usage_table}"
                    await message.channel.send(f"{message.author.display_name}の使用時間:\n{usage}")
                    
        @self.client.event
        async def on_voice_state_update(member, before, after):
            if not self.search_user_data(member.id):
                self.create_user_inital_data(member.id)
            if before.channel != after.channel:
                if after.channel and after.channel.id == self.VOICE_CHANNEL_ID:
                    self.logger.info(f"{member.display_name} joined {after.channel.name}")
                    await self.send_line_message(f"{member.display_name} joined {after.channel.name}")
                    if not self.update_active_status(member.id, True):
                        self.logger.error(f"Failed to update active status for {member.id}")
                    
                if before.channel and before.channel.id == self.VOICE_CHANNEL_ID:
                    self.logger.info(f"{member.display_name} left {before.channel.name}")
                    await self.send_line_message(f"{member.display_name} left {before.channel.name}")
                    if not self.update_active_status(member.id, False):
                        self.logger.error(f"Failed to update active status for {member.id}")
                    
    async def send_line_message(self,message):
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
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=json.dumps(data)) as response:
                if response.status == 200:
                    self.logger.info("LINEメッセージ送信成功")
                else:
                    error_text = await response.text()
                    self.logger.error(f"LINEメッセージ送信失敗: {response.status}, {error_text}")
                    self.logger.error(f"{json.dumps(data)}")
            
    async def send_discord_message(self, message, channel_id=None):
        try:
            if channel_id is None:
                channel_id = self.CONSOLE_CHANNEL_ID
            channel = self.client.get_channel(channel_id)
            if channel:
                await channel.send(message)
                self.logger.info(f"Discord message sent to channel {channel_id}")
            else:
                self.logger.error(f"Channel {channel_id} not found.")
        except Exception as e:
            self.logger.error(f"Failed to send Discord message: {e}")
            
    def create_user_inital_data(self, user_id) -> None:
        initical_data = {
            "user_id": user_id,
            "intime": None,
            "active_status": False,
            "monthly_data": {}
        }
        self.db.insert(initical_data)
    
    def search_user_data(self, user_id) -> bool:
        return bool(self.db.search(self.UsageData.user_id == user_id))
        
    def update_active_status(self, user_id, status:bool) -> bool:
        try:
            current_time = datetime.datetime.now().isoformat()
            result = self.db.search(self.UsageData.user_id == user_id)
            if result:
                updates = {"active_status": status}
                if status:
                    updates["intime"] = current_time
                else:
                    intime = datetime.datetime.fromisoformat(result[0]['intime'])
                    duration = datetime.datetime.now() - intime
                    duration_seconds = int(duration.total_seconds())
                    month = datetime.datetime.now().strftime("%Y-%m")
                    updates["monthly_data." + month] = result[0]['monthly_data'].get(month, 0) + duration_seconds
                    updates["intime"] = None
                self.db.update(updates, self.UsageData.user_id == user_id)
                return True
            else:
                self.logger.warning(f"No user data found for user_id: {user_id}")
                return False
        except Exception as e:
            self.logger.error(f"Error updating active status for user_id {user_id}: {e}")
            return False
        
    def get_monthly_usage(self, user_id, month=None) -> dict:
        result = self.db.search(self.UsageData.user_id == user_id)
        if result:
            user_data = result[0]
            if month:
                return user_data['monthly_data'].get(month, 0)
            else:
                return user_data['monthly_data']
        return {}
    
    

# class intime_calculator:
#     def __init__(self):
        

def app_main():
    bot = discord_bot()
    bot.client.run(bot.DISCORD_TOKEN)
 
if __name__ == "__main__":
    app_main()
from dotenv import load_dotenv
import discord
from discord.ext import commands
import os
import logging
import uuid
import json
import time
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
        self.db_init()
        self.setup_client()
    
    
    def env_init(self):
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
                json.dump({}, f)
        self.setup_multi_level_logger()
        if load_dotenv():
            self.DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
            self.VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID") or 0)
            self.MONTHLY_REPORT_CHANNEL = int(os.getenv("MONTHLY_REPORT_CHANNEL") or 0)
            self.LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
            self.LINE_GROUP_ID = os.getenv("LINE_GROUP_ID")
            self.CONSOLE_CHANNEL_ID = int(os.getenv("CONSOLE_CHANNEL_ID") or 0)
        else:
            self.logger.error("Failed to load environment variables from .env file.")
            raise EnvironmentError("Environment variables not loaded. Please check your .env file.")
        
    def setup_multi_level_logger(self):
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)  # ロガー自体は最低レベルに設定
        
        # ログディレクトリの確認と作成
        log_dir = "./logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # フォーマッターの作成
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        formatter.converter = lambda *args: time.localtime(time.time() + 9 * 3600)
        
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
            
    def db_init(self):
        # TinyDBの初期化
        self.db = TinyDB(f"./db/{self.USAGE_DATA_FILE}")
        self.UsageData = Query()
        if not self.db.contains(self.UsageData.users.exists()):
            self.db.insert({"users": {}})
        self.logger.info("Database initialized successfully.")
        
    def setup_client(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        intents.voice_states = True
        # administrative intents
        intents.message_content = True
        
        self.client = commands.Bot(command_prefix="!", intents=intents)
        # イベントハンドラの登録
        @self.client.event
        async def on_ready():
            self.logger.info(f"Bot is ready. Logged in as {self.client.user}")
            await self.send_discord_message("Bot is ready.", channel_id=self.CONSOLE_CHANNEL_ID)

        @self.client.event
        async def on_message(message):
            if message.author.bot:
                return  # Botのメッセージは無視
            iddentifier = str(message.author.id)
            if not self.search_user_data(iddentifier):
                self.create_user_inital_data(iddentifier)
            words = message.content.split()
            if words[0].lower() == "!report":
                usage_table = f"{message.author.display_name}の使用時間:\n"
                if len(words) > 1:
                    month = words[1]
                    if len(month) != 7 or month[4] != '-' or not (month[:4].isdigit() and month[5:].isdigit()):
                        await message.channel.send("月の形式が正しくありません。例: 2025-05")
                        return
                    month = words[1]
                    usage = self.get_monthly_usage(iddentifier, month)
                    if usage:
                        
                        usage_table += f"{month}  :  {round(usage / 3600, 2)}hours\n"
                        await message.channel.send(f"{usage_table}")
                    else:
                        await message.channel.send(f"{message.author.display_name}の{month}の使用時間は記録されていません。")
                else:
                    usage = self.get_monthly_usage(iddentifier)
                    if not usage:
                        await message.channel.send(f"{message.author.display_name}の使用時間は記録されていません。")
                        return
                    for month, seconds in usage.items():
                        usage_table += f"{month}  :  {round(seconds / 3600, 2)}hours\n"
                    await message.channel.send(f"{usage_table}")
                    
        @self.client.event
        async def on_voice_state_update(member, before, after):
            iddentifier = str(member.id)
            if not self.search_user_data(iddentifier):
                self.create_user_inital_data(iddentifier)
            if before.channel != after.channel:
                if after.channel and after.channel.id == self.VOICE_CHANNEL_ID:
                    self.logger.info(f"{member.display_name} joined {after.channel.name}")
                    await self.send_line_message(f"{member.display_name} joined {after.channel.name}")
                    if not self.update_active_status(iddentifier, True):
                        self.logger.error(f"Failed to update active status for {iddentifier}")
                    
                if before.channel and before.channel.id == self.VOICE_CHANNEL_ID:
                    self.logger.info(f"{member.display_name} left {before.channel.name}")
                    await self.send_line_message(f"{member.display_name} left {before.channel.name}")
                    if not self.update_active_status(iddentifier, False):
                        self.logger.error(f"Failed to update active status for {iddentifier}")
                    
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
        current_data = self.db.get(self.UsageData.users.exists())
        users = current_data["users"]
        if user_id not in users:
            users[user_id] = {
                "intime": None,
                "active_status": False,
                "monthly_data": {}
            }
            self.db.update({"users": users}, self.UsageData.users.exists())
    
    def search_user_data(self, user_id) -> bool:
        current_data = self.db.get(self.UsageData.users.exists())
        return user_id in current_data["users"]
        
    def update_active_status(self, user_id, status:bool) -> bool:
        try:
            current_data = self.db.get(self.UsageData.users.exists())
            users = current_data["users"]
            if str(user_id) in users:
                user_data = users[user_id]
                current_time = datetime.datetime.now().isoformat()
                                
                    
                if status:
                    user_data["intime"] = current_time
                    user_data["active_status"] = True
                else:
                    if user_data["intime"]:
                        intime = datetime.datetime.fromisoformat(user_data["intime"])
                        duration = datetime.datetime.now() - intime
                        duration_seconds = int(duration.total_seconds())
                        month = datetime.datetime.now().strftime("%Y-%m")
                        user_data["monthly_data"][month] = user_data["monthly_data"].get(month, 0) + duration_seconds
                    user_data["intime"] = None
                    user_data["active_status"] = False
                users[user_id] = user_data
                self.db.update({"users": users}, self.UsageData.users.exists())
                return True
            else:
                self.logger.warning(f"No user data found for user_id: {user_id}")
                return False
        except Exception as e:
            self.logger.error(f"Error updating active status for user_id {user_id}: {e}")
            return False
        
    def get_monthly_usage(self, user_id, month=None) -> dict:
        current_data = self.db.get(self.UsageData.users.exists())
        users = current_data["users"]
        if str(user_id) in users:
            user_data = users[user_id]
            if month:
                return user_data["monthly_data"].get(month, 0)
            else:
                return user_data["monthly_data"]
        return {}

def app_main():
    bot = discord_bot()
    try:
        bot.logger.info("Starting Discord bot...")
        bot.client.run(bot.DISCORD_TOKEN)
    except Exception as e:
        bot.logger.error(f"An error occurred while running the bot: {e}")
        raise
 
if __name__ == "__main__":
    app_main()
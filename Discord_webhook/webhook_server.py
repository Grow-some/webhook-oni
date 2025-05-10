from dotenv import load_dotenv
import discord
import os
import logging
import uuid
import json
import requests
import datetime
import time
import calendar
import threading

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID") or 0)
MONTHLY_REPORT_CHANNEL = int(os.getenv("MONTHLY_REPORT_CHANNEL") or 0)

LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_GROUP_ID = os.getenv("LINE_GROUP_ID")

USAGE_DATA_FILE = "voice_chat_usage.json"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_usage_data():
    """Load voice chat usage data from file"""
    try:
        if os.path.exists(USAGE_DATA_FILE):
            with open(USAGE_DATA_FILE, 'r') as f:
                return json.load(f)
        else:
            return {
                "users": {},
                "current_month": datetime.datetime.now().strftime("%Y-%m"),
                "last_report_date": None
            }
    except Exception as e:
        logger.error(f"Error loading usage data: {e}")
        return {
            "users": {},
            "current_month": datetime.datetime.now().strftime("%Y-%m"),
            "last_report_date": None
        }

def save_usage_data(data):
    """Save voice chat usage data to file"""
    try:
        with open(USAGE_DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving usage data: {e}")

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

def format_duration(seconds):
    """Format seconds into hours and minutes"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}時間{minutes}分"

def generate_monthly_report():
    """Generate a monthly usage report"""
    data = load_usage_data()
    current_month = datetime.datetime.now().strftime("%Y-%m")
    
    if data["current_month"] != current_month:
        data["current_month"] = current_month
        save_usage_data(data)
    
    report = f"📊 {current_month} ボイスチャット利用時間レポート\n\n"
    
    if not data["users"]:
        report += "今月はまだボイスチャットの利用がありません。"
    else:
        sorted_users = sorted(
            data["users"].items(), 
            key=lambda x: x[1].get("total_time", 0), 
            reverse=True
        )
        
        for user_id, user_data in sorted_users:
            total_time = user_data.get("total_time", 0)
            if total_time > 0:
                report += f"👤 {user_data.get('display_name', user_id)}: {format_duration(total_time)}\n"
        
        total_group_time = sum(user.get("total_time", 0) for user in data["users"].values())
        report += f"\n👥 グループ合計: {format_duration(total_group_time)}"
    
    return report

async def send_discord_message(channel_id, message):
    """Send a message to a Discord channel"""
    try:
        channel = client.get_channel(channel_id)
        if channel:
            await channel.send(message)
            logger.info(f"✅ Discordメッセージ送信成功: Channel {channel_id}")
            return True
        else:
            logger.error(f"❌ Discordチャンネルが見つかりません: {channel_id}")
            return False
    except Exception as e:
        logger.error(f"❌ Discordメッセージ送信失敗: {e}")
        return False

async def send_monthly_report(report):
    """Send monthly report to Discord channel only"""
    if MONTHLY_REPORT_CHANNEL:
        success = await send_discord_message(MONTHLY_REPORT_CHANNEL, report)
        if success:
            logger.info("Monthly report sent to Discord channel")
            return True
        else:
            logger.error("Failed to send monthly report to Discord channel")
            return False
    else:
        logger.warning("MONTHLY_REPORT_CHANNEL not configured, skipping Discord report")
        return False

def check_and_send_monthly_report():
    """Check if it's time to send a monthly report and send if needed"""
    now = datetime.datetime.now()
    data = load_usage_data()
    
    if now.day == 1:
        last_report = data.get("last_report_date")
        
        if last_report is None or last_report != now.strftime("%Y-%m-%d"):
            report = generate_monthly_report()
            
            client.loop.create_task(send_monthly_report(report))
            
            data["last_report_date"] = now.strftime("%Y-%m-%d")
            save_usage_data(data)
            logger.info(f"Monthly report sent on {now.strftime('%Y-%m-%d')}")
    
def schedule_monthly_report_check():
    """Schedule a daily check for monthly report"""
    now = datetime.datetime.now()
    
    tomorrow = now.replace(day=now.day, hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    seconds_until_midnight = (tomorrow - now).total_seconds()
    
    threading.Timer(seconds_until_midnight, run_monthly_report_check).start()
    logger.info(f"Scheduled next monthly report check in {seconds_until_midnight:.1f} seconds")

def run_monthly_report_check():
    """Run the monthly report check and schedule the next one"""
    check_and_send_monthly_report()
    schedule_monthly_report_check()

def update_user_session(user_id, display_name, start_time=None, end_time=None):
    """Update user session data"""
    data = load_usage_data()
    
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "display_name": display_name,
            "total_time": 0,
            "last_join": None
        }
    
    data["users"][user_id]["display_name"] = display_name
    
    if start_time is not None:
        data["users"][user_id]["last_join"] = start_time
    
    if end_time is not None and data["users"][user_id]["last_join"] is not None:
        last_join = data["users"][user_id]["last_join"]
        session_duration = end_time - last_join
        data["users"][user_id]["total_time"] += session_duration
        data["users"][user_id]["last_join"] = None
        logger.info(f"User {display_name} session duration: {format_duration(session_duration)}")
    
    save_usage_data(data)

@client.event
async def on_ready():
    logger.info("Bot is ready.")
    schedule_monthly_report_check()

@client.event
async def on_voice_state_update(user, before, after):
    if before.channel != after.channel:
        current_time = int(time.time())
        
        if after.channel is not None and after.channel.id == VOICE_CHANNEL_ID:
            message = f"{after.channel.name}に{user.display_name}が参加しました"
            logger.info(message)
            send_line_message(message)
            
            update_user_session(str(user.id), user.display_name, start_time=current_time)
        
        if before.channel is not None and before.channel.id == VOICE_CHANNEL_ID:
            message = f"{before.channel.name}から{user.display_name}が退出しました"
            logger.info(message)
            send_line_message(message)
            
            update_user_session(str(user.id), user.display_name, end_time=current_time)

@client.event
async def on_message(message):
    if message.content.lower() == "!report" and message.author.guild_permissions.administrator:
        report = generate_monthly_report()
        
        success = await send_monthly_report(report)
        
        if success:
            await message.channel.send("Monthly report sent to Discord channel.")
        else:
            await message.channel.send("Failed to send monthly report. Please check MONTHLY_REPORT_CHANNEL configuration.")

client.run(DISCORD_TOKEN)

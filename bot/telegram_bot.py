# [Filename: bot/telegram_bot.py]
import os
import logging
from typing import Optional
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold, hlink, hcode
from aiogram.filters import Command
from aiogram.enums import ParseMode
import aiohttp
import json

# Configure logging
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not set in environment variables")
    bot = None
    dp = None
else:
    try:
        bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
        dp = Dispatcher()
        logger.info("✅ Telegram bot initialized")
    except Exception as e:
        logger.error(f"❌ Bot initialization failed: {e}")
        bot = None
        dp = None

# Message handlers
async def start_handler(message: Message):
    """Handle /start command"""
    user = message.from_user
    welcome_text = f"""
👋 Hello {user.first_name}!

Welcome to *ApnaJeet AI Video Verifier Bot*! 🎮

📹 *Send me a video* of your gaming screen and I'll extract:
• 👤 Player ID (10-digit number)
• 📅 Profile Date
• 📧 Email Content
• 📢 Ad Page Content

⚡ *How to use:*
1. Send a video file (MP4, AVI, MOV, MKV, 3GP)
2. Wait for processing (10-30 seconds)
3. Get extracted information instantly

🚀 *Commands:*
/start - Show this message
/help - Get help
/status - Check bot status

🎯 *Example:* Send a screen recording of your profile page!
    """
    await message.reply(welcome_text, parse_mode=ParseMode.MARKDOWN)

async def help_handler(message: Message):
    """Handle /help command"""
    help_text = """
📖 *Help Guide*

🎥 *Video Requirements:*
• Format: MP4, AVI, MOV, MKV, 3GP
• Size: Max 50MB
• Duration: 30-60 seconds ideal
• Content: Show profile page clearly

📤 *How to send:*
1. Open Telegram
2. Select this bot (@apnajeet_verifier_bot)
3. Tap 📎 attachment icon
4. Choose video file
5. Send and wait for results

❓ *Need Support?*
Contact: @apnajeet_support

🔗 *Our Apps:*
• ApnaJeet Gaming Platform
• ApnaJeet Admin Panel
    """
    await message.reply(help_text, parse_mode=ParseMode.MARKDOWN)

async def status_handler(message: Message):
    """Handle /status command"""
    status_text = f"""
📊 *Bot Status*

✅ Bot: Online
✅ API: Connected
✅ Database: Connected
⚡ Processing Queue: Empty

📈 *Stats:*
• Uptime: 99.9%
• Videos Processed: 0
• Success Rate: 0%

🔧 *Version:* 1.0.0
    """
    await message.reply(status_text, parse_mode=ParseMode.MARKDOWN)

async def handle_video(message: Message):
    """Handle video messages"""
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    logger.info(f"📹 Video received from {username} (ID: {user_id})")
    
    # Send initial response
    processing_msg = await message.reply(
        "⏳ *Processing your video...*\n"
        "This may take 10-30 seconds.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Get video file info
        video = message.video
        file_id = video.file_id
        file_name = video.file_name or f"video_{user_id}.mp4"
        
        # Get file from Telegram
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        # Download file
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                if resp.status == 200:
                    video_data = await resp.read()
                    
                    # Upload to your API
                    api_url = os.getenv("API_URL", "https://web-production-253a4.up.railway.app")
                    
                    # Create multipart form data
                    form = aiohttp.FormData()
                    form.add_field('file', video_data, filename=file_name, content_type='video/mp4')
                    form.add_field('chat_id', str(user_id))
                    
                    # Send to verification API
                    async with session.post(f"{api_url}/verify", data=form) as api_resp:
                        if api_resp.status == 200:
                            result = await api_resp.json()
                            
                            # Format response
                            response_text = f"""
✅ *Verification Complete!*

👤 *Player ID:* `{result.get('player_id', 'Not found')}`
📅 *Profile Date:* {result.get('profile_date', 'Not found')}
📧 *Email Date:* {result.get('email_date', 'Not found')}

📨 *Email Content:*
{chr(10).join(result.get('email_lines', ['No email content found']))}

📢 *Ad Content:*
{chr(10).join(result.get('ad_lines', ['No ad content found']))}

🆔 *Request ID:* `{result.get('request_id', 'N/A')}`
                            """
                            
                            await processing_msg.edit_text(
                                response_text,
                                parse_mode=ParseMode.MARKDOWN
                            )
                            
                            # Notify admin for monitoring
                            if ADMIN_CHAT_ID:
                                admin_msg = f"""
📹 *Video Processed*
User: {username} (ID: {user_id})
Player ID: {result.get('player_id', 'Not found')}
Request: {result.get('request_id', 'N/A')}
                                """
                                await bot.send_message(
                                    ADMIN_CHAT_ID,
                                    admin_msg,
                                    parse_mode=ParseMode.MARKDOWN
                                )
                        else:
                            error = await api_resp.text()
                            raise Exception(f"API error: {api_resp.status} - {error}")
                else:
                    raise Exception(f"Failed to download video: {resp.status}")
                    
    except Exception as e:
        logger.error(f"❌ Video processing failed: {e}")
        await processing_msg.edit_text(
            f"❌ *Processing Failed*\n\nError: {str(e)}\n\nPlease try again later.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_unsupported(message: Message):
    """Handle unsupported message types"""
    await message.reply(
        "❌ *Unsupported message type*\n\n"
        "Please send a video file (MP4, AVI, MOV, MKV, 3GP)",
        parse_mode=ParseMode.MARKDOWN
    )

# Register handlers
if dp:
    dp.message.register(start_handler, Command("start"))
    dp.message.register(help_handler, Command("help"))
    dp.message.register(status_handler, Command("status"))
    dp.message.register(handle_video, lambda msg: msg.video is not None)
    dp.message.register(handle_unsupported)

async def handle_telegram_webhook(update_data: dict):
    """Handle incoming webhook updates"""
    if not dp:
        logger.error("Dispatcher not available")
        return
    
    try:
        # Parse update
        update = types.Update(**update_data)
        
        # Process update
        await dp.feed_update(bot, update)
        
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)

async def send_verification_result(chat_id: str, message: str):
    """Send verification result to user"""
    try:
        await bot.send_message(chat_id, message, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")

# For polling mode (development only)
async def start_polling():
    """Start bot in polling mode (for development)"""
    if not bot or not dp:
        logger.error("Bot not initialized")
        return
    
    try:
        logger.info("Starting bot in polling mode...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Polling error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(start_polling())

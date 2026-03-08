import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
API_URL = os.getenv("API_URL", "https://apnajeet-ai-verifier.up.railway.app")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Initialize bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# User state for manual entry (if needed)
user_state = {}

@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "🎮 **ApnaJeet AI Video Verifier**\n\n"
        "Send me a screen recording video and I'll extract:\n"
        "• Player ID (10-digit number)\n"
        "• Profile Date\n"
        "• Email Content\n"
        "• Ad Page Content\n\n"
        "Send /verify to begin"
    )

@dp.message(Command("verify"))
async def verify_command(message: Message):
    await message.answer(
        "🎥 **Please send your screen recording video**\n\n"
        "Make sure the video clearly shows:\n"
        "1️⃣ Profile screen (Player ID + Date)\n"
        "2️⃣ Email content (scroll slowly)\n"
        "3️⃣ Ad page after clicking link\n\n"
        "Supported formats: MP4, AVI, MOV, 3GP (max 50MB)"
    )

@dp.message(lambda message: message.video is not None)
async def handle_video(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "N/A"
    
    try:
        # Check file size
        if message.video.file_size > MAX_FILE_SIZE:
            await message.answer("❌ Video too large! Maximum size: 50MB")
            return
        
        # Send processing message
        processing_msg = await message.answer(
            "⏳ Video received! Processing with AI... (30-60 seconds)"
        )
        
        # Download video
        file = await bot.get_file(message.video.file_id)
        file_data = await bot.download_file(file.file_path)
        
        # Send to API
        async with aiohttp.ClientSession() as session:
            form_data = aiohttp.FormData()
            form_data.add_field(
                'file',
                file_data.read(),
                filename='video.mp4',
                content_type='video/mp4'
            )
            
            async with session.post(f"{API_URL}/verify", data=form_data) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Format result
                    if "error" in result:
                        await message.answer(f"❌ Error: {result['error']}")
                    else:
                        reply = "✅ **VERIFICATION COMPLETE**\n\n"
                        
                        # Player ID
                        player_id = result.get("player_id")
                        reply += f"👤 **Player ID:** {player_id if player_id else '❌ Not found'}\n"
                        
                        # Dates
                        profile_date = result.get("profile_date")
                        email_date = result.get("email_date")
                        reply += f"📅 **Profile Date:** {profile_date if profile_date else '❌ Not found'}\n"
                        reply += f"📧 **Email Date:** {email_date if email_date else '❌ Not found'}\n\n"
                        
                        # Email content
                        email_lines = result.get("email_lines", [])
                        if email_lines:
                            reply += "📧 **Email Content:**\n"
                            for line in email_lines[:3]:
                                reply += f"  • {line[:100]}{'...' if len(line) > 100 else ''}\n"
                        else:
                            reply += "📧 **Email Content:** ❌ Not found\n"
                        
                        # Ad content
                        ad_lines = result.get("ad_lines", [])
                        if ad_lines:
                            reply += "\n📢 **Ad Content:**\n"
                            for line in ad_lines[:2]:
                                reply += f"  • {line[:80]}{'...' if len(line) > 80 else ''}\n"
                        
                        # Metadata
                        metadata = result.get("metadata", {})
                        proc_time = metadata.get("processing_time_seconds", 0)
                        reply += f"\n⏱️ **Processing Time:** {proc_time:.1f}s"
                        
                        await message.answer(reply, parse_mode=ParseMode.MARKDOWN)
                        
                        # Also send to admin
                        admin_msg = f"🔔 **New Verification**\nUser: @{username}\n{reply}"
                        await bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode=ParseMode.MARKDOWN)
                        
                else:
                    error_text = await response.text()
                    await message.answer(f"❌ API Error: {response.status}")
                    logger.error(f"API Error {response.status}: {error_text[:200]}")
        
        # Delete processing message
        await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"Bot error: {str(e)}")
        await message.answer(f"❌ Error: {str(e)[:200]}")

@dp.message(Command("status"))
async def status_command(message: Message):
    if str(message.chat.id) != ADMIN_CHAT_ID:
        return
    
    await message.answer(
        "📊 **Bot Status**\n\n"
        f"✅ Bot: Running\n"
        f"✅ API: {API_URL}\n"
        f"✅ Users: 0 active"
    )

@dp.message()
async def handle_other(message: Message):
    await message.answer("Please send a video file or use /verify command.")

async def main():
    logger.info("Starting Telegram bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

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

# ============================================
# 🔥 CONFIGURATION
# ============================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# ✅ Railway deployed API URL
API_URL = "https://web-production-253a4.up.railway.app"

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# User state (optional - for multi-step verification)
user_state = {}

# ============================================
# 🔥 COMMAND HANDLERS
# ============================================
@dp.message(Command("start"))
async def start_command(message: Message):
    """Welcome message"""
    await message.answer(
        "🎮 **ApnaJeet AI Video Verifier**\n\n"
        "Send me a screen recording video and I'll extract:\n"
        "• Player ID (10-digit number)\n"
        "• Profile Date\n"
        "• Email Content\n"
        "• Ad Page Content\n\n"
        "Commands:\n"
        "/verify - Start verification\n"
        "/help - Get help\n"
        "/status - Check bot status"
    )

@dp.message(Command("help"))
async def help_command(message: Message):
    """Help message"""
    await message.answer(
        "📋 **How to Use:**\n\n"
        "1️⃣ Send /verify command\n"
        "2️⃣ Record your screen showing:\n"
        "   • Profile screen (Player ID + Date)\n"
        "   • Email content (scroll slowly)\n"
        "   • Ad page after clicking link\n"
        "3️⃣ Send the video\n"
        "4️⃣ Wait for AI processing (30-60 seconds)\n"
        "5️⃣ Get verification result\n\n"
        "Supported formats: MP4, AVI, MOV, 3GP (max 50MB)"
    )

@dp.message(Command("status"))
async def status_command(message: Message):
    """Check bot and API status"""
    try:
        # Check API health
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/health", timeout=5) as resp:
                api_status = "✅ Online" if resp.status == 200 else "❌ Error"
                
        await message.answer(
            f"📊 **Bot Status**\n\n"
            f"🤖 Bot: ✅ Running\n"
            f"🌐 API: {api_status}\n"
            f"🔗 API URL: {API_URL}\n"
            f"👤 User: @{message.from_user.username or 'N/A'}"
        )
    except Exception as e:
        await message.answer(f"❌ API Connection Error: {str(e)[:100]}")

@dp.message(Command("verify"))
async def verify_command(message: Message):
    """Start verification process"""
    await message.answer(
        "🎥 **Please send your screen recording video**\n\n"
        "Make sure the video clearly shows:\n"
        "1️⃣ Profile screen (Player ID + Date)\n"
        "2️⃣ Email content (scroll slowly)\n"
        "3️⃣ Ad page after clicking link\n\n"
        "Supported formats: MP4, AVI, MOV, 3GP (max 50MB)"
    )

# ============================================
# 🔥 VIDEO HANDLER
# ============================================
@dp.message(lambda message: message.video is not None)
async def handle_video(message: Message):
    """Process video sent by user"""
    user_id = message.from_user.id
    username = message.from_user.username or "N/A"
    
    # Create progress message
    progress_msg = await message.answer("⏳ **Processing video...** (0%)")
    
    try:
        # Check file size
        file_size = message.video.file_size
        if file_size > MAX_FILE_SIZE:
            await progress_msg.delete()
            await message.answer("❌ Video too large! Maximum size: 50MB")
            return
        
        await progress_msg.edit_text("⏳ **Downloading video...** (20%)")
        
        # Download video
        file = await bot.get_file(message.video.file_id)
        file_data = await bot.download_file(file.file_path)
        
        await progress_msg.edit_text("⏳ **Sending to AI...** (40%)")
        
        # Send to API
        async with aiohttp.ClientSession() as session:
            form_data = aiohttp.FormData()
            form_data.add_field(
                'file',
                file_data.read(),
                filename='video.mp4',
                content_type='video/mp4'
            )
            
            async with session.post(f"{API_URL}/verify", data=form_data, timeout=120) as response:
                await progress_msg.edit_text("⏳ **AI processing...** (70%)")
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Format result message
                    reply = await format_result(result, username)
                    
                    await progress_msg.delete()
                    await message.answer(reply, parse_mode=ParseMode.MARKDOWN)
                    
                    # Also send to admin
                    if ADMIN_CHAT_ID:
                        admin_msg = f"🔔 **New Verification**\nUser: @{username}\n\n{reply}"
                        await bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode=ParseMode.MARKDOWN)
                        
                else:
                    error_text = await response.text()
                    await progress_msg.delete()
                    await message.answer(f"❌ API Error ({response.status}): {error_text[:200]}")
                    
    except asyncio.TimeoutError:
        await progress_msg.delete()
        await message.answer("❌ Request timeout! AI processing took too long ( >2 minutes).")
    except Exception as e:
        logger.error(f"Bot error: {str(e)}")
        await progress_msg.delete()
        await message.answer(f"❌ Error: {str(e)[:200]}")

# ============================================
# 🔥 RESULT FORMATTER
# ============================================
async def format_result(result: dict, username: str) -> str:
    """Format API response into nice message"""
    
    # Extract data
    player_id = result.get("player_id")
    profile_date = result.get("profile_date")
    email_date = result.get("email_date")
    email_lines = result.get("email_lines", [])
    ad_lines = result.get("ad_lines", [])
    metadata = result.get("metadata", {})
    
    # Build message
    reply = "✅ **VERIFICATION COMPLETE**\n\n"
    
    # Player ID
    if player_id:
        reply += f"👤 **Player ID:** `{player_id}`\n"
    else:
        reply += f"👤 **Player ID:** ❌ Not found\n"
    
    # Dates
    reply += f"📅 **Profile Date:** {profile_date or '❌ Not found'}\n"
    reply += f"📧 **Email Date:** {email_date or '❌ Not found'}\n\n"
    
    # Email content
    if email_lines:
        reply += "📧 **Email Content:**\n"
        for i, line in enumerate(email_lines[:3]):  # Max 3 lines
            short_line = line[:100] + "..." if len(line) > 100 else line
            reply += f"  {i+1}. {short_line}\n"
    else:
        reply += "📧 **Email Content:** ❌ Not found\n"
    
    # Ad content
    if ad_lines:
        reply += "\n📢 **Ad Content:**\n"
        for i, line in enumerate(ad_lines[:2]):  # Max 2 lines
            short_line = line[:80] + "..." if len(line) > 80 else line
            reply += f"  {i+1}. {short_line}\n"
    
    # Metadata
    proc_time = metadata.get("processing_time_seconds", 0)
    frames = metadata.get("frames_processed", 0)
    reply += f"\n⏱️ **Time:** {proc_time:.1f}s | 📊 **Frames:** {frames}"
    
    return reply

# ============================================
# 🔥 FALLBACK HANDLER
# ============================================
@dp.message()
async def handle_other(message: Message):
    """Handle non-video messages"""
    await message.answer(
        "❌ Please send a video file.\n"
        "Use /verify command for instructions."
    )

# ============================================
# 🔥 START BOT
# ============================================
async def main():
    logger.info("=" * 50)
    logger.info("🚀 Starting Telegram Bot...")
    logger.info(f"Bot Token: {BOT_TOKEN[:10]}...")
    logger.info(f"Admin Chat ID: {ADMIN_CHAT_ID}")
    logger.info(f"API URL: {API_URL}")
    logger.info("=" * 50)
    
    # Test API connection
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/health", timeout=5) as resp:
                if resp.status == 200:
                    logger.info("✅ API connection successful")
                else:
                    logger.warning(f"⚠️ API returned status {resp.status}")
    except Exception as e:
        logger.error(f"❌ API connection failed: {e}")
    
    # Start bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

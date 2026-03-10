# [Filename: telegram_bot/bot.py]
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import httpx
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
PROCESSOR_URL = os.getenv("PROCESSOR_URL", "http://video-processor:8082")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome! Send me a screenshot of your gaming screen.\n"
        "I'll extract your Player ID and verify it!"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos sent by user"""
    await update.message.reply_text("📸 Processing your screenshot...")
    
    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Download photo
        photo_bytes = await file.download_as_bytearray()
        
        # Send to processor server
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {'file': ('screenshot.jpg', photo_bytes, 'image/jpeg')}
            response = await client.post(f"{PROCESSOR_URL}/process", files=files)
            
            if response.status_code == 200:
                result = response.json()
                
                # Format response
                msg = f"""
✅ *Verification Complete!*

👤 *Player ID:* `{result.get('player_id', 'Not found')}`
📅 *Date:* {result.get('date', 'Not found')}
📊 *Confidence:* {result.get('confidence', 0)}%

📧 *Email Match:* {result.get('matches', {}).get('email_match', 0)}%
📢 *Ad Match:* {result.get('matches', {}).get('ad_match', 0)}%

🔍 *Status:* {'✅ Verified' if result.get('player_valid') else '❌ Not Found'}
                """
                await update.message.reply_text(msg, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Processing failed. Try again.")
                
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Error processing image. Try again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_error_handler(error_handler)
    
    logger.info("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()

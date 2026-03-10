# [Filename: telegram-bot/bot.py]
import os
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get environment variables
TOKEN = os.getenv("BOT_TOKEN")
PROCESSOR_URL = os.getenv("PROCESSOR_URL", "http://video-processor:8082")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hi {user.first_name}!\n\n"
        "Send me a screenshot of your gaming screen and I'll verify it.\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Get help"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when /help is issued."""
    await update.message.reply_text(
        "📸 How to use:\n"
        "1. Take a screenshot of your gaming screen\n"
        "2. Send the screenshot to me\n"
        "3. Wait 5-10 seconds for processing\n"
        "4. Get verification result\n\n"
        "Make sure the screenshot clearly shows:\n"
        "• Player ID (10 digits)\n"
        "• Profile date\n"
        "• Email content\n"
        "• Ad content"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos sent by user."""
    await update.message.reply_text("📥 Received screenshot! Processing...")
    
    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Download photo
        photo_bytes = await file.download_as_bytearray()
        
        # Send to processor server
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {'file': ('screenshot.jpg', photo_bytes, 'image/jpeg')}
            
            # Try multiple possible URLs
            urls_to_try = [
                PROCESSOR_URL,
                "https://video-processor.up.railway.app",
                "http://video-processor:8082"
            ]
            
            success = False
            for url in urls_to_try:
                try:
                    processor_url = f"{url}/process"
                    logger.info(f"Trying processor at: {processor_url}")
                    
                    response = await client.post(processor_url, files=files)
                    
                    if response.status_code == 200:
                        result = response.json()
                        success = True
                        
                        # Format response
                        msg = (
                            f"✅ *Verification Complete!*\n\n"
                            f"👤 *Player ID:* `{result.get('player_id', 'Not found')}`\n"
                            f"📅 *Date:* {result.get('date', 'Not found')}\n"
                            f"📊 *Confidence:* {result.get('confidence', 0)}%\n\n"
                            f"📧 *Email Match:* {result.get('matches', {}).get('email_match', 0)}%\n"
                            f"📢 *Ad Match:* {result.get('matches', {}).get('ad_match', 0)}%\n\n"
                            f"🔍 *Status:* {'✅ Verified' if result.get('player_valid') else '❌ Not Found'}"
                        )
                        await update.message.reply_text(msg, parse_mode='Markdown')
                        break
                        
                except Exception as e:
                    logger.warning(f"Failed with URL {url}: {e}")
                    continue
            
            if not success:
                await update.message.reply_text("❌ Processor server not available. Try again later.")
                
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await update.message.reply_text("❌ Error processing image. Please try again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot."""
    if not TOKEN:
        logger.error("No BOT_TOKEN found in environment!")
        return
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Bot started! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

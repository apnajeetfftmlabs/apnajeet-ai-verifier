# [Filename: telegram-bot/bot.py]
import os
import logging
from flask import Flask, request
import httpx
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.getenv("BOT_TOKEN")
PROCESSOR_URL = os.getenv("PROCESSOR_URL", "https://video-processor.up.railway.app")
PORT = int(os.getenv("PORT", 8080))

# Flask app for webhook
flask_app = Flask(__name__)

# Telegram application
telegram_app = Application.builder().token(TOKEN).build()

# ============ HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hi {user.first_name}!\n\n"
        "Send me a screenshot of your gaming screen and I'll verify it.\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Get help"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await update.message.reply_text(
        "📸 How to use:\n"
        "1. Take a screenshot of your gaming screen\n"
        "2. Send the screenshot to me\n"
        "3. Wait 5-10 seconds\n"
        "4. Get verification result\n\n"
        "Make sure the screenshot clearly shows:\n"
        "• Player ID (10 digits)\n"
        "• Profile date\n"
        "• Email content"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos sent by user"""
    await update.message.reply_text("📥 Processing your screenshot...")
    
    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Download photo
        photo_bytes = await file.download_as_bytearray()
        
        # Send to video processor
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {'file': ('screenshot.jpg', photo_bytes, 'image/jpeg')}
            
            logger.info(f"Sending to processor: {PROCESSOR_URL}/process")
            response = await client.post(f"{PROCESSOR_URL}/process", files=files)
            
            if response.status_code == 200:
                result = response.json()
                
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
            else:
                await update.message.reply_text("❌ Processing failed. Try again.")
                
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await update.message.reply_text("❌ Error occurred. Please try again.")

# Register handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# ============ WEBHOOK ENDPOINT ============

@flask_app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    """Telegram sends updates here"""
    try:
        update_data = request.get_json()
        update = Update.de_json(update_data, telegram_app.bot)
        
        # Process update in background
        asyncio.run_coroutine_threadsafe(
            telegram_app.process_update(update),
            telegram_app.loop
        )
        
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

@flask_app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return {"status": "healthy"}, 200

@flask_app.route("/", methods=["GET"])
def root():
    """Root endpoint"""
    return {
        "service": "Telegram Bot",
        "status": "running",
        "mode": "webhook",
        "processor_url": PROCESSOR_URL
    }, 200

# ============ SET WEBHOOK FUNCTION ============

def set_webhook():
    """Delete old webhook and set new one"""
    import requests
    
    # Get Railway URL
    railway_url = os.getenv("RAILWAY_PUBLIC_URL", f"https://{os.getenv('RAILWAY_STATIC_URL', 'localhost')}")
    webhook_url = f"{railway_url}/webhook/{TOKEN}"
    
    logger.info(f"Setting webhook to: {webhook_url}")
    
    # Delete old webhook first
    delete_response = requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
    logger.info(f"Delete webhook response: {delete_response.json()}")
    
    # Set new webhook
    set_response = requests.get(
        f"https://api.telegram.org/bot{TOKEN}/setWebhook",
        params={"url": webhook_url}
    )
    
    logger.info(f"Set webhook response: {set_response.json()}")
    
    if set_response.json().get("ok"):
        logger.info("✅ Webhook set successfully!")
    else:
        logger.error("❌ Failed to set webhook")

# ============ MAIN ============

if __name__ == "__main__":
    # Set webhook on startup
    set_webhook()
    
    # Start Flask app
    logger.info(f"Starting bot on port {PORT}")
    flask_app.run(host="0.0.0.0", port=PORT)

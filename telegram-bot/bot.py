# [Filename: telegram-bot/bot.py] - FINAL FIXED VERSION
import os
import logging
from flask import Flask, request
import httpx
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
TOKEN = os.getenv("BOT_TOKEN")
PROCESSOR_URL = os.getenv("PROCESSOR_URL", "https://apnajeet-ai-verifier-production-e660.up.railway.app")
PORT = int(os.getenv("PORT", 8080))

# Conversation states
PROFILE, EMAIL, AD = range(3)

# Flask app
app = Flask(__name__)

# ============ TELEGRAM APP SETUP ============

# Create application
telegram_app = Application.builder().token(TOKEN).build()

# CRITICAL FIX: Initialize the application
import asyncio
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(telegram_app.initialize())
logger.info("✅ Telegram application initialized")

# User data storage (temporary)
user_screenshots = {}

# ============ HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the verification process"""
    user = update.effective_user
    user_id = user.id
    
    # Initialize user data
    user_screenshots[user_id] = {'profile': None, 'email': None, 'ad': None}
    
    await update.message.reply_text(
        f"👋 Hi {user.first_name}!\n\n"
        "📸 *3-Step Verification Process*\n\n"
        "I need 3 screenshots from you:\n"
        "1️⃣ *Profile Screen* - Showing your Player ID and Date of Birth\n"
        "2️⃣ *Email Content* - The email you received\n"
        "3️⃣ *Ad Page* - The advertisement page\n\n"
        "Please send the **PROFILE** screenshot first:",
        parse_mode='Markdown'
    )
    return PROFILE

async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle profile screenshot"""
    user_id = update.effective_user.id
    
    # Save photo
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    
    user_screenshots[user_id]['profile'] = photo_bytes
    
    await update.message.reply_text(
        "✅ Profile screenshot received!\n\n"
        "Now please send the **EMAIL** screenshot:",
        parse_mode='Markdown'
    )
    return EMAIL

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle email screenshot"""
    user_id = update.effective_user.id
    
    # Save photo
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    
    user_screenshots[user_id]['email'] = photo_bytes
    
    await update.message.reply_text(
        "✅ Email screenshot received!\n\n"
        "Finally, please send the **AD** screenshot:",
        parse_mode='Markdown'
    )
    return AD

async def handle_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ad screenshot and process all three"""
    user_id = update.effective_user.id
    
    # Save photo
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    
    user_screenshots[user_id]['ad'] = photo_bytes
    
    await update.message.reply_text("📥 All 3 screenshots received! Processing... (This may take 10-15 seconds)")
    
    try:
        # Send all three images to processor
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Prepare multipart form data
            files = {
                'profile': ('profile.jpg', user_screenshots[user_id]['profile'], 'image/jpeg'),
                'email': ('email.jpg', user_screenshots[user_id]['email'], 'image/jpeg'),
                'ad': ('ad.jpg', user_screenshots[user_id]['ad'], 'image/jpeg')
            }
            
            # Send to processor
            response = await client.post(f"{PROCESSOR_URL}/verify-three", files=files)
            
            if response.status_code == 200:
                result = response.json()
                
                # Format response
                msg = (
                    f"✅ *Verification Complete!*\n\n"
                    f"👤 *Player ID:* `{result.get('player_id', 'Not found')}`\n"
                    f"📅 *DOB:* {result.get('dob', 'Not found')}\n\n"
                    f"📧 *Email Match:* {result.get('email_match', 0)}%\n"
                    f"📢 *Ad Match:* {result.get('ad_match', 0)}%\n"
                    f"📊 *Overall Confidence:* {result.get('confidence', 0)}%\n\n"
                    f"🔍 *Status:* {'✅ Verified' if result.get('verified') else '❌ Not Verified'}"
                )
                await update.message.reply_text(msg, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Processing failed. Please try again.")
                
    except Exception as e:
        logger.error(f"Processing error: {e}")
        await update.message.reply_text("❌ Error occurred. Please try again.")
    
    # Clear user data
    del user_screenshots[user_id]
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation"""
    user_id = update.effective_user.id
    if user_id in user_screenshots:
        del user_screenshots[user_id]
    await update.message.reply_text("❌ Verification cancelled. Send /start to begin again.")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    await update.message.reply_text(
        "📸 *How to use:*\n\n"
        "1️⃣ Send /start to begin\n"
        "2️⃣ Send PROFILE screenshot (with Player ID and DOB)\n"
        "3️⃣ Send EMAIL screenshot\n"
        "4️⃣ Send AD screenshot\n"
        "5️⃣ Get verification result\n\n"
        "📌 *Note:* All 3 images are required for verification.",
        parse_mode='Markdown'
    )

# Register handlers
telegram_app.add_handler(ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        PROFILE: [MessageHandler(filters.PHOTO, handle_profile)],
        EMAIL: [MessageHandler(filters.PHOTO, handle_email)],
        AD: [MessageHandler(filters.PHOTO, handle_ad)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
))
telegram_app.add_handler(CommandHandler('help', help_command))

# ============ FIXED WEBHOOK FUNCTION ============

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    """Telegram webhook - FIXED with proper async handling"""
    update_data = request.get_json()
    update = Update.de_json(update_data, telegram_app.bot)
    
    try:
        # Run the update processing in the existing loop
        asyncio.run_coroutine_threadsafe(
            telegram_app.process_update(update),
            loop
        )
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy"}, 200

@app.route("/", methods=["GET"])
def root():
    return {"service": "Telegram Bot", "status": "running", "mode": "3-image"}, 200

def set_webhook():
    """Set webhook on startup"""
    import requests
    railway_url = "https://protective-fulfillment-production-be90.up.railway.app"
    webhook_url = f"{railway_url}/webhook/{TOKEN}"
    
    logger.info(f"Setting webhook to: {webhook_url}")
    
    # Delete old webhook
    del_resp = requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true")
    logger.info(f"Delete response: {del_resp.json()}")
    
    # Set new webhook
    set_resp = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook", params={"url": webhook_url})
    logger.info(f"Set response: {set_resp.json()}")

if __name__ == "__main__":
    # Set webhook on startup
    set_webhook()
    
    # Start Flask app
    app.run(host="0.0.0.0", port=PORT)

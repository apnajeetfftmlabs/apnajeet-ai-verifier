# [Filename: telegram-bot/bot_aiohttp.py]
import os
import logging
from aiohttp import web
import httpx
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

# Initialize bot application
application = Application.builder().token(TOKEN).build()

# User data storage
user_screenshots = {}

# ============ HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_screenshots[user_id] = {'profile': None, 'email': None, 'ad': None}
    
    await update.message.reply_text(
        f"👋 Hi {user.first_name}!\n\n"
        "📸 *3-Step Verification Process*\n\n"
        "I need 3 screenshots:\n"
        "1️⃣ *Profile Screen* - Player ID and Date of Birth\n"
        "2️⃣ *Email Content*\n"
        "3️⃣ *Ad Page*\n\n"
        "Please send the **PROFILE** screenshot first:",
        parse_mode='Markdown'
    )
    return PROFILE

async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    user_screenshots[user_id]['profile'] = photo_bytes
    
    await update.message.reply_text(
        "✅ Profile received!\n\nNow send **EMAIL** screenshot:",
        parse_mode='Markdown'
    )
    return EMAIL

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    user_screenshots[user_id]['email'] = photo_bytes
    
    await update.message.reply_text(
        "✅ Email received!\n\nFinally send **AD** screenshot:",
        parse_mode='Markdown'
    )
    return AD

async def handle_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    user_screenshots[user_id]['ad'] = photo_bytes
    
    await update.message.reply_text("📥 Processing 3 images... (10-15 seconds)")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {
                'profile': ('profile.jpg', user_screenshots[user_id]['profile'], 'image/jpeg'),
                'email': ('email.jpg', user_screenshots[user_id]['email'], 'image/jpeg'),
                'ad': ('ad.jpg', user_screenshots[user_id]['ad'], 'image/jpeg')
            }
            
            response = await client.post(f"{PROCESSOR_URL}/verify-three", files=files)
            
            if response.status_code == 200:
                result = response.json()
                msg = (
                    f"✅ *Verification Complete!*\n\n"
                    f"👤 *Player ID:* `{result.get('player_id', 'Not found')}`\n"
                    f"📅 *DOB:* {result.get('dob', 'Not found')}\n\n"
                    f"📧 *Email Match:* {result.get('email_match', 0)}%\n"
                    f"📢 *Ad Match:* {result.get('ad_match', 0)}%\n"
                    f"📊 *Confidence:* {result.get('confidence', 0)}%\n\n"
                    f"🔍 *Status:* {'✅ Verified' if result.get('verified') else '❌ Not Verified'}"
                )
                await update.message.reply_text(msg, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Processing failed")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Error occurred")
    
    del user_screenshots[user_id]
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_screenshots:
        del user_screenshots[user_id]
    await update.message.reply_text("❌ Cancelled. Send /start to begin.")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 *How to use:*\n\n"
        "1️⃣ /start\n2️⃣ Profile screenshot\n3️⃣ Email screenshot\n4️⃣ Ad screenshot",
        parse_mode='Markdown'
    )

# Add handlers
application.add_handler(ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        PROFILE: [MessageHandler(filters.PHOTO, handle_profile)],
        EMAIL: [MessageHandler(filters.PHOTO, handle_email)],
        AD: [MessageHandler(filters.PHOTO, handle_ad)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
))
application.add_handler(CommandHandler('help', help_command))

# Initialize application
async def init_app():
    await application.initialize()
    await application.bot.set_webhook(url=f"https://protective-fulfillment-production-be90.up.railway.app/webhook/{TOKEN}")
    logger.info("✅ Bot initialized and webhook set")

# ============ AIOHTTP WEBHOOK HANDLER ============

async def webhook_handler(request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return web.Response(text="OK", status=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(text="Error", status=500)

async def health_handler(request):
    return web.json_response({"status": "healthy"})

async def root_handler(request):
    return web.json_response({
        "service": "Telegram Bot",
        "status": "running",
        "mode": "3-image"
    })

# ============ MAIN ============

async def main():
    # Initialize bot
    await init_app()
    
    # Setup web app
    web_app = web.Application()
    web_app.router.add_post(f"/webhook/{TOKEN}", webhook_handler)
    web_app.router.add_get("/health", health_handler)
    web_app.router.add_get("/", root_handler)
    
    # Start server
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"🚀 Server running on port {PORT}")
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

# [Filename: api/main.py]
import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio

# Import bot modules
try:
    from bot.telegram_bot import bot, dp, handle_telegram_webhook
    BOT_AVAILABLE = True
    logging.info("✅ Telegram bot module loaded")
except ImportError as e:
    BOT_AVAILABLE = False
    logging.warning(f"⚠️ Telegram bot not available: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="ApnaJeet AI Video Verifier")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.3gp'}

# ============================================
# BASIC ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "port": os.getenv("PORT", "8080"),
        "service": "ApnaJeet AI Video Verifier",
        "version": "1.0",
        "features": {
            "telegram_bot": BOT_AVAILABLE
        }
    }

@app.get("/health")
async def health():
    """Health check for Railway"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "up",
            "telegram_bot": "enabled" if BOT_AVAILABLE else "disabled"
        }
    }

# ============================================
# TELEGRAM WEBHOOK ENDPOINT
# ============================================

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Handle Telegram bot updates via webhook
    """
    if not BOT_AVAILABLE:
        logger.error("Telegram bot not available")
        return {"error": "Bot not available"}
    
    try:
        # Get update from Telegram
        update_data = await request.json()
        logger.info(f"📨 Received Telegram update: {update_data.get('update_id')}")
        
        # Process update
        await handle_telegram_webhook(update_data)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

# ============================================
# SET WEBHOOK ENDPOINT (Admin only)
# ============================================

@app.post("/admin/set-webhook")
async def set_webhook(secret_token: str):
    """
    Set Telegram bot webhook (Admin only)
    """
    # Simple admin check - in production use proper auth
    if secret_token != os.getenv("ADMIN_SECRET", "apnajeet123"):
        raise HTTPException(403, "Unauthorized")
    
    if not BOT_AVAILABLE:
        raise HTTPException(500, "Bot not available")
    
    try:
        # Get Railway URL
        railway_url = os.getenv("RAILWAY_PUBLIC_URL", "https://web-production-253a4.up.railway.app")
        webhook_url = f"{railway_url}/webhook/telegram"
        
        # Set webhook
        success = await bot.set_webhook(webhook_url)
        
        if success:
            # Get webhook info
            webhook_info = await bot.get_webhook_info()
            
            return {
                "status": "success",
                "webhook_url": webhook_url,
                "webhook_info": {
                    "url": webhook_info.url,
                    "has_custom_certificate": webhook_info.has_custom_certificate,
                    "pending_update_count": webhook_info.pending_update_count,
                    "max_connections": webhook_info.max_connections
                }
            }
        else:
            return {"status": "failed", "message": "Could not set webhook"}
            
    except Exception as e:
        logger.error(f"❌ Set webhook error: {e}")
        raise HTTPException(500, str(e))

# ============================================
# DELETE WEBHOOK ENDPOINT
# ============================================

@app.post("/admin/delete-webhook")
async def delete_webhook(secret_token: str):
    """Delete Telegram bot webhook"""
    if secret_token != os.getenv("ADMIN_SECRET", "apnajeet123"):
        raise HTTPException(403, "Unauthorized")
    
    if not BOT_AVAILABLE:
        raise HTTPException(500, "Bot not available")
    
    try:
        success = await bot.delete_webhook()
        return {"status": "success" if success else "failed"}
    except Exception as e:
        raise HTTPException(500, str(e))

# ============================================
# VERIFY ENDPOINT (With Telegram Notification)
# ============================================

@app.post("/verify")
async def verify_video(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    user_id: Optional[str] = None,
    chat_id: Optional[str] = None
):
    """
    Upload video and extract player info
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] New verification request: {file.filename}")
    
    # Validate file
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Invalid format. Allowed: {ALLOWED_EXTENSIONS}")
    
    try:
        # Read file
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(400, f"File too large. Max {MAX_FILE_SIZE//(1024*1024)}MB")
        
        # Save file
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Mock result (replace with actual AI)
        result = {
            "player_id": "1234567890",
            "profile_date": "09/03/2026",
            "email_date": "March 9, 2026",
            "email_lines": [
                "A $10,000 Gold Target Is Now Being Discussed",
                "Gold continues to hit new record high..."
            ],
            "ad_lines": [
                "Elite Trade Club - Start your day with the trends"
            ],
            "filename": file.filename,
            "request_id": request_id,
            "processed_at": datetime.now().isoformat()
        }
        
        # Send Telegram notification if chat_id provided
        if chat_id and BOT_AVAILABLE:
            background_tasks.add_task(
                send_telegram_notification,
                chat_id=chat_id,
                result=result,
                file_path=file_path
            )
        
        # Cleanup file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Error: {e}")
        raise HTTPException(500, f"Verification failed")

async def send_telegram_notification(chat_id: str, result: dict, file_path: str):
    """Send verification result to Telegram"""
    try:
        from bot.telegram_bot import send_verification_result
        
        message = f"""
✅ *Verification Complete!*

👤 *Player ID:* `{result['player_id']}`
📅 *Profile Date:* {result['profile_date']}
📧 *Email Date:* {result['email_date']}

📨 *Email Preview:*
{chr(10).join(result['email_lines'][:3])}

📢 *Ad Content:*
{chr(10).join(result['ad_lines'][:2])}

🆔 *Request ID:* `{result['request_id']}`
        """
        
        await send_verification_result(chat_id, message)
        logger.info(f"✅ Telegram notification sent to {chat_id}")
        
    except Exception as e:
        logger.error(f"❌ Telegram notification failed: {e}")

# ============================================
# DEBUG ENDPOINTS
# ============================================

@app.get("/debug")
async def debug_info():
    """Debug endpoint"""
    return {
        "cwd": os.getcwd(),
        "files": os.listdir('.'),
        "env_vars": {k: v for k, v in os.environ.items() 
                    if not any(secret in k.lower() 
                    for secret in ['token', 'key', 'pass', 'cred'])},
        "bot_available": BOT_AVAILABLE,
        "upload_dir_exists": os.path.exists(UPLOAD_DIR),
        "upload_dir_writable": os.access(UPLOAD_DIR, os.W_OK) if os.path.exists(UPLOAD_DIR) else False
    }

@app.post("/echo")
async def echo_file(file: UploadFile = File(...)):
    """Echo file info for testing"""
    content = await file.read()
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(content)
    }

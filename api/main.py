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
import shutil
from pathlib import Path

# Import bot modules
try:
    from bot.telegram_bot import bot, dp, handle_telegram_webhook, send_verification_result
    BOT_AVAILABLE = True
    logging.info("✅ Telegram bot module loaded")
except ImportError as e:
    BOT_AVAILABLE = False
    logging.warning(f"⚠️ Telegram bot not available: {e}")

# Import AI modules (optional)
try:
    from ai.pipeline import VideoProcessor
    AI_AVAILABLE = True
    logging.info("✅ AI pipeline module loaded")
except ImportError as e:
    AI_AVAILABLE = False
    logging.warning(f"⚠️ AI pipeline not available: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="ApnaJeet AI Video Verifier",
    version="1.0.0",
    description="AI-powered video verification for gaming tournaments"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.3gp'}

# Global components
video_processor = None

@app.on_event("startup")
async def startup_event():
    """Initialize heavy components on startup"""
    global video_processor
    logger.info("🚀 Starting ApnaJeet AI Video Verifier...")
    
    # Initialize video processor if AI available
    if AI_AVAILABLE:
        try:
            video_processor = VideoProcessor()
            logger.info("✅ Video processor initialized")
        except Exception as e:
            logger.error(f"❌ Video processor initialization failed: {e}")
            video_processor = None

# ============================================
# BASIC ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Health check endpoint"""
    port = os.getenv("PORT", "8080")
    railway_url = os.getenv("RAILWAY_PUBLIC_URL", "https://web-production-253a4.up.railway.app")
    
    return {
        "status": "ok",
        "port": port,
        "service": "ApnaJeet AI Video Verifier",
        "version": "1.0.0",
        "features": {
            "telegram_bot": BOT_AVAILABLE,
            "ai_pipeline": AI_AVAILABLE and video_processor is not None
        },
        "endpoints": {
            "health": "/health",
            "verify": "/verify (POST)",
            "telegram_webhook": "/webhook/telegram (POST)",
            "set_webhook": "/admin/set-webhook?secret_token=YOUR_TOKEN",
            "delete_webhook": "/admin/delete-webhook?secret_token=YOUR_TOKEN",
            "debug": "/debug"
        },
        "documentation": "https://github.com/apnajeetfftmlabs/apnajeet-ai-verifier"
    }

@app.get("/health")
async def health():
    """Health check for Railway"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "up",
            "telegram_bot": "enabled" if BOT_AVAILABLE else "disabled",
            "ai_pipeline": "ready" if video_processor else "loading" if AI_AVAILABLE else "disabled"
        },
        "disk_space": {
            "free": shutil.disk_usage("/").free // (2**30),  # GB
            "total": shutil.disk_usage("/").total // (2**30)
        }
    }

@app.get("/test")
async def test():
    """Simple test endpoint"""
    return {"message": "working", "timestamp": datetime.now().isoformat()}

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
        update_id = update_data.get('update_id', 'unknown')
        logger.info(f"📨 Received Telegram update: {update_id}")
        
        # Process update
        await handle_telegram_webhook(update_data)
        
        return {"status": "ok", "update_id": update_id}
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

# ============================================
# ADMIN WEBHOOK MANAGEMENT
# ============================================

@app.get("/admin/set-webhook")
async def set_webhook_get(secret_token: str):
    """
    Set Telegram bot webhook via GET (for browser)
    """
    return await set_webhook_logic(secret_token)

@app.post("/admin/set-webhook")
async def set_webhook_post(request: Request):
    """
    Set Telegram bot webhook via POST
    """
    try:
        data = await request.json()
        secret_token = data.get("secret_token")
    except:
        secret_token = None
    
    return await set_webhook_logic(secret_token)

async def set_webhook_logic(secret_token: str):
    """
    Common webhook setting logic
    """
    # Simple admin check
    admin_secret = os.getenv("ADMIN_SECRET", "apnajeet123")
    
    if secret_token != admin_secret:
        return JSONResponse(
            status_code=403,
            content={
                "error": "Unauthorized",
                "message": "Invalid secret token",
                "hint": f"Use ?secret_token={admin_secret} in URL"
            }
        )
    
    if not BOT_AVAILABLE:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Bot not available",
                "message": "Telegram bot module not loaded",
                "check": [
                    "Is BOT_TOKEN set in Railway variables?",
                    "Is bot/telegram_bot.py present?",
                    "Check logs for import errors"
                ]
            }
        )
    
    try:
        # Get Railway URL
        railway_url = os.getenv("RAILWAY_PUBLIC_URL", "https://web-production-253a4.up.railway.app")
        webhook_url = f"{railway_url}/webhook/telegram"
        
        logger.info(f"🔧 Setting webhook to: {webhook_url}")
        
        # Delete old webhook first
        await bot.delete_webhook()
        logger.info("🗑️ Old webhook deleted")
        
        # Set new webhook
        success = await bot.set_webhook(
            webhook_url,
            max_connections=40,
            allowed_updates=["message", "callback_query"]
        )
        
        if success:
            # Get webhook info
            webhook_info = await bot.get_webhook_info()
            
            # Send test message to admin
            try:
                admin_chat_id = os.getenv("ADMIN_CHAT_ID")
                if admin_chat_id:
                    await bot.send_message(
                        admin_chat_id,
                        f"✅ *Webhook Configured*\n\n"
                        f"URL: `{webhook_url}`\n"
                        f"Bot is now live!\n\n"
                        f"📱 Open Telegram and search for @apnajeet_verifier_bot",
                        parse_mode="Markdown"
                    )
                    logger.info(f"📱 Test message sent to admin {admin_chat_id}")
            except Exception as e:
                logger.warning(f"Could not send test message: {e}")
            
            return {
                "status": "success",
                "message": "✅ Webhook set successfully! Bot is now live.",
                "webhook_url": webhook_url,
                "webhook_info": {
                    "url": webhook_info.url,
                    "has_custom_certificate": webhook_info.has_custom_certificate,
                    "pending_update_count": webhook_info.pending_update_count,
                    "max_connections": webhook_info.max_connections,
                    "allowed_updates": webhook_info.allowed_updates
                },
                "bot_info": {
                    "username": (await bot.get_me()).username,
                    "is_bot": True,
                    "can_join_groups": (await bot.get_me()).can_join_groups
                },
                "next_steps": [
                    "1. Open Telegram and search for @apnajeet_verifier_bot",
                    "2. Send /start command",
                    "3. Send a video to test"
                ]
            }
        else:
            return {
                "status": "failed",
                "message": "❌ Could not set webhook. Check bot token.",
                "check_token": f"Bot token starts with: {BOT_TOKEN[:5]}...{BOT_TOKEN[-5:]}" if BOT_TOKEN else "No token",
                "token_length": len(BOT_TOKEN) if BOT_TOKEN else 0
            }
            
    except Exception as e:
        logger.error(f"❌ Set webhook error: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }

@app.get("/admin/delete-webhook")
async def delete_webhook_get(secret_token: str):
    """
    Delete Telegram bot webhook via GET
    """
    return await delete_webhook_logic(secret_token)

@app.post("/admin/delete-webhook")
async def delete_webhook_post(request: Request):
    """
    Delete Telegram bot webhook via POST
    """
    try:
        data = await request.json()
        secret_token = data.get("secret_token")
    except:
        secret_token = None
    
    return await delete_webhook_logic(secret_token)

async def delete_webhook_logic(secret_token: str):
    """Common webhook deletion logic"""
    admin_secret = os.getenv("ADMIN_SECRET", "apnajeet123")
    
    if secret_token != admin_secret:
        return JSONResponse(
            status_code=403,
            content={"error": "Unauthorized", "message": "Invalid secret token"}
        )
    
    if not BOT_AVAILABLE:
        return JSONResponse(
            status_code=500,
            content={"error": "Bot not available"}
        )
    
    try:
        success = await bot.delete_webhook()
        
        if success:
            return {
                "status": "success",
                "message": "✅ Webhook deleted successfully. Bot is now in polling mode (not active).",
                "next_step": "Run /admin/set-webhook to re-enable bot"
            }
        else:
            return {
                "status": "failed",
                "message": "❌ Could not delete webhook"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/admin/webhook-info")
async def webhook_info_get(secret_token: str):
    """Get current webhook info"""
    admin_secret = os.getenv("ADMIN_SECRET", "apnajeet123")
    
    if secret_token != admin_secret:
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    
    if not BOT_AVAILABLE:
        return JSONResponse(status_code=500, content={"error": "Bot not available"})
    
    try:
        webhook_info = await bot.get_webhook_info()
        return {
            "status": "success",
            "webhook_info": {
                "url": webhook_info.url,
                "has_custom_certificate": webhook_info.has_custom_certificate,
                "pending_update_count": webhook_info.pending_update_count,
                "max_connections": webhook_info.max_connections,
                "last_error_date": webhook_info.last_error_date,
                "last_error_message": webhook_info.last_error_message
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============================================
# VERIFY ENDPOINT (Main Video Processing)
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
    
    Parameters:
    - file: Video file (MP4, AVI, MOV, MKV, 3GP)
    - user_id: Optional user identifier
    - chat_id: Optional Telegram chat ID for notification
    
    Returns:
    - Extracted player information
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] 📥 New verification request: {file.filename}")
    
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format. Allowed: {ALLOWED_EXTENSIONS}"
        )
    
    try:
        # Read file
        content = await file.read()
        file_size = len(content)
        
        # Validate file size
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max {MAX_FILE_SIZE//(1024*1024)}MB"
            )
        
        logger.info(f"[{request_id}] 📊 Size: {file_size/1024/1024:.2f}MB")
        
        # Save file temporarily
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"[{request_id}] 💾 Saved: {file_path}")
        
        # Process video (mock or real AI)
        if video_processor:
            # Real AI processing
            logger.info(f"[{request_id}] 🧠 Using AI pipeline")
            result = await process_with_ai(request_id, str(file_path), file.filename)
        else:
            # Mock result for testing
            logger.info(f"[{request_id}] 🎭 Using mock result")
            result = get_mock_result(request_id, file.filename)
        
        # Send Telegram notification if chat_id provided
        if chat_id and BOT_AVAILABLE:
            background_tasks.add_task(
                send_telegram_notification,
                chat_id=chat_id,
                result=result
            )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] ❌ Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Verification failed: {str(e)}"
        )
    finally:
        # Cleanup file in background
        if 'file_path' in locals() and file_path.exists():
            background_tasks.add_task(cleanup_file, str(file_path))

async def process_with_ai(request_id: str, file_path: str, original_filename: str) -> Dict:
    """Process video with AI pipeline"""
    try:
        result = await video_processor.process_video(file_path)
        
        # Add metadata
        result.update({
            "filename": original_filename,
            "request_id": request_id,
            "processed_at": datetime.now().isoformat(),
            "processor": "ai"
        })
        
        return result
    except Exception as e:
        logger.error(f"AI processing failed: {e}")
        # Fallback to mock
        return get_mock_result(request_id, original_filename)

def get_mock_result(request_id: str, filename: str) -> Dict:
    """Generate mock result for testing"""
    return {
        "player_id": "1234567890",
        "profile_date": datetime.now().strftime("%d/%m/%Y"),
        "email_date": datetime.now().strftime("%B %d, %Y"),
        "email_lines": [
            "A $10,000 Gold Target Is Now Being Discussed",
            "Gold continues to hit new record high...",
            "Investment banks just raised their targets"
        ],
        "ad_lines": [
            "Elite Trade Club - Start your day with the trends",
            "Pre-market Report: RECORD CHIPS, SMARTER FLEETS"
        ],
        "all_text": [
            "Player ID: 1234567890",
            "Profile Date: 09/03/2026",
            "Email: March 9, 2026",
            "Subject: Gold Target Update"
        ],
        "filename": filename,
        "request_id": request_id,
        "processed_at": datetime.now().isoformat(),
        "processor": "mock"
    }

async def send_telegram_notification(chat_id: str, result: dict):
    """Send verification result to Telegram"""
    try:
        # Format message
        message = f"""
✅ *Verification Complete!*

👤 *Player ID:* `{result.get('player_id', 'Not found')}`
📅 *Profile Date:* {result.get('profile_date', 'Not found')}
📧 *Email Date:* {result.get('email_date', 'Not found')}

📨 *Email Preview:*
{chr(10).join(result.get('email_lines', ['No content'])[:3])}

📢 *Ad Content:*
{chr(10).join(result.get('ad_lines', ['No content'])[:2])}

🆔 *Request ID:* `{result.get('request_id', 'N/A')}`
⏱️ *Processed:* {result.get('processed_at', '')[:19]}
        """
        
        await send_verification_result(chat_id, message)
        logger.info(f"✅ Telegram notification sent to {chat_id}")
        
    except Exception as e:
        logger.error(f"❌ Telegram notification failed: {e}")

async def cleanup_file(file_path: str):
    """Clean up temporary file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"🧹 Cleaned up: {file_path}")
    except Exception as e:
        logger.warning(f"Cleanup failed for {file_path}: {e}")

# ============================================
# DEBUG ENDPOINTS
# ============================================

@app.get("/debug")
async def debug_info():
    """Debug endpoint - shows system info"""
    return {
        "cwd": str(Path.cwd()),
        "base_dir": str(BASE_DIR),
        "upload_dir": {
            "path": str(UPLOAD_DIR),
            "exists": UPLOAD_DIR.exists(),
            "writable": os.access(UPLOAD_DIR, os.W_OK) if UPLOAD_DIR.exists() else False,
            "files": len(list(UPLOAD_DIR.glob("*"))) if UPLOAD_DIR.exists() else 0
        },
        "files_in_root": [str(f) for f in Path.cwd().iterdir() if f.is_file()][:10],
        "env_vars": {
            k: v for k, v in os.environ.items() 
            if not any(secret in k.lower() 
            for secret in ['token', 'key', 'pass', 'cred', 'secret'])
        },
        "features": {
            "bot_available": BOT_AVAILABLE,
            "ai_available": AI_AVAILABLE,
            "video_processor": video_processor is not None
        },
        "bot_status": {
            "token_set": bool(BOT_TOKEN),
            "admin_chat_set": bool(os.getenv("ADMIN_CHAT_ID")),
            "firebase_url_set": bool(os.getenv("FIREBASE_DATABASE_URL"))
        } if BOT_AVAILABLE else None,
        "python_version": os.sys.version
    }

@app.post("/echo")
async def echo_file(file: UploadFile = File(...)):
    """Echo file info for testing"""
    content = await file.read()
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(content),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/test-webhook")
async def test_webhook():
    """Test if webhook is accessible"""
    return {
        "message": "Webhook endpoint is accessible",
        "method": "GET",
        "note": "This endpoint is for GET requests. POST requests go to /webhook/telegram"
    }

# ============================================
# FIREBASE TEST ENDPOINT
# ============================================

@app.get("/test-firebase")
async def tes

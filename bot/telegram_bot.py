import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

load_dotenv()

# Import handlers
from bot.handlers import start, verify, admin

# Initialize bot
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Register handlers
dp.include_router(start.router)
dp.include_router(verify.router)
dp.include_router(admin.router)

async def main():
    logging.info("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
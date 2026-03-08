from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "🎮 <b>ApnaJeet AI Video Verifier</b>\n\n"
        "Commands:\n"
        "/verify - Start verification\n"
        "/status - Check system status\n"
        "/help - Get help"
    )
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from Logs.Loging_main import setup_loging, Logged

# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
BOT_TOKEN = ""

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Укажите Telegram ID, которому нужно отправить сообщение
TARGET_USER_ID = 00000000000000000000

# Обработчик команды /start
@dp.message(CommandStart())
async def handle_start(message: types.Message):
    """
    Отправляет приветственное сообщение конкретному пользователю.
    """
    # Сообщение, которое будет отправлено
    greeting_message = "Привет!"
    
    # Отправляем сообщение конкретному пользователю по его ID
    try:
        await bot.send_message(TARGET_USER_ID, greeting_message)
        # Также можно ответить пользователю, который написал /start, 
        # чтобы дать ему обратную связь
        await message.answer("Сообщение отправлено!")
    except Exception as e:
        Logged()
        raise


async def main():
    """
    Запускает бота и начинает обработку сообщений.
    """
    setup_loging(dp)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
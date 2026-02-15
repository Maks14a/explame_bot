import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import boto3
from botocore.exceptions import ClientError

# Загружаем переменные окружения из .env
load_dotenv()

# Настройки из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
YANDEX_ACCESS_KEY = os.getenv("YANDEX_ACCESS_KEY")
YANDEX_SECRET_KEY = os.getenv("YANDEX_SECRET_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")
REGION = "ru-central1"  # регион твоего бакета (можно посмотреть в консоли)
ENDPOINT_URL = "https://storage.yandexcloud.net"  # стандартный эндпоинт

# Настраиваем логирование (чтобы видеть ошибки)
logging.basicConfig(level=logging.INFO)

# Инициализируем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Создаём клиента для S3 (Яндекс.Облако)
session = boto3.session.Session()
s3_client = session.client(
    service_name="s3",
    endpoint_url=ENDPOINT_URL,
    aws_access_key_id=YANDEX_ACCESS_KEY,
    aws_secret_access_key=YANDEX_SECRET_KEY,
    region_name=REGION,
)


async def upload_to_yandex(file_content: bytes, file_name: str) -> str | None:
    try:
        # Сначала загружаем файл (без указания ACL)
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=file_name,
            Body=file_content,
            ContentType="image/jpeg"
        )
        # Теперь делаем этот файл публичным
        s3_client.put_object_acl(
            Bucket=BUCKET_NAME,
            Key=file_name,
            ACL='public-read'
        )
        url = f"https://storage.yandexcloud.net/{BUCKET_NAME}/{file_name}"
        return url
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        logging.error(f"Ошибка при загрузке в Яндекс.Облако: {e}")
        return None

# Обработчик команды /start
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.reply(
        "Привет! Я бот для загрузки картинок в Яндекс.Облако.\n"
        "Просто отправь мне фото, и я верну тебе публичную ссылку."
    )


# Обработчик фото (документов) – реагирует на любые изображения
@dp.message(lambda message: message.photo or message.document)
async def handle_image(message: types.Message):
    # Определяем, что прислали: фото или документ
    if message.photo:
        # Берём фото самого большого размера (последний элемент в списке)
        file_id = message.photo[-1].file_id
    elif message.document and message.document.mime_type.startswith("image/"):
        file_id = message.document.file_id
    else:
        await message.reply("Пожалуйста, отправь изображение.")
        return

    # Скачиваем файл с серверов Telegram
    file = await bot.get_file(file_id)
    file_path = file.file_path
    # Генерируем имя для сохранения в бакете (например, используем file_id + расширение)
    # Можно добавить уникальность, но для теста оставим так
    if message.photo:
        file_name = f"{file_id}.jpg"
    else:
        # Для документа пробуем взять оригинальное имя, но если нет – используем file_id
        original_name = message.document.file_name
        if original_name:
            file_name = original_name
        else:
            # определяем расширение из mime_type
            ext = message.document.mime_type.split("/")[-1]
            file_name = f"{file_id}.{ext}"

    # Скачиваем содержимое
    file_content = await bot.download_file(file_path)
    file_bytes = file_content.read()

    # Отправляем уведомление, что началась загрузка
    status_msg = await message.reply("⏳ Загружаю картинку в Яндекс.Облако...")

    # Загружаем в бакет
    url = await upload_to_yandex(file_bytes, file_name)

    if url:
        # Удаляем сообщение о загрузке и отправляем результат
        await status_msg.delete()
        await message.reply(
            f"✅ Готово!\n"
            f"Прямая ссылка:\n{url}\n\n"
            f"Теперь её можно вставить на сайт."
        )
    else:
        await status_msg.edit_text("❌ Ошибка при загрузке. Попробуй ещё раз.")


# Запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
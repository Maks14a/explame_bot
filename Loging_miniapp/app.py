from fastapi import (
    FastAPI, HTTPException, Depends, Header
)
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from pydantic import BaseModel
from typing import Optional

# Импортируем секретный ключ и список ID администраторов из файла конфигурации
from config import Loging_Secret, ADMIN_IDS, LOG_BOT_TOKEN

# ─────────────────── КОНФИГУРАЦИЯ БОТА ────────────────────
# URL для отправки документов в Telegram
TELEGRAM_SEND_DOCUMENT_URL = f"https://api.telegram.org/bot{LOG_BOT_TOKEN}/sendDocument"

# ─────────────────── FastAPI & CORS ────────────────────
app = FastAPI(
    title="Log Backend API",
    docs_url="/docs", redoc_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Pydantic модель для валидации входящих данных
class LogMessage(BaseModel):
    message: str
    bot_username: Optional[str] = None # Новое поле для имени бота

# ─────────────────── Проверка подлинности ────────────────────
def check_auth(authorization: str = Header(...)):
    """
    Зависимость, которая проверяет заголовок "Authorization"
    и сравнивает его с секретным токеном.
    """
    # Заголовок должен быть в формате "Bearer <токен>"
    if authorization != f"Bearer {Loging_Secret}":
        raise HTTPException(status_code=403, detail="Forbidden: Invalid token")
    # Возвращаем True, если авторизация успешна
    return True

# ─────────────────── Эндпоинты API ────────────────────
@app.post("/log", dependencies=[Depends(check_auth)])
def send_log(log_data: LogMessage):
    """
    Принимает log-сообщение и отправляет его в Telegram всем администраторам.
    Отправляется как файл report.txt с подписью, содержащей информацию об ошибке.
    Требуется авторизация.
    """
    # Формируем содержимое файла
    file_content = f"=== ERROR REPORT ===\n\n{log_data.message}"
    
    # Формируем подпись для файла (caption)
    caption_text = ""
    if log_data.bot_username:
        caption_text = f"🚨 Обнаружена ошибка в Mini_APP:\nBot: @{log_data.bot_username}"

    # Отправляем файл каждому администратору
    for admin_id in ADMIN_IDS:
        try:
            files = {
                'document': ('report.txt', file_content.encode('utf-8'), 'text/plain')
            }
            document_data = {
                'chat_id': admin_id,
                'caption': caption_text # Добавляем подпись к файлу
            }
            document_response = requests.post(TELEGRAM_SEND_DOCUMENT_URL, data=document_data, files=files)
            document_response.raise_for_status()

        except requests.exceptions.RequestException as e:
            # Если отправка одному из админов не удалась, продолжаем,
            # но выводим ошибку в консоль
            print(f"Ошибка при отправке в Telegram для chat_id {admin_id}: {e}")
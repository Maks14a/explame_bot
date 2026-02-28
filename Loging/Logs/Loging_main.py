# Logs/Loging_main.py
# Использование:
#   from Logs.Loging_main import setup_loging, Logged
#   ...
#   setup_loging(dp)
#   ...
#   ...В хендлере при собственном try/except:
#   ...
#       except Exception:
#           await message.answer("Произошла ошибка...")
#           Logged()  # <- сказал глобальному логеру "не дублируй уведомление"
#           raise                  # <- проброс исключения наверх: TXT уйдёт админам
#   ...
#   ВАЖНО! Так же все будет работать без try/except, достаточно их просто удалить в своем скрипте!

import logging
import traceback
from typing import Optional
from contextvars import ContextVar

from aiogram import types, Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.types import BufferedInputFile

from .Loging_config import (
    ADMIN_IDS,
    LOG_BOT_TOKEN,
    NOTIFY_USER_ON_ERROR,
    ERROR_REPORT_FILENAME,
)

# --------- Флажок "пользователь уже уведомлён этим хендлером" (на один апдейт) ---------
_USER_NOTIFIED: ContextVar[bool] = ContextVar("_USER_NOTIFIED", default=False)

def Logged():
    """Позначить, что текущий хендлер уже уведомил пользователя."""
    _USER_NOTIFIED.set(True)

def _was_user_notified() -> bool:
    return _USER_NOTIFIED.get()

# --------- Внутренние сущности ---------
_LOG_BOT: Optional[Bot] = None
_BOT_USERNAME_CACHE: Optional[str] = None

async def _get_bot_username(bot: Bot) -> str:
    global _BOT_USERNAME_CACHE
    if _BOT_USERNAME_CACHE:
        return _BOT_USERNAME_CACHE
    try:
        me = await bot.get_me()
        _BOT_USERNAME_CACHE = me.username or "unknown_bot"
    except Exception as e:
        logging.error(f"[loging] Не удалось получить @username бота: {e}")
        _BOT_USERNAME_CACHE = "unknown_bot"
    return _BOT_USERNAME_CACHE

def _build_full_error_text(exc: Exception, upd: types.Update) -> str:
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    upd_repr = repr(upd)
    return (
        "=== ERROR REPORT ===\n"
        f"Type: {type(exc).__name__}\n"
        f"Message: {str(exc)}\n"
        f"Update (repr): {upd_repr}\n\n"
        f"Traceback:\n{tb}"
    )

async def _notify_user_about_error(bot: Bot, upd: types.Update):
    if not NOTIFY_USER_ON_ERROR or _was_user_notified():
        return
    try:
        chat_id = None
        if getattr(upd, "message", None):
            chat_id = upd.message.chat.id
        elif getattr(upd, "callback_query", None) and upd.callback_query.message:
            chat_id = upd.callback_query.message.chat.id
        if chat_id:
            await bot.send_message(chat_id, "❌Произошла ошибка. Администраторам отправлено уведомление.")
    except TelegramAPIError as e:
        logging.error(f"[loging] Не удалось уведомить пользователя: {e}")

async def _send_document(bot: Bot, chat_id: int, caption: str, text_for_file: str):
    try:
        file = BufferedInputFile(text_for_file.encode("utf-8"), filename=ERROR_REPORT_FILENAME)
        await bot.send_document(chat_id=chat_id, document=file, caption=caption)
    except TelegramRetryAfter as e:
        logging.error(f"[loging] Рейтлимит при отправке в {chat_id}: подождать {e.retry_after} сек")
    except TelegramAPIError as e:
        logging.error(f"[loging] Не удалось отправить отчёт в {chat_id}: {e}")

async def _report_to_admins(origin_username: str, full_text: str, main_bot: Bot):
    if not ADMIN_IDS:
        logging.warning("[loging] ADMIN_IDS пуст — отчёт некому отправлять.")
        return

    caption = f"🚨 Ошибка в работе бота.\nБот: @{origin_username}"

    # Отправка только через лог-бот
    global _LOG_BOT
    if _LOG_BOT:
        for admin_id in ADMIN_IDS:
            await _send_document(_LOG_BOT, admin_id, caption, full_text)
    else:
        # Отправляем через основной бот, если лог-бот не инициализирован
        for admin_id in ADMIN_IDS:
            await _send_document(main_bot, admin_id, caption, full_text)

def setup_loging(dp: Dispatcher):
    """
    Регистрирует глобальный обработчик ошибок.
    Настройки берутся из Logs/Loging_config.py.
    """
    global _LOG_BOT
    if LOG_BOT_TOKEN:
        try:
            _LOG_BOT = Bot(token=LOG_BOT_TOKEN)
            logging.info("Лог-бот успешно инициализирован.")
        except Exception as e:
            logging.error(f"Не удалось инициализировать LOG_BOT: {e}. Будет использован основной бот.")
            _LOG_BOT = None

    async def _errors_handler(event: types.ErrorEvent, bot: Bot):
        # Новый апдейт — сброс флажка (на всякий случай)
        _USER_NOTIFIED.set(False)

        # 1) Коротко уведомим пользователя (если хендлер не уведомил сам)
        await _notify_user_about_error(bot, event.update)

        # 2) Полный txt-отчёт админам
        full_text = _build_full_error_text(event.exception, event.update)
        username = await _get_bot_username(bot)
        await _report_to_admins(username, full_text, bot)

        return True  # исключение обработано

    dp.errors.register(_errors_handler)

__all__ = ["setup_loging", "Logged"]
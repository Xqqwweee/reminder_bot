import logging
import asyncio
import sqlite3
import os

from aiogram import Dispatcher, Bot, types, Router
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta


TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
scheduler = AsyncIOScheduler()

conn = sqlite3.connect("reminder.db")
cursor = conn.cursor()
cursor.execute("""
               CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    text TEXT,
                    time TEXT
               )
"""
)
conn.commit()

@router.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Привет! Напиши задачу и время, например: \nНапомни 'Купить молоко' в 18:30")
@router.message()
async def add_reminder(message: types.Message):
    try:
        text = message.text
        if "в" not in text:
            await message.answer(f"Неверный формат. Используй: \nНапомни 'Купить молоко' в 18:30")
            return

        task_text, time_text = text.split(" в ", maxsplit=1)
        time_text = time_text.strip()
        task_text = task_text.replace("Напомни" or "напомни" or "НАПОМНИ", "").strip()

        try:
            reminder_time = datetime.strptime(time_text, "%H:%M").time()
        except ValueError:
            await message.answer("Ошибка в формате времени. Используй HH:MM (например, 18:30).")
            return

        now = datetime.now()
        reminder_datetime = datetime.combine(now, reminder_time)
        if reminder_datetime < now:
            reminder_datetime += timedelta(days=1)

        logging.info(f"Напоминание установлено на: {reminder_datetime}")

        cursor.execute("INSERT INTO reminders (user_id, text, time) VALUES (?, ?, ?)",
                       (message.from_user.id, task_text, reminder_datetime.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

        scheduler.add_job(send_reminder, "date", run_date=reminder_datetime, args=[message.from_user.id, task_text])

        await message.answer(f"✅ Напоминание добавлено: '{task_text}' в {time_text}")
    except Exception as e:
        logging.exception("Ошибка при добавлении напоминания")
        await message.answer("Произошла ошибка. Проверьте формат ввода и попробуйте снова.")

async def send_reminder(user_id, text):
    try:
        await bot.send_message(user_id, f"⏰ Напоминание: {text}")
    except Exception as e:
        logging.exception("Ошибка при отправке напоминания")

async def main():
    dp.include_router(router)
    scheduler.start()
    logging.info("Бот запущен и планировщик работает")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())


import asyncio
import sqlite3
from aiogram import Bot

OLD_BOT_TOKEN = "YOUR_OLD_TOKEN_HERE"

async def download_all_photos():
    bot = Bot(token=OLD_BOT_TOKEN)
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, photo_id FROM graffiti WHERE photo_id IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()

    import os
    os.makedirs("saved_photos", exist_ok=True)

    for g_id, photo_id in rows:
        try:
            file = await bot.get_file(photo_id)
            await bot.download_file(file.file_path, f"saved_photos/{g_id}.jpg")
            print(f"Скачано фото {g_id}")
        except Exception as e:
            print(f"Ошибка {g_id}: {e}")

    await bot.session.close()
    print("Готово!")

asyncio.run(download_all_photos())
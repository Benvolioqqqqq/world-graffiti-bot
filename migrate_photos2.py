import asyncio
import sqlite3
from aiogram import Bot
from aiogram.types import FSInputFile

NEW_BOT_TOKEN = "8715244020:AAHdbZgTBoMwW5rydf20pmhwRviOdDukjjY"
ADMIN_ID = 516580829

async def migrate():
    bot = Bot(token=NEW_BOT_TOKEN)
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM graffiti WHERE photo_id IS NOT NULL")
    rows = cursor.fetchall()

    for (g_id,) in rows:
        path = f"photos/{g_id}.jpg"
        try:
            photo = FSInputFile(path)
            msg = await bot.send_photo(chat_id=ADMIN_ID, photo=photo)
            new_file_id = msg.photo[-1].file_id
            cursor.execute("UPDATE graffiti SET photo_id = ? WHERE id = ?", (new_file_id, g_id))
            conn.commit()
            await bot.delete_message(chat_id=ADMIN_ID, message_id=msg.message_id)
            print(f"OK {g_id}")
        except Exception as e:
            print(f"Error {g_id}: {e}")

    conn.close()
    await bot.session.close()
    print("Done!")

asyncio.run(migrate())
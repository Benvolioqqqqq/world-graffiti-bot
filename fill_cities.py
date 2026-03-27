import sqlite3
import reverse_geocoder as rg

conn = sqlite3.connect("graffiti.db")
cursor = conn.cursor()
cursor.execute("SELECT id, latitude, longitude FROM graffiti WHERE city IS NULL")
rows = cursor.fetchall()

for g_id, lat, lon in rows:
    try:
        result = rg.search((lat, lon))
        city = f"{result[0]['name']}, {result[0]['cc']}"
        cursor.execute("UPDATE graffiti SET city = ? WHERE id = ?", (city, g_id))
        print(f"ID {g_id}: {city}")
    except Exception as e:
        print(f"Error {g_id}: {e}")

conn.commit()
conn.close()
print("Done!")
import sqlite3

def init_db():
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS graffiti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            photo_id TEXT,
            author TEXT DEFAULT 'Неизвестен',
            date TEXT DEFAULT 'Неизвестна',
            description TEXT DEFAULT '',
            added_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """)
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                user_id INTEGER,
                graffiti_id INTEGER,
                reaction TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, graffiti_id)
            )
        """)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
    except:
        pass
    conn.commit()
    conn.close()

    try:
        cursor.execute("ALTER TABLE graffiti ADD COLUMN city TEXT")
    except:
        pass

def add_graffiti(latitude, longitude, photo_id, author, date, description, added_by):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO graffiti (latitude, longitude, photo_id, author, date, description, added_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (latitude, longitude, photo_id, author, date, description, added_by)
    )
    last_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return last_id

def get_all_graffiti():
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM graffiti WHERE status = 'approved'")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_pending_graffiti():
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM graffiti WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_status(graffiti_id, status):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE graffiti SET status = ? WHERE id = ?", (status, graffiti_id))
    conn.commit()
    conn.close()

def delete_graffiti(graffiti_id):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM graffiti WHERE id = ?", (graffiti_id,))
    conn.commit()
    conn.close()

def search_graffiti(query):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM graffiti WHERE status = 'approved' AND (author LIKE ? OR description LIKE ?)",
        (f"%{query}%", f"%{query}%")
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_stats():
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM graffiti WHERE status = 'approved'")
    approved = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM graffiti WHERE status = 'pending'")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM graffiti")
    total = cursor.fetchone()[0]
    cursor.execute("""
        SELECT added_by, COUNT(*) as cnt 
        FROM graffiti WHERE status = 'approved' 
        GROUP BY added_by ORDER BY cnt DESC LIMIT 10
    """)
    top_users = cursor.fetchall()
    conn.close()
    return {"approved": approved, "pending": pending, "total": total, "top_users": top_users}

def update_added_by_username(graffiti_id, username):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE graffiti SET added_by = ? WHERE id = ?", (username, graffiti_id))
    conn.commit()
    conn.close()

def save_user(user_id, username, full_name):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
        (user_id, username, full_name)
    )
    conn.commit()
    conn.close()

def get_users_count():
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count



def toggle_reaction(user_id, graffiti_id, reaction):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT reaction FROM likes WHERE user_id = ? AND graffiti_id = ?", (user_id, graffiti_id))
    row = cursor.fetchone()
    if row and row[0] == reaction:
        cursor.execute("DELETE FROM likes WHERE user_id = ? AND graffiti_id = ?", (user_id, graffiti_id))
        result = None
    else:
        cursor.execute("INSERT OR REPLACE INTO likes (user_id, graffiti_id, reaction) VALUES (?, ?, ?)", (user_id, graffiti_id, reaction))
        result = reaction
    conn.commit()
    conn.close()
    return result

def get_reactions_count(graffiti_id):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT reaction, COUNT(*) FROM likes 
        WHERE graffiti_id = ? GROUP BY reaction
    """, (graffiti_id,))
    rows = cursor.fetchall()
    conn.close()
    counts = {"fire": 0, "like": 0, "puke": 0}
    for reaction, count in rows:
        if reaction in counts:
            counts[reaction] = count
    return counts

def get_user_reaction(user_id, graffiti_id):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT reaction FROM likes WHERE user_id = ? AND graffiti_id = ?", (user_id, graffiti_id))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_top_liked(limit=5):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT g.id, g.author, g.photo_id, COUNT(l.user_id) as likes
        FROM graffiti g
        JOIN likes l ON g.id = l.graffiti_id
        WHERE g.status = 'approved'
        GROUP BY g.id
        ORDER BY likes DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_all_reactions():
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT graffiti_id, reaction, COUNT(*) as cnt
        FROM likes GROUP BY graffiti_id, reaction
    """)
    rows = cursor.fetchall()
    conn.close()
    result = {}
    for g_id, reaction, count in rows:
        if g_id not in result:
            result[g_id] = {"fire": 0, "like": 0, "puke": 0}
        if reaction in result[g_id]:
            result[g_id][reaction] = count
    return result

def set_display_name(user_id, name):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (name, user_id))
    conn.commit()
    conn.close()

def get_display_name(user_id):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT display_name FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def get_all_users():
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_display_name_by_username(username):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT display_name FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None


def update_city(graffiti_id, city):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE graffiti SET city = ? WHERE id = ?", (city, graffiti_id))
    conn.commit()
    conn.close()
import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "movies.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS genres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            poster_url TEXT,
            link TEXT NOT NULL,
            genre_id INTEGER,
            year INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (genre_id) REFERENCES genres(id)
        )
    """)

    # Default genres
    default_genres = ["Komediya", "Drama", "Action", "Triller", "Animatsiya", "Melodrama", "Qo'rqinchli", "Fantastika"]
    for g in default_genres:
        c.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (g,))

    conn.commit()
    conn.close()


# ── ADMIN ──────────────────────────────────────────────
def is_admin(user_id: int) -> bool:
    # Check env variable for super admin
    super_admin = os.getenv("SUPER_ADMIN_ID")
    if super_admin and str(user_id) == str(super_admin):
        return True
    conn = get_conn()
    row = conn.execute("SELECT id FROM admins WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row is not None


def add_admin(user_id: int, username: str = None) -> bool:
    try:
        conn = get_conn()
        conn.execute("INSERT OR IGNORE INTO admins (user_id, username) VALUES (?,?)", (user_id, username))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def remove_admin(user_id: int) -> bool:
    conn = get_conn()
    conn.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    return True


def get_all_admins():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM admins").fetchall()
    conn.close()
    return rows


# ── GENRE ──────────────────────────────────────────────
def get_genres():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM genres ORDER BY name").fetchall()
    conn.close()
    return rows


def add_genre(name: str) -> int:
    conn = get_conn()
    cur = conn.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (name,))
    conn.commit()
    genre_id = cur.lastrowid
    conn.close()
    return genre_id


def delete_genre(genre_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM genres WHERE id=?", (genre_id,))
    conn.commit()
    conn.close()


# ── MOVIE ──────────────────────────────────────────────
def add_movie(title, link, genre_id=None, description=None, poster_url=None, year=None) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO movies (title, link, genre_id, description, poster_url, year) VALUES (?,?,?,?,?,?)",
        (title, link, genre_id, description, poster_url, year)
    )
    conn.commit()
    movie_id = cur.lastrowid
    conn.close()
    return movie_id


def get_movies_by_genre(genre_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT m.*, g.name as genre_name FROM movies m LEFT JOIN genres g ON m.genre_id=g.id WHERE m.genre_id=? ORDER BY m.title",
        (genre_id,)
    ).fetchall()
    conn.close()
    return rows


def get_movie(movie_id: int):
    conn = get_conn()
    row = conn.execute(
        "SELECT m.*, g.name as genre_name FROM movies m LEFT JOIN genres g ON m.genre_id=g.id WHERE m.id=?",
        (movie_id,)
    ).fetchone()
    conn.close()
    return row


def search_movies(query: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT m.*, g.name as genre_name FROM movies m LEFT JOIN genres g ON m.genre_id=g.id WHERE m.title LIKE ? ORDER BY m.title LIMIT 20",
        (f"%{query}%",)
    ).fetchall()
    conn.close()
    return rows


def delete_movie(movie_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM movies WHERE id=?", (movie_id,))
    conn.commit()
    conn.close()


def update_movie(movie_id: int, **kwargs):
    allowed = {"title", "link", "genre_id", "description", "poster_url", "year"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [movie_id]
    conn = get_conn()
    conn.execute(f"UPDATE movies SET {set_clause} WHERE id=?", values)
    conn.commit()
    conn.close()


def get_all_movies():
    conn = get_conn()
    rows = conn.execute(
        "SELECT m.*, g.name as genre_name FROM movies m LEFT JOIN genres g ON m.genre_id=g.id ORDER BY m.title"
    ).fetchall()
    conn.close()
    return rows


def get_movies_count() -> int:
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    conn.close()
    return count

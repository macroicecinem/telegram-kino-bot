import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id SERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE NOT NULL,
            username TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS genres (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            poster_url TEXT,
            link TEXT NOT NULL,
            genre_id INTEGER REFERENCES genres(id) ON DELETE SET NULL,
            year INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE NOT NULL,
            phone TEXT,
            username TEXT,
            full_name TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    default_genres = ["Fantastika", "Drama", "Komediya", "Qo'rqinchli"]
    for g in default_genres:
        c.execute("INSERT INTO genres (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (g,))

    conn.commit()
    conn.close()


# ── USER ───────────────────────────────────────────────
def get_user(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
    row = c.fetchone()
    conn.close()
    return row


def add_user(user_id: int, phone: str, username: str = None, full_name: str = None):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (user_id, phone, username, full_name) VALUES (%s,%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET phone=%s, username=%s, full_name=%s",
        (user_id, phone, username, full_name, phone, username, full_name)
    )
    conn.commit()
    conn.close()


def get_all_users():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    rows = c.fetchall()
    conn.close()
    return rows


def get_users_count() -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM users")
    row = c.fetchone()
    conn.close()
    return row["cnt"]


# ── ADMIN ──────────────────────────────────────────────
def is_admin(user_id: int) -> bool:
    super_admin = os.getenv("SUPER_ADMIN_ID")
    if super_admin and str(user_id) == str(super_admin):
        return True
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM admins WHERE user_id=%s", (user_id,))
    row = c.fetchone()
    conn.close()
    return row is not None


def add_admin(user_id: int, username: str = None) -> bool:
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO admins (user_id, username) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING", (user_id, username))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def remove_admin(user_id: int) -> bool:
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id=%s", (user_id,))
    conn.commit()
    conn.close()
    return True


def get_all_admins():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM admins")
    rows = c.fetchall()
    conn.close()
    return rows


# ── GENRE ──────────────────────────────────────────────
def get_genres():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM genres ORDER BY name")
    rows = c.fetchall()
    conn.close()
    return rows


def add_genre(name: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO genres (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id", (name,))
    row = c.fetchone()
    conn.commit()
    conn.close()
    return row["id"] if row else None


def delete_genre(genre_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM genres WHERE id=%s", (genre_id,))
    conn.commit()
    conn.close()


# ── MOVIE ──────────────────────────────────────────────
def add_movie(title, link, genre_id=None, description=None, poster_url=None, year=None) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO movies (title, link, genre_id, description, poster_url, year) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
        (title, link, genre_id, description, poster_url, year)
    )
    row = c.fetchone()
    conn.commit()
    conn.close()
    return row["id"]


def get_movies_by_genre(genre_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT m.*, g.name as genre_name FROM movies m LEFT JOIN genres g ON m.genre_id=g.id WHERE m.genre_id=%s ORDER BY m.title",
        (genre_id,)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def get_movie(movie_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT m.*, g.name as genre_name FROM movies m LEFT JOIN genres g ON m.genre_id=g.id WHERE m.id=%s",
        (movie_id,)
    )
    row = c.fetchone()
    conn.close()
    return row


def search_movies(query: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT m.*, g.name as genre_name FROM movies m LEFT JOIN genres g ON m.genre_id=g.id WHERE m.title ILIKE %s ORDER BY m.title LIMIT 20",
        (f"%{query}%",)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def delete_movie(movie_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM movies WHERE id=%s", (movie_id,))
    conn.commit()
    conn.close()


def get_all_movies():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT m.*, g.name as genre_name FROM movies m LEFT JOIN genres g ON m.genre_id=g.id ORDER BY m.title")
    rows = c.fetchall()
    conn.close()
    return rows


def get_movies_count() -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM movies")
    row = c.fetchone()
    conn.close()
    return row["cnt"]

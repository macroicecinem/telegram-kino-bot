"""
Bu scriptni bir marta ishlatib o'chiring.
Barcha codsiz kinolarga avtomatik kod beradi.

Railway -> telegram-kino-bot -> Settings -> Start Command:
python assign_codes.py && python bot.py

Yoki oddiyroq: Railway Console da ishlatish
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
c = conn.cursor()

# Codsiz kinolarni olish
c.execute("SELECT id, title FROM movies WHERE code IS NULL OR code = '' ORDER BY id")
movies = c.fetchall()

print(f"Codsiz kinolar soni: {len(movies)}")

# Eng katta mavjud kod
c.execute("SELECT COALESCE(MAX(CAST(code AS INTEGER)), 100) as max_code FROM movies WHERE code ~ '^[0-9]+$'")
row = c.fetchone()
next_code = (row["max_code"] or 100) + 1

for movie in movies:
    c.execute("UPDATE movies SET code=%s WHERE id=%s", (str(next_code), movie["id"]))
    print(f"  {movie['title']} -> kod: {next_code}")
    next_code += 1

conn.commit()
conn.close()
print("✅ Hammasi tayyor!")

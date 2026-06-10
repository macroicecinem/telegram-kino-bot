"""
Bu scriptni bir marta ishlatib, barcha kinolardagi linkdan
channel_username va channel_post_id ni avtomatik ajratib oladi.
"""
import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
c = conn.cursor()

c.execute("SELECT id, title, link FROM movies WHERE link IS NOT NULL")
movies = c.fetchall()

updated = 0
skipped = 0

for movie in movies:
    link = movie["link"] or ""
    # https://t.me/username/123 formatini tekshirish
    match = re.match(r"https?://t\.me/([^/c][^/]*)/(\d+)", link)
    if match:
        username = match.group(1)
        post_id = int(match.group(2))
        c.execute(
            "UPDATE movies SET channel_username=%s, channel_post_id=%s WHERE id=%s",
            (username, post_id, movie["id"])
        )
        print(f"✅ {movie['title']} -> @{username}/{post_id}")
        updated += 1
    else:
        print(f"⚠️  {movie['title']} -> link noto'g'ri: {link}")
        skipped += 1

conn.commit()
conn.close()
print(f"\n✅ Yangilandi: {updated} ta")
print(f"⚠️  O'tkazildi: {skipped} ta (link noto'g'ri)")

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
import hashlib

import database as db
import user
import admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    db.init_db()
    logger.info("Database initialized")

    super_admin_id = os.getenv("SUPER_ADMIN_ID")
    if super_admin_id:
        db.add_admin(int(super_admin_id), "super_admin")
        logger.info(f"Super admin {super_admin_id} registered")

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Inline query handler
    @dp.inline_query()
    async def inline_search(query: InlineQuery):
        text = query.query.strip()
        results = []

        if len(text) >= 1:
            movies = db.search_movies(text)
        else:
            movies = db.get_all_movies()

        results_list = [dict(m) for m in movies][:20]

        for movie in results_list:

            # Kartochka matni
            desc_parts = []
            if movie.get("year"):
                desc_parts.append(f"📅 {movie['year']}")
            if movie.get("genre_name"):
                desc_parts.append(f"🎭 {movie['genre_name']}")
            if movie.get("country"):
                desc_parts.append(f"🌍 {movie['country']}")

            description = " | ".join(desc_parts)

            # Xabar matni
            text_msg = f"🎬 <b>{movie['title']}</b>\n"
            text_msg += "—————————————————\n"
            if movie.get("country"):
                text_msg += f"🌍 Davlat: {movie['country']}\n"
            if movie.get("year"):
                text_msg += f"📅 Yil: {movie['year']}\n"
            if movie.get("quality"):
                text_msg += f"🎬 Sifat: {movie['quality']}\n"
            if movie.get("language"):
                text_msg += f"🗣 Til: {movie['language']}\n"
            if movie.get("genre_name"):
                text_msg += f"🎭 Janr: {movie['genre_name']}\n"
            if movie.get("description"):
                text_msg += f"\n📝 {movie['description']}\n"
            if movie.get("link"):
                text_msg += f"\n▶️ <a href=\"{movie['link']}\">Ko'rish</a>"

            result_id = hashlib.md5(str(movie["id"]).encode()).hexdigest()

            result = InlineQueryResultArticle(
                id=result_id,
                title=movie["title"],
                description=description,
                thumbnail_url=movie.get("poster_url") or None,
                input_message_content=InputTextMessageContent(
                    message_text=text_msg,
                    parse_mode="HTML"
                )
            )
            results.append(result)

        await query.answer(results, cache_time=10, is_personal=True)

    # Vaqtinchalik: file_id olish uchun
    @dp.message(F.animation)
    async def get_animation_id(message):
        if str(message.from_user.id) == os.getenv("SUPER_ADMIN_ID", ""):
            await message.answer(f"GIF file_id:\n<code>{message.animation.file_id}</code>")

    @dp.message(F.video)
    async def get_video_id(message):
        if str(message.from_user.id) == os.getenv("SUPER_ADMIN_ID", ""):
            await message.answer(f"Video file_id:\n<code>{message.video.file_id}</code>")

    @dp.message(F.document)
    async def get_doc_id(message):
        if str(message.from_user.id) == os.getenv("SUPER_ADMIN_ID", ""):
            await message.answer(f"Document file_id:\n<code>{message.document.file_id}</code>")

    dp.include_router(admin.router)
    dp.include_router(user.router)

    logger.info("Bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

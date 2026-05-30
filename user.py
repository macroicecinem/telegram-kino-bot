from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db

router = Router()


def genres_keyboard():
    genres = db.get_genres()
    builder = InlineKeyboardBuilder()
    for g in genres:
        builder.button(text=f"🎬 {g['name']}", callback_data=f"genre:{g['id']}")
    builder.button(text="🔍 Qidirish", callback_data="search")
    builder.adjust(2)
    return builder.as_markup()


def movies_keyboard(genre_id: int):
    movies = db.get_movies_by_genre(genre_id)
    builder = InlineKeyboardBuilder()
    for m in movies:
        builder.button(text=f"🎥 {m['title']}", callback_data=f"movie:{m['id']}")
    builder.button(text="⬅️ Orqaga", callback_data="back_genres")
    builder.adjust(1)
    return builder.as_markup()


def movie_keyboard(movie: dict):
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Ko'rish", url=movie["link"])
    builder.button(text="⬅️ Orqaga", callback_data=f"genre:{movie['genre_id']}")
    builder.adjust(1)
    return builder.as_markup()


# ── /start ─────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message):
    count = db.get_movies_count()
    await message.answer(
        f"🎬 *Kino Botga xush kelibsiz!*\n\n"
        f"Bazada hozir *{count} ta* kino mavjud.\n\n"
        f"Janrni tanlang yoki qidirish tugmasini bosing 👇",
        parse_mode="Markdown",
        reply_markup=genres_keyboard()
    )


# ── /kinolar ───────────────────────────────────────────
@router.message(Command("kinolar"))
async def cmd_movies(message: Message):
    await message.answer(
        "🎬 *Janrni tanlang:*",
        parse_mode="Markdown",
        reply_markup=genres_keyboard()
    )


# ── /qidirish ──────────────────────────────────────────
@router.message(Command("qidirish"))
async def cmd_search(message: Message):
    await message.answer("🔍 Kino nomini yozing:")


# ── Janr tanlandi ──────────────────────────────────────
@router.callback_query(F.data.startswith("genre:"))
async def genre_selected(call: CallbackQuery):
    genre_id = int(call.data.split(":")[1])
    movies = db.get_movies_by_genre(genre_id)
    genre = next((g for g in db.get_genres() if g["id"] == genre_id), None)

    if not movies:
        await call.answer("Bu janrda hali kino yo'q 😕", show_alert=True)
        return

    await call.message.edit_text(
        f"🎬 *{genre['name']}* — {len(movies)} ta kino\n\nKinoni tanlang:",
        parse_mode="Markdown",
        reply_markup=movies_keyboard(genre_id)
    )


# ── Kino tanlandi ──────────────────────────────────────
@router.callback_query(F.data.startswith("movie:"))
async def movie_selected(call: CallbackQuery):
    movie_id = int(call.data.split(":")[1])
    movie = db.get_movie(movie_id)

    if not movie:
        await call.answer("Kino topilmadi 😕", show_alert=True)
        return

    text = f"🎬 *{movie['title']}*\n"
    if movie["year"]:
        text += f"📅 Yil: {movie['year']}\n"
    if movie["genre_name"]:
        text += f"🎭 Janr: {movie['genre_name']}\n"
    if movie["description"]:
        text += f"\n📝 {movie['description']}\n"

    text += "\n👇 Ko'rish uchun tugmani bosing:"

    kb = movie_keyboard(dict(movie))

    if movie["poster_url"]:
        try:
            await call.message.answer_photo(
                photo=movie["poster_url"],
                caption=text,
                parse_mode="Markdown",
                reply_markup=kb
            )
            await call.message.delete()
        except Exception:
            await call.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)


# ── Orqaga ─────────────────────────────────────────────
@router.callback_query(F.data == "back_genres")
async def back_to_genres(call: CallbackQuery):
    count = db.get_movies_count()
    await call.message.edit_text(
        f"🎬 *Kino Botga xush kelibsiz!*\n\n"
        f"Bazada hozir *{count} ta* kino mavjud.\n\n"
        f"Janrni tanlang yoki qidirish tugmasini bosing 👇",
        parse_mode="Markdown",
        reply_markup=genres_keyboard()
    )


# ── Qidirish ───────────────────────────────────────────
@router.callback_query(F.data == "search")
async def search_prompt(call: CallbackQuery):
    await call.message.answer("🔍 Kino nomini yozing (masalan: *Avatar*):", parse_mode="Markdown")
    await call.answer()


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message):
    # Check if it looks like a search query
    query = message.text.strip()
    if len(query) < 2:
        return

    results = db.search_movies(query)
    if not results:
        await message.answer(
            f"❌ *\"{query}\"* bo'yicha hech narsa topilmadi.\n\n/kinolar — barcha kinolarni ko'rish",
            parse_mode="Markdown"
        )
        return

    builder = InlineKeyboardBuilder()
    for m in results:
        label = f"🎥 {m['title']}"
        if m["year"]:
            label += f" ({m['year']})"
        builder.button(text=label, callback_data=f"movie:{m['id']}")
    builder.button(text="⬅️ Bosh sahifa", callback_data="back_genres")
    builder.adjust(1)

    await message.answer(
        f"🔍 *\"{query}\"* bo'yicha {len(results)} ta natija:",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )

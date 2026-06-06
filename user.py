from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db

router = Router()

TELEGRAM_CHANNEL = "@macroicecinema"
YOUTUBE_URL = "https://www.youtube.com/@MACROICEcinema"
INSTAGRAM_URL = "https://www.instagram.com/macroice_cinema/"


class Registration(StatesGroup):
    phone = State()


class FilterState(StatesGroup):
    waiting = State()


async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(TELEGRAM_CHANNEL, user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception:
        return False


def subscription_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📺 Telegram kanal", url="https://t.me/macroicecinema")
    builder.button(text="▶️ YouTube kanal", url=YOUTUBE_URL)
    builder.button(text="📸 Instagram", url=INSTAGRAM_URL)
    builder.button(text="✅ Obuna bo'ldim!", callback_data="check_sub")
    builder.adjust(1)
    return builder.as_markup()


def phone_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamimni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return kb


def main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Barcha filmlar", callback_data="all_movies")
    builder.button(text="🔍 Qidirish", switch_inline_query_current_chat="")
    builder.button(text="📂 Filter", callback_data="filter_menu")
    builder.button(text="⭐️ Saqlangan", callback_data="saved_movies")
    builder.adjust(2)
    return builder.as_markup()


def genres_keyboard():
    genres = db.get_genres()
    builder = InlineKeyboardBuilder()
    for g in genres:
        builder.button(text=f"🎬 {g['name']}", callback_data=f"genre:{g['id']}")
    builder.button(text="⬅️ Orqaga", callback_data="back_main")
    builder.adjust(2)
    return builder.as_markup()


def movies_keyboard(movies, back_callback="back_genres_main"):
    builder = InlineKeyboardBuilder()
    for m in movies:
        label = f"🎥 {m['title']}"
        if m.get("year"):
            label += f" ({m['year']})"
        builder.button(text=label, callback_data=f"movie:{m['id']}")
    builder.button(text="⬅️ Orqaga", callback_data=back_callback)
    builder.adjust(1)
    return builder.as_markup()


def movie_keyboard(movie: dict, user_id: int, has_forward: bool = False):
    builder = InlineKeyboardBuilder()
    # Forward bo'lsa Ko'rish tugmasi kerak emas
    if not has_forward and movie.get("link"):
        builder.button(text="▶️ Ko'rish", url=movie["link"])
    saved = db.is_saved(user_id, movie["id"])
    if saved:
        builder.button(text="❌ Saqlangandan o'chir", callback_data=f"unsave:{movie['id']}")
    else:
        builder.button(text="⭐️ Saqlash", callback_data=f"save:{movie['id']}")
    genre_id = movie.get("genre_id")
    if genre_id:
        builder.button(text="⬅️ Orqaga", callback_data=f"back_movie:{movie['id']}:{genre_id}")
    else:
        builder.button(text="⬅️ Orqaga", callback_data=f"back_movie:{movie['id']}:0")
    builder.adjust(1)
    return builder.as_markup()


def movie_card_text(movie):
    text = f"🎬 <b>{movie['title']}</b>\n"
    text += "—————————————————\n"
    if movie.get("country"):
        text += f"🌍 Davlat: {movie['country']}\n"
    if movie.get("year"):
        text += f"📅 Yil: {movie['year']}\n"
    if movie.get("quality"):
        text += f"🎬 Sifat: {movie['quality']}\n"
    if movie.get("language"):
        text += f"🗣 Til: {movie['language']}\n"
    if movie.get("genre_name"):
        text += f"🎭 Janr: {movie['genre_name']}\n"
    if movie.get("code"):
        text += f"🔢 Film kodi: {movie['code']}\n"
    if movie.get("views"):
        text += f"👁 Ko'rishlar: {movie['views']}\n"
    if movie.get("description"):
        text += f"\n📝 {movie['description']}\n"
    text += "\n👇 Ko'rish uchun tugmani bosing:"
    return text


BANNER_GIF = "CgACAgIAAxkBAAIxC2oiuTuJXS1LQbV2EnOXz64qhIzJAAKWoQACWfYZSa2rlxDma_1cOwQ"

async def show_main_menu(message: Message):
    count = db.get_movies_count()
    text = (
        f"🎬 <b>MACROICE Cinema botiga xush kelibsiz!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🍿 Bazada: <b>{count} ta</b> kino\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Quyidagilardan birini tanlang 👇"
    )
    try:
        await message.answer_animation(
            animation=BANNER_GIF,
            caption=text,
            reply_markup=main_keyboard()
        )
    except Exception:
        await message.answer(text, reply_markup=main_keyboard())


# ── /start ─────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user:
        await state.set_state(Registration.phone)
        await message.answer(
            "👋 <b>Assalomu alaykum!</b>\n\n"
            "Botdan foydalanish uchun telefon raqamingizni tasdiqlang 👇",
            reply_markup=phone_keyboard()
        )
        return

    subscribed = await check_subscription(bot, user_id)
    if not subscribed:
        try:
            await message.answer_animation(
                animation=BANNER_GIF,
                caption=(
                    "🎬 <b>MACROICE Cinema</b>\n\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "❌ Botdan foydalanish uchun\n"
                    "<b>MACROICE kanallariga obuna bo'ling!</b>\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    "Obuna bo'lgach <b>✅ Obuna bo'ldim!</b> bosing."
                ),
                reply_markup=subscription_keyboard()
            )
        except Exception:
            await message.answer(
                "❌ <b>MACROICE kanallariga obuna bo'ling:</b>\n\n"
                "Obuna bo'lgach <b>✅ Obuna bo'ldim!</b> tugmasini bosing.",
                reply_markup=subscription_keyboard()
            )
        return

    await show_main_menu(message)


# ── /kinolar ───────────────────────────────────────────
@router.message(Command("kinolar"))
async def cmd_kinolar(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await message.answer("❌ <b>MACROICE kanallariga obuna bo'ling:</b>", reply_markup=subscription_keyboard())
        return
    await show_main_menu(message)


# ── Telefon ────────────────────────────────────────────
@router.message(Registration.phone, F.contact)
async def get_phone(message: Message, state: FSMContext, bot: Bot):
    contact = message.contact
    user_id = message.from_user.id
    db.add_user(user_id, contact.phone_number, message.from_user.username, message.from_user.full_name)
    await state.clear()
    await message.answer("✅ <b>Telefon raqam tasdiqlandi!</b>", reply_markup=ReplyKeyboardRemove())

    subscribed = await check_subscription(bot, user_id)
    if not subscribed:
        try:
            await message.answer_animation(
                animation=BANNER_GIF,
                caption=(
                    "🎬 <b>MACROICE Cinema</b>\n\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "❌ Botdan foydalanish uchun\n"
                    "<b>MACROICE kanallariga obuna bo'ling!</b>\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    "Obuna bo'lgach <b>✅ Obuna bo'ldim!</b> bosing."
                ),
                reply_markup=subscription_keyboard()
            )
        except Exception:
            await message.answer(
                "📢 <b>MACROICE kanallariga obuna bo'ling:</b>\n\n"
                "Obuna bo'lgach <b>✅ Obuna bo'ldim!</b> tugmasini bosing.",
                reply_markup=subscription_keyboard()
            )
        return
    await show_main_menu(message)


@router.message(Registration.phone)
async def wrong_phone(message: Message):
    await message.answer("📱 Iltimos, tugma orqali telefon raqamingizni yuboring:", reply_markup=phone_keyboard())


# ── Obuna ──────────────────────────────────────────────
@router.callback_query(F.data == "check_sub")
async def check_sub_callback(call: CallbackQuery, bot: Bot):
    subscribed = await check_subscription(bot, call.from_user.id)
    if not subscribed:
        await call.answer("❌ Siz hali @macroicecinema kanaliga obuna bo'lmadingiz!", show_alert=True)
        return
    await call.message.delete()
    await show_main_menu(call.message)


# ── Bosh menyu ─────────────────────────────────────────
@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery):
    count = db.get_movies_count()
    text = (
        f"🎬 <b>MACROICE Cinema botiga xush kelibsiz!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🍿 Bazada: <b>{count} ta</b> kino\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Quyidagilardan birini tanlang 👇"
    )
    try:
        await call.message.delete()
        await call.message.answer_animation(
            animation=BANNER_GIF,
            caption=text,
            reply_markup=main_keyboard()
        )
    except Exception:
        try:
            await call.message.edit_text(text, reply_markup=main_keyboard())
        except Exception:
            await call.message.delete()
            await call.message.answer(text, reply_markup=main_keyboard())


# ── Barcha filmlar (janrlar) ───────────────────────────
@router.callback_query(F.data == "all_movies")
async def all_movies(call: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer("❌ Avval kanalga obuna bo'ling!", show_alert=True)
        return
    try:
        await call.message.edit_text("🎬 <b>Janrni tanlang:</b>", reply_markup=genres_keyboard())
    except Exception:
        await call.message.delete()
        await call.message.answer("🎬 <b>Janrni tanlang:</b>", reply_markup=genres_keyboard())


# ── Janr ───────────────────────────────────────────────
@router.callback_query(F.data.startswith("genre:"))
async def genre_selected(call: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer("❌ Avval kanalga obuna bo'ling!", show_alert=True)
        return

    genre_id = int(call.data.split(":")[1])
    movies = db.get_movies_by_genre(genre_id)
    genre = next((g for g in db.get_genres() if g["id"] == genre_id), None)

    if not movies:
        await call.answer("Bu janrda hali kino yo'q 😕", show_alert=True)
        return

    try:
        await call.message.edit_text(
            f"🎬 <b>{genre['name']}</b> — {len(movies)} ta kino\n\nKinoni tanlang:",
            reply_markup=movies_keyboard(movies, back_callback="all_movies")
        )
    except Exception:
        await call.message.delete()
        await call.message.answer(
            f"🎬 <b>{genre['name']}</b> — {len(movies)} ta kino\n\nKinoni tanlang:",
            reply_markup=movies_keyboard(movies, back_callback="all_movies")
        )


# ── Kino ───────────────────────────────────────────────
@router.callback_query(F.data.startswith("movie:"))
async def movie_selected(call: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer("❌ Avval kanalga obuna bo'ling!", show_alert=True)
        return

    movie_id = int(call.data.split(":")[1])
    movie = db.get_movie(movie_id)

    if not movie:
        await call.answer("Kino topilmadi 😕", show_alert=True)
        return

    db.increment_views(movie_id)
    movie = dict(movie)

    # Kanal post ID orqali forward qilish
    if movie.get("channel_post_id") and movie.get("channel_username"):
        try:
            # Info xabarini yuborish
            kb = movie_keyboard(movie, call.from_user.id)
            info_text = movie_card_text(movie)

            try:
                await call.message.edit_text(info_text, reply_markup=kb)
            except Exception:
                await call.message.delete()
                await call.message.answer(info_text, reply_markup=kb)

            # Kanaldan forward qilish
            channel = movie["channel_username"]
            if not channel.startswith("@"):
                channel = "@" + channel
            forwarded = await bot.forward_message(
                chat_id=call.from_user.id,
                from_chat_id=channel,
                message_id=movie["channel_post_id"]
            )

            # Forward xabar ID ni saqlaymiz (orqaga bosganda o'chirish uchun)
            db.save_forward_message(call.from_user.id, movie_id, forwarded.message_id)
            return
        except Exception as e:
            pass

    # Eski usul - link bilan
    text = movie_card_text(movie)
    kb = movie_keyboard(movie, call.from_user.id)

    if movie.get("poster_url"):
        try:
            await call.message.delete()
            await call.message.answer_photo(photo=movie["poster_url"], caption=text, reply_markup=kb)
        except Exception:
            try:
                await call.message.edit_text(text, reply_markup=kb)
            except Exception:
                await call.message.delete()
                await call.message.answer(text, reply_markup=kb)
    else:
        try:
            await call.message.edit_text(text, reply_markup=kb)
        except Exception:
            await call.message.delete()
            await call.message.answer(text, reply_markup=kb)




# ── Orqaga (forward o'chirish) ─────────────────────────
@router.callback_query(F.data.startswith("back_movie:"))
async def back_from_movie(call: CallbackQuery, bot: Bot):
    parts = call.data.split(":")
    movie_id = int(parts[1])
    genre_id = int(parts[2])

    # Forward xabarlarni o'chirish
    forward_ids = db.get_forward_messages(call.from_user.id, movie_id)
    for msg_id in forward_ids:
        try:
            await bot.delete_message(call.from_user.id, msg_id)
        except Exception:
            pass
    db.delete_forward_messages(call.from_user.id, movie_id)

    # Orqaga qaytish
    if genre_id and genre_id != 0:
        movies = db.get_movies_by_genre(genre_id)
        genre = next((g for g in db.get_genres() if g["id"] == genre_id), None)
        try:
            await call.message.edit_text(
                f"🎬 <b>{genre['name']}</b> — {len(movies)} ta kino\n\nKinoni tanlang:",
                reply_markup=movies_keyboard(movies, back_callback="all_movies")
            )
        except Exception:
            await call.message.delete()
            await call.message.answer(
                f"🎬 <b>{genre['name']}</b> — {len(movies)} ta kino\n\nKinoni tanlang:",
                reply_markup=movies_keyboard(movies, back_callback="all_movies")
            )
    else:
        count = db.get_movies_count()
        text = (
            f"🎬 <b>MACROICE Cinema botiga xush kelibsiz!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🍿 Bazada: <b>{count} ta</b> kino\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"Quyidagilardan birini tanlang 👇"
        )
        try:
            await call.message.delete()
            await call.message.answer_animation(
                animation=BANNER_GIF,
                caption=text,
                reply_markup=main_keyboard()
            )
        except Exception:
            await call.message.edit_text(text, reply_markup=main_keyboard())

# ── Saqlash ────────────────────────────────────────────
@router.callback_query(F.data.startswith("save:"))
async def save_movie(call: CallbackQuery):
    movie_id = int(call.data.split(":")[1])
    db.save_movie(call.from_user.id, movie_id)
    await call.answer("⭐️ Film saqlandi!", show_alert=True)

    movie = db.get_movie(movie_id)
    if movie:
        text = movie_card_text(dict(movie))
        kb = movie_keyboard(dict(movie), call.from_user.id)
        try:
            await call.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            try:
                await call.message.edit_text(text, reply_markup=kb)
            except Exception:
                pass


@router.callback_query(F.data.startswith("unsave:"))
async def unsave_movie(call: CallbackQuery):
    movie_id = int(call.data.split(":")[1])
    db.unsave_movie(call.from_user.id, movie_id)
    await call.answer("❌ Saqlangandan o'chirildi!", show_alert=True)

    movie = db.get_movie(movie_id)
    if movie:
        text = movie_card_text(dict(movie))
        kb = movie_keyboard(dict(movie), call.from_user.id)
        try:
            await call.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            try:
                await call.message.edit_text(text, reply_markup=kb)
            except Exception:
                pass


# ── Saqlangan filmlar ──────────────────────────────────
@router.callback_query(F.data == "saved_movies")
async def show_saved(call: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer("❌ Avval kanalga obuna bo'ling!", show_alert=True)
        return

    movies = db.get_saved_movies(call.from_user.id)

    if not movies:
        try:
            await call.message.edit_text(
                "⭐️ <b>Saqlangan filmlar</b>\n\nHozircha saqlanmagan.",
                reply_markup=InlineKeyboardBuilder().button(text="⬅️ Orqaga", callback_data="back_main").as_markup()
            )
        except Exception:
            await call.message.delete()
            await call.message.answer(
                "⭐️ <b>Saqlangan filmlar</b>\n\nHozircha saqlanmagan.",
                reply_markup=InlineKeyboardBuilder().button(text="⬅️ Orqaga", callback_data="back_main").as_markup()
            )
        return

    builder = InlineKeyboardBuilder()
    for m in movies:
        label = f"⭐️ {m['title']}"
        if m.get("year"):
            label += f" ({m['year']})"
        builder.button(text=label, callback_data=f"movie:{m['id']}")
    builder.button(text="⬅️ Orqaga", callback_data="back_main")
    builder.adjust(1)

    try:
        await call.message.edit_text(
            f"⭐️ <b>Saqlangan filmlar</b> ({len(movies)} ta):",
            reply_markup=builder.as_markup()
        )
    except Exception:
        await call.message.delete()
        await call.message.answer(
            f"⭐️ <b>Saqlangan filmlar</b> ({len(movies)} ta):",
            reply_markup=builder.as_markup()
        )


# ── Filter ─────────────────────────────────────────────
@router.callback_query(F.data == "filter_menu")
async def filter_menu(call: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer("❌ Avval kanalga obuna bo'ling!", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="🎭 Janr", callback_data="filter:genre")
    builder.button(text="🌍 Davlat", callback_data="filter:country")
    builder.button(text="📅 Yil", callback_data="filter:year")
    builder.button(text="🎬 Sifat", callback_data="filter:quality")
    builder.button(text="⬅️ Orqaga", callback_data="back_main")
    builder.adjust(2)

    try:
        await call.message.edit_text("📂 <b>Filter</b>\n\nQaysi bo'yicha filtrlaysiz?", reply_markup=builder.as_markup())
    except Exception:
        await call.message.delete()
        await call.message.answer("📂 <b>Filter</b>\n\nQaysi bo'yicha filtrlaysiz?", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("filter:"))
async def filter_selected(call: CallbackQuery):
    filter_type = call.data.split(":")[1]

    builder = InlineKeyboardBuilder()

    if filter_type == "genre":
        items = db.get_genres()
        for item in items:
            builder.button(text=item["name"], callback_data=f"fresult:genre:{item['id']}")
    elif filter_type == "country":
        items = db.get_distinct_countries()
        for item in items:
            builder.button(text=f"🌍 {item}", callback_data=f"fresult:country:{item}")
    elif filter_type == "year":
        items = db.get_distinct_years()
        for item in items:
            builder.button(text=f"📅 {item}", callback_data=f"fresult:year:{item}")
    elif filter_type == "quality":
        items = db.get_distinct_qualities()
        for item in items:
            builder.button(text=f"🎬 {item}", callback_data=f"fresult:quality:{item}")

    builder.button(text="⬅️ Orqaga", callback_data="filter_menu")
    builder.adjust(2)

    titles = {"genre": "Janr", "country": "Davlat", "year": "Yil", "quality": "Sifat"}
    try:
        await call.message.edit_text(
            f"📂 <b>{titles.get(filter_type, 'Filter')}</b> tanlang:",
            reply_markup=builder.as_markup()
        )
    except Exception:
        await call.message.delete()
        await call.message.answer(
            f"📂 <b>{titles.get(filter_type, 'Filter')}</b> tanlang:",
            reply_markup=builder.as_markup()
        )


@router.callback_query(F.data.startswith("fresult:"))
async def filter_result(call: CallbackQuery):
    parts = call.data.split(":", 2)
    filter_type = parts[1]
    value = parts[2]

    if filter_type == "genre":
        movies = db.get_movies_by_genre(int(value))
    elif filter_type == "country":
        movies = db.get_movies_by_filter(country=value)
    elif filter_type == "year":
        movies = db.get_movies_by_filter(year=int(value))
    elif filter_type == "quality":
        movies = db.get_movies_by_filter(quality=value)
    else:
        movies = []

    if not movies:
        await call.answer("Bu filtrda kino topilmadi 😕", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for m in movies:
        label = f"🎥 {m['title']}"
        if m.get("year"):
            label += f" ({m['year']})"
        builder.button(text=label, callback_data=f"movie:{m['id']}")
    builder.button(text="⬅️ Filtrlarga", callback_data="filter_menu")
    builder.adjust(1)

    try:
        await call.message.edit_text(
            f"📂 <b>{len(movies)} ta natija:</b>",
            reply_markup=builder.as_markup()
        )
    except Exception:
        await call.message.delete()
        await call.message.answer(
            f"📂 <b>{len(movies)} ta natija:</b>",
            reply_markup=builder.as_markup()
        )


# ── Qidirish ───────────────────────────────────────────
@router.callback_query(F.data == "search")
async def search_prompt(call: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer("❌ Avval kanalga obuna bo'ling!", show_alert=True)
        return
    try:
        await call.message.edit_text(
            "🔍 <b>Qidiruv</b>\n\nKino nomini yozing:",
            reply_markup=InlineKeyboardBuilder().button(text="⬅️ Orqaga", callback_data="back_main").as_markup()
        )
    except Exception:
        await call.message.delete()
        await call.message.answer("🔍 Kino nomini yozing:")
    await call.answer()


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await message.answer("❌ Botdan foydalanish uchun kanalga obuna bo'ling:", reply_markup=subscription_keyboard())
        return

    query = message.text.strip()
    if len(query) < 1:
        return

    # Avval kod bo'yicha qidiruv
    movie_by_code = db.get_movie_by_code(query)
    if movie_by_code:
        movie = dict(movie_by_code)
        db.increment_views(movie["id"])
        text = movie_card_text(movie)
        kb = movie_keyboard(movie, message.from_user.id)
        if movie.get("poster_url"):
            try:
                await message.answer_photo(photo=movie["poster_url"], caption=text, reply_markup=kb)
            except Exception:
                await message.answer(text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)
        return

    # Nom bo'yicha qidiruv
    if len(query) < 2:
        return

    results = db.search_movies(query)
    if not results:
        await message.answer(
            f"❌ <b>\"{query}\"</b> bo'yicha hech narsa topilmadi.\n\n"
            f"🔢 Kino kodini ham sinab ko'ring!"
        )
        return

    builder = InlineKeyboardBuilder()
    for m in results:
        label = f"🎥 {m['title']}"
        if m.get("year"):
            label += f" ({m['year']})"
        if m.get("country"):
            label += f" | 🌍{m['country']}"
        builder.button(text=label, callback_data=f"movie:{m['id']}")
    builder.button(text="⬅️ Bosh sahifa", callback_data="back_main")
    builder.adjust(1)

    await message.answer(
        f"🔍 <b>\"{query}\"</b> bo'yicha {len(results)} ta natija:",
        reply_markup=builder.as_markup()
    )

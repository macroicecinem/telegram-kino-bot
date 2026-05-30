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


async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(TELEGRAM_CHANNEL, user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception:
        return False


def subscription_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📺 Telegram kanal", url=f"https://t.me/macroicecinema")
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


async def show_main_menu(message: Message):
    count = db.get_movies_count()
    await message.answer(
        f"🎬 <b>MACROICE Cinema botiga xush kelibsiz!</b>\n\n"
        f"Bazada hozir <b>{count} ta</b> kino mavjud.\n\n"
        f"Janrni tanlang yoki qidirish tugmasini bosing 👇",
        reply_markup=genres_keyboard()
    )


# ── /start ─────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id

    # Ro'yxatdan o'tganmi?
    user = db.get_user(user_id)

    if not user:
        # Yangi foydalanuvchi — telefon so'ra
        await state.set_state(Registration.phone)
        await message.answer(
            "👋 <b>Assalomu alaykum!</b>\n\n"
            "Botdan foydalanish uchun telefon raqamingizni tasdiqlang 👇",
            reply_markup=phone_keyboard()
        )
        return

    # Obunani tekshir
    subscribed = await check_subscription(bot, user_id)
    if not subscribed:
        await message.answer(
            "❌ <b>MACROICE kanallariga obuna bo'ling:</b>\n\n"
            "Obuna bo'lgach <b>✅ Obuna bo'ldim!</b> tugmasini bosing.",
            reply_markup=subscription_keyboard()
        )
        return

    await show_main_menu(message)


# ── Telefon qabul qilish ───────────────────────────────
@router.message(Registration.phone, F.contact)
async def get_phone(message: Message, state: FSMContext, bot: Bot):
    contact = message.contact
    user_id = message.from_user.id
    phone = contact.phone_number
    username = message.from_user.username
    full_name = message.from_user.full_name

    db.add_user(user_id, phone, username, full_name)
    await state.clear()

    await message.answer(
        "✅ <b>Telefon raqam tasdiqlandi!</b>",
        reply_markup=ReplyKeyboardRemove()
    )

    # Obunani tekshir
    subscribed = await check_subscription(bot, user_id)
    if not subscribed:
        await message.answer(
            "📢 <b>MACROICE kanallariga obuna bo'ling:</b>\n\n"
            "Obuna bo'lgach <b>✅ Obuna bo'ldim!</b> tugmasini bosing.",
            reply_markup=subscription_keyboard()
        )
        return

    await show_main_menu(message)


@router.message(Registration.phone)
async def wrong_phone(message: Message):
    await message.answer(
        "📱 Iltimos, tugma orqali telefon raqamingizni yuboring:",
        reply_markup=phone_keyboard()
    )


# ── Obuna tekshirish ───────────────────────────────────
@router.callback_query(F.data == "check_sub")
async def check_sub_callback(call: CallbackQuery, bot: Bot):
    subscribed = await check_subscription(bot, call.from_user.id)
    if not subscribed:
        await call.answer(
            "❌ Siz hali @macroicecinema kanaliga obuna bo'lmadingiz!",
            show_alert=True
        )
        return

    await call.message.delete()
    await show_main_menu(call.message)


# ── Janr tanlandi ──────────────────────────────────────
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

    await call.message.edit_text(
        f"🎬 <b>{genre['name']}</b> — {len(movies)} ta kino\n\nKinoni tanlang:",
        reply_markup=movies_keyboard(genre_id)
    )


# ── Kino tanlandi ──────────────────────────────────────
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

    text = f"🎬 <b>{movie['title']}</b>\n"
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
                reply_markup=kb
            )
            await call.message.delete()
        except Exception:
            await call.message.edit_text(text, reply_markup=kb)
    else:
        await call.message.edit_text(text, reply_markup=kb)


# ── Orqaga ─────────────────────────────────────────────
@router.callback_query(F.data == "back_genres")
async def back_to_genres(call: CallbackQuery):
    count = db.get_movies_count()
    await call.message.edit_text(
        f"🎬 <b>MACROICE Cinema botiga xush kelibsiz!</b>\n\n"
        f"Bazada hozir <b>{count} ta</b> kino mavjud.\n\n"
        f"Janrni tanlang yoki qidirish tugmasini bosing 👇",
        reply_markup=genres_keyboard()
    )


# ── Qidirish ───────────────────────────────────────────
@router.callback_query(F.data == "search")
async def search_prompt(call: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer("❌ Avval kanalga obuna bo'ling!", show_alert=True)
        return
    await call.message.answer("🔍 Kino nomini yozing:")
    await call.answer()


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await message.answer(
            "❌ Botdan foydalanish uchun kanalga obuna bo'ling:",
            reply_markup=subscription_keyboard()
        )
        return

    query = message.text.strip()
    if len(query) < 2:
        return

    results = db.search_movies(query)
    if not results:
        await message.answer(
            f"❌ <b>\"{query}\"</b> bo'yicha hech narsa topilmadi.\n\n/kinolar — barcha kinolarni ko'rish"
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
        f"🔍 <b>\"{query}\"</b> bo'yicha {len(results)} ta natija:",
        reply_markup=builder.as_markup()
    )

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db

router = Router()

YOUTUBE_URL = "https://www.youtube.com/@MACROICEcinema"
INSTAGRAM_URL = "https://www.instagram.com/macroice_cinema/"
BANNER_GIF = "CgACAgIAAxkBAAIxC2oiuTuJXS1LQbV2EnOXz64qhIzJAAKWoQACWfYZSa2rlxDma_1cOwQ"

REQUIRED_CHANNELS = [
    {"username": "@macroicecinema", "url": "https://t.me/macroicecinema", "name": "🎬 MACROICE Cinema"},
]


class Registration(StatesGroup):
    phone = State()


class ContactAdmin(StatesGroup):
    message = State()


async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member("@macroicecinema", user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception:
        return True


def subscription_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 MACROICE Cinema", url="https://t.me/macroicecinema")
    builder.button(text="▶️ YouTube kanal", url=YOUTUBE_URL)
    builder.button(text="📸 Instagram", url=INSTAGRAM_URL)
    builder.button(text="✅ Obuna bo'ldim!", callback_data="check_sub")
    builder.adjust(1)
    return builder.as_markup()


def phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamimni yuborish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )


def main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Barcha filmlar", callback_data="all_movies")
    builder.button(text="📂 Filter", callback_data="filter_menu")
    builder.button(text="⭐️ Saqlangan", callback_data="saved_movies")
    builder.button(text="❓ Yordam", callback_data="help_menu")
    builder.button(text="💳 Donat qilish", callback_data="donate_menu")
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


def movies_keyboard(movies, back_callback="all_movies"):
    builder = InlineKeyboardBuilder()
    for m in movies:
        label = f"🎥 {m['title']}"
        if m.get("year"):
            label += f" ({m['year']})"
        builder.button(text=label, callback_data=f"movie:{m['id']}")
    builder.button(text="⬅️ Orqaga", callback_data=back_callback)
    builder.adjust(1)
    return builder.as_markup()


def movie_keyboard(movie: dict, user_id: int):
    builder = InlineKeyboardBuilder()
    if movie.get("channel_post_id") and movie.get("channel_username"):
        builder.button(text="▶️ Ko'rish", callback_data=f"watch:{movie['id']}")
    elif movie.get("link"):
        builder.button(text="▶️ Ko'rish", url=movie["link"])
    saved = db.is_saved(user_id, movie["id"])
    if saved:
        builder.button(text="❌ Saqlangandan o'chir", callback_data=f"unsave:{movie['id']}")
    else:
        builder.button(text="⭐️ Saqlash", callback_data=f"save:{movie['id']}")
    genre_id = movie.get("genre_id")
    if genre_id:
        builder.button(text="⬅️ Orqaga", callback_data=f"genre:{genre_id}")
    else:
        builder.button(text="⬅️ Orqaga", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()


def movie_card_text(movie):
    text = f"🎬 <b>{movie['title']}</b>\n"
    text += "━━━━━━━━━━━━━━━━━━\n"
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


async def show_main_menu(message: Message):
    text = (
        "🎬 <b>MACROICE Cinema botiga xush kelibsiz!</b>\n\n"
        "🔢 Kerakli film uchun kodni yozing"
    )
    try:
        await message.answer_animation(animation=BANNER_GIF, caption=text, reply_markup=main_keyboard())
    except Exception:
        await message.answer(text, reply_markup=main_keyboard())


async def show_movie_by_code(message: Message, code: str, user_id: int, bot: Bot) -> bool:
    """Kod bo'yicha kinoni topib, foydalanuvchiga ko'rsatadi.
    Kanaldagi https://t.me/BOT_USERNAME?start=KOD ssilkasi bosilganda ham,
    botga kod yozib yuborilganda ham shu funksiya ishlaydi."""
    movie_row = db.get_movie_by_code(code)
    if not movie_row:
        await message.answer(f"❌ <b>{code}</b> kodli kino topilmadi.")
        return False

    movie = dict(movie_row)
    db.increment_views(movie["id"])

    if movie.get("channel_post_id") and movie.get("channel_username"):
        channel = movie["channel_username"]
        if not channel.startswith("@"):
            channel = "@" + channel
        genre_id = movie.get("genre_id") or 0
        try:
            sent_msg = None
            try:
                sent_msg = await bot.copy_message(chat_id=user_id, from_chat_id=channel, message_id=movie["channel_post_id"])
            except Exception:
                sent_msg = await bot.forward_message(chat_id=user_id, from_chat_id=channel, message_id=movie["channel_post_id"])
            back_builder = InlineKeyboardBuilder()
            back_builder.button(text="⬅️ Orqaga", callback_data=f"delete_and_back:{movie['id']}:{genre_id}:{sent_msg.message_id}")
            await bot.send_message(chat_id=user_id, text="👆 Film yuqorida", reply_markup=back_builder.as_markup())
            return True
        except Exception:
            pass

    text = movie_card_text(movie)
    kb = movie_keyboard(movie, user_id)
    if movie.get("poster_url"):
        try:
            await message.answer_photo(photo=movie["poster_url"], caption=text, reply_markup=kb)
            return True
        except Exception:
            pass
    await message.answer(text, reply_markup=kb)
    return True


@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    payload = command.args  # https://t.me/BOT_USERNAME?start=717 -> "717"

    if not user:
        if payload:
            await state.update_data(pending_code=payload)
        await state.set_state(Registration.phone)
        await message.answer(
            "👋 <b>Assalomu alaykum!</b>\n\nBotdan foydalanish uchun telefon raqamingizni tasdiqlang 👇",
            reply_markup=phone_keyboard()
        )
        return

    subscribed = await check_subscription(bot, user_id)
    if not subscribed:
        if payload:
            await state.update_data(pending_code=payload)
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
                "❌ <b>MACROICE kanallariga obuna bo'ling:</b>\n\nObuna bo'lgach ✅ bosing.",
                reply_markup=subscription_keyboard()
            )
        return

    if payload:
        shown = await show_movie_by_code(message, payload, user_id, bot)
        if shown:
            return

    await show_main_menu(message)


@router.message(Command("kinolar"))
async def cmd_kinolar(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await message.answer("❌ <b>MACROICE kanallariga obuna bo'ling:</b>", reply_markup=subscription_keyboard())
        return
    await show_main_menu(message)


@router.message(Registration.phone, F.contact)
async def get_phone(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    db.add_user(user_id, message.contact.phone_number, message.from_user.username, message.from_user.full_name)
    data = await state.get_data()
    pending_code = data.get("pending_code")
    await state.clear()
    await message.answer("✅ <b>Telefon raqam tasdiqlandi!</b>", reply_markup=ReplyKeyboardRemove())
    subscribed = await check_subscription(bot, user_id)
    if not subscribed:
        if pending_code:
            await state.update_data(pending_code=pending_code)
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
            await message.answer("📢 <b>MACROICE kanallariga obuna bo'ling:</b>", reply_markup=subscription_keyboard())
        return
    if pending_code:
        shown = await show_movie_by_code(message, pending_code, user_id, bot)
        if shown:
            return
    await show_main_menu(message)


@router.message(Registration.phone)
async def wrong_phone(message: Message):
    await message.answer("📱 Tugma orqali telefon raqamingizni yuboring:", reply_markup=phone_keyboard())


@router.callback_query(F.data == "check_sub")
async def check_sub_callback(call: CallbackQuery, bot: Bot, state: FSMContext):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer("❌ Siz hali @macroicecinema kanaliga obuna bo'lmadingiz!", show_alert=True)
        return
    await call.message.delete()
    data = await state.get_data()
    pending_code = data.get("pending_code")
    if pending_code:
        await state.update_data(pending_code=None)
        shown = await show_movie_by_code(call.message, pending_code, call.from_user.id, bot)
        if shown:
            return
    await show_main_menu(call.message)


@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery):
    text = (
        "🎬 <b>MACROICE Cinema botiga xush kelibsiz!</b>\n\n"
        "🔢 Kerakli film uchun kodni yozing"
    )
    try:
        await call.message.delete()
        await call.message.answer_animation(animation=BANNER_GIF, caption=text, reply_markup=main_keyboard())
    except Exception:
        try:
            await call.message.edit_text(text, reply_markup=main_keyboard())
        except Exception:
            await call.message.answer(text, reply_markup=main_keyboard())


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


@router.callback_query(F.data.startswith("genre:"))
async def genre_selected(call: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer("❌ Avval kanalga obuna bo'ling!", show_alert=True)
        return
    genre_id = int(call.data.split(":")[1])
    genre = next((g for g in db.get_genres() if g["id"] == genre_id), None)
    if not genre:
        await call.answer("Janr topilmadi!", show_alert=True)
        return
    sagas = db.get_sagas_by_genre(genre_id)
    custom_text = genre.get("genre_text")
    if sagas:
        builder = InlineKeyboardBuilder()
        for saga in sagas:
            movies_in_saga = db.get_movies_by_saga(saga["name"], genre_id)
            builder.button(text=f"🎬 {saga['name']} ({len(movies_in_saga)} ta)", callback_data=f"saga:{genre_id}:{saga['name']}")
        no_saga = db.get_movies_without_saga(genre_id)
        if no_saga:
            builder.button(text=f"📽 Boshqa kinolar ({len(no_saga)} ta)", callback_data=f"saga:{genre_id}:__nosaga__")
        builder.button(text="⬅️ Orqaga", callback_data="all_movies")
        builder.adjust(1)
        total = db.get_movies_by_genre(genre_id)
        body = custom_text or (
            "📽 Filmlarni to'g'ri tartibda va tushunarli tarzda tomosha qilish uchun "
            "quyidagi fazalardan birini tanlang 👇"
        )
        saga_text = f"🎬 <b>{genre['name']}</b> — {len(total)} ta kino\n\n{body}"
        try:
            await call.message.edit_text(saga_text, reply_markup=builder.as_markup())
        except Exception:
            await call.message.delete()
            await call.message.answer(saga_text, reply_markup=builder.as_markup())
    else:
        movies = db.get_movies_by_genre(genre_id)
        if not movies:
            await call.answer("Bu janrda hali kino yo'q 😕", show_alert=True)
            return
        body = custom_text or "Kinoni tanlang:"
        text = f"🎬 <b>{genre['name']}</b> — {len(movies)} ta kino\n\n{body}"
        try:
            await call.message.edit_text(text, reply_markup=movies_keyboard(movies, back_callback="all_movies"))
        except Exception:
            await call.message.delete()
            await call.message.answer(text, reply_markup=movies_keyboard(movies, back_callback="all_movies"))


@router.callback_query(F.data.startswith("saga:"))
async def saga_selected(call: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer("❌ Avval kanalga obuna bo'ling!", show_alert=True)
        return
    parts = call.data.split(":", 2)
    genre_id = int(parts[1])
    saga_name = parts[2]
    saga_custom_text = None
    if saga_name == "__nosaga__":
        movies = db.get_movies_without_saga(genre_id)
        title = "📽 Boshqa kinolar"
    else:
        movies = db.get_movies_by_saga(saga_name, genre_id)
        title = saga_name
        sagas = db.get_sagas_by_genre(genre_id)
        saga_row = next((s for s in sagas if s["name"] == saga_name), None)
        if saga_row:
            saga_custom_text = saga_row.get("saga_text")
    if not movies:
        await call.answer("Bu sagada kino yo'q 😕", show_alert=True)
        return
    body = saga_custom_text or "Kinoni tanlang:"
    text = f"🎬 <b>{title}</b> — {len(movies)} ta kino\n\n{body}"
    try:
        await call.message.edit_text(text, reply_markup=movies_keyboard(movies, back_callback=f"genre:{genre_id}"))
    except Exception:
        await call.message.delete()
        await call.message.answer(text, reply_markup=movies_keyboard(movies, back_callback=f"genre:{genre_id}"))


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

    if movie.get("channel_post_id") and movie.get("channel_username"):
        channel = movie["channel_username"]
        if not channel.startswith("@"):
            channel = "@" + channel
        genre_id = movie.get("genre_id") or 0
        try:
            await call.message.delete()
        except Exception:
            pass
        try:
            sent_msg = None
            try:
                sent_msg = await bot.copy_message(chat_id=call.from_user.id, from_chat_id=channel, message_id=movie["channel_post_id"])
            except Exception:
                sent_msg = await bot.forward_message(chat_id=call.from_user.id, from_chat_id=channel, message_id=movie["channel_post_id"])
            back_builder = InlineKeyboardBuilder()
            back_builder.button(text="⬅️ Orqaga", callback_data=f"delete_and_back:{movie_id}:{genre_id}:{sent_msg.message_id}")
            await bot.send_message(chat_id=call.from_user.id, text="👆 Film yuqorida", reply_markup=back_builder.as_markup())
        except Exception:
            if movie.get("link"):
                link_builder = InlineKeyboardBuilder()
                link_builder.button(text="▶️ Kanal orqali ko'rish", url=movie["link"])
                genre_id = movie.get("genre_id") or 0
                if genre_id:
                    link_builder.button(text="⬅️ Orqaga", callback_data=f"genre:{genre_id}")
                else:
                    link_builder.button(text="⬅️ Orqaga", callback_data="back_main")
                link_builder.adjust(1)
                title = movie.get("title", "Film")
                await bot.send_message(call.from_user.id, f"🎬 <b>{title}</b>\n\n▶️ Filmni ko'rish uchun tugmani bosing:", reply_markup=link_builder.as_markup())
            else:
                await call.answer("❌ Film yuklanmadi!", show_alert=True)
        return

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
                await call.message.answer(text, reply_markup=kb)
    else:
        try:
            await call.message.edit_text(text, reply_markup=kb)
        except Exception:
            await call.message.delete()
            await call.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("watch:"))
async def watch_movie(call: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer("❌ Avval kanalga obuna bo'ling!", show_alert=True)
        return
    movie_id = int(call.data.split(":")[1])
    movie = db.get_movie(movie_id)
    if not movie:
        await call.answer("Kino topilmadi!", show_alert=True)
        return
    movie = dict(movie)
    channel = movie.get("channel_username", "")
    post_id = movie.get("channel_post_id")
    if not channel or not post_id:
        await call.answer("Kino linki topilmadi!", show_alert=True)
        return
    if not channel.startswith("@"):
        channel = "@" + channel
    genre_id = movie.get("genre_id") or 0
    try:
        await call.message.delete()
    except Exception:
        pass
    try:
        sent_msg = None
        try:
            sent_msg = await bot.copy_message(chat_id=call.from_user.id, from_chat_id=channel, message_id=post_id)
        except Exception:
            sent_msg = await bot.forward_message(chat_id=call.from_user.id, from_chat_id=channel, message_id=post_id)
        back_builder = InlineKeyboardBuilder()
        back_builder.button(text="⬅️ Orqaga", callback_data=f"delete_and_back:{movie_id}:{genre_id}:{sent_msg.message_id}")
        await bot.send_message(chat_id=call.from_user.id, text="👆 Film yuqorida", reply_markup=back_builder.as_markup())
    except Exception:
        if movie.get("link"):
            link_builder = InlineKeyboardBuilder()
            link_builder.button(text="▶️ Kanal orqali ko'rish", url=movie["link"])
            if genre_id:
                link_builder.button(text="⬅️ Orqaga", callback_data=f"genre:{genre_id}")
            else:
                link_builder.button(text="⬅️ Orqaga", callback_data="back_main")
            link_builder.adjust(1)
            title = movie.get("title", "Film")
            await bot.send_message(call.from_user.id, f"🎬 <b>{title}</b>\n\n▶️ Filmni ko'rish uchun tugmani bosing:", reply_markup=link_builder.as_markup())
        else:
            await call.answer("❌ Film yuklanmadi!", show_alert=True)


@router.callback_query(F.data.startswith("delete_and_back:"))
async def delete_and_back(call: CallbackQuery, bot: Bot):
    parts = call.data.split(":")
    movie_id = int(parts[1])
    genre_id = int(parts[2])
    forward_msg_id = int(parts[3])
    for msg_id in [forward_msg_id, call.message.message_id]:
        try:
            await bot.delete_message(call.from_user.id, msg_id)
        except Exception:
            pass
    if genre_id and genre_id != 0:
        movies = db.get_movies_by_genre(genre_id)
        genre = next((g for g in db.get_genres() if g["id"] == genre_id), None)
        if genre and movies:
            await call.message.answer(f"🎬 <b>{genre['name']}</b> — {len(movies)} ta kino\n\nKinoni tanlang:", reply_markup=movies_keyboard(movies, back_callback="all_movies"))
            return
    text = "🎬 <b>MACROICE Cinema botiga xush kelibsiz!</b>\n\n🔢 Kerakli film uchun kodni yozing"
    try:
        await call.message.answer_animation(animation=BANNER_GIF, caption=text, reply_markup=main_keyboard())
    except Exception:
        await call.message.answer(text, reply_markup=main_keyboard())


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


@router.callback_query(F.data == "saved_movies")
async def show_saved(call: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer("❌ Avval kanalga obuna bo'ling!", show_alert=True)
        return
    movies = db.get_saved_movies(call.from_user.id)
    builder = InlineKeyboardBuilder()
    if not movies:
        builder.button(text="⬅️ Orqaga", callback_data="back_main")
        try:
            await call.message.edit_text("⭐️ <b>Saqlangan filmlar</b>\n\nHozircha saqlanmagan.", reply_markup=builder.as_markup())
        except Exception:
            await call.message.delete()
            await call.message.answer("⭐️ <b>Saqlangan filmlar</b>\n\nHozircha saqlanmagan.", reply_markup=builder.as_markup())
        return
    for m in movies:
        label = f"⭐️ {m['title']}"
        if m.get("year"):
            label += f" ({m['year']})"
        builder.button(text=label, callback_data=f"movie:{m['id']}")
    builder.button(text="⬅️ Orqaga", callback_data="back_main")
    builder.adjust(1)
    try:
        await call.message.edit_text(f"⭐️ <b>Saqlangan filmlar</b> ({len(movies)} ta):", reply_markup=builder.as_markup())
    except Exception:
        await call.message.delete()
        await call.message.answer(f"⭐️ <b>Saqlangan filmlar</b> ({len(movies)} ta):", reply_markup=builder.as_markup())


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
        for item in db.get_genres():
            builder.button(text=item["name"], callback_data=f"fresult:genre:{item['id']}")
    elif filter_type == "country":
        for item in db.get_distinct_countries():
            builder.button(text=f"🌍 {item}", callback_data=f"fresult:country:{item}")
    elif filter_type == "year":
        for item in db.get_distinct_years():
            builder.button(text=f"📅 {item}", callback_data=f"fresult:year:{item}")
    elif filter_type == "quality":
        for item in db.get_distinct_qualities():
            builder.button(text=f"🎬 {item}", callback_data=f"fresult:quality:{item}")
    builder.button(text="⬅️ Orqaga", callback_data="filter_menu")
    builder.adjust(2)
    titles = {"genre": "Janr", "country": "Davlat", "year": "Yil", "quality": "Sifat"}
    try:
        await call.message.edit_text(f"📂 <b>{titles.get(filter_type, 'Filter')}</b> tanlang:", reply_markup=builder.as_markup())
    except Exception:
        await call.message.delete()
        await call.message.answer(f"📂 <b>{titles.get(filter_type, 'Filter')}</b> tanlang:", reply_markup=builder.as_markup())


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
        await call.message.edit_text(f"📂 <b>{len(movies)} ta natija:</b>", reply_markup=builder.as_markup())
    except Exception:
        await call.message.delete()
        await call.message.answer(f"📂 <b>{len(movies)} ta natija:</b>", reply_markup=builder.as_markup())


@router.callback_query(F.data == "help_menu")
async def help_menu(call: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="✉️ Adminga xabar yuborish", callback_data="contact_admin")
    builder.button(text="⬅️ Orqaga", callback_data="back_main")
    builder.adjust(1)
    try:
        await call.message.edit_text(
            "❓ <b>Yordam</b>\n\n"
            "🔢 Film kodi: Telegram kanallarimizda har bir film postida kod ko'rsatilgan. "
            "Shu kodni botga yozing — film darhol chiqadi!\n\n"
            "🔍 Qidiruv: Film nomini yozing yoki @macroicebot orqali qidiring\n\n"
            "📢 Muammo yoki taklif bo'lsa adminga yozing 👇",
            reply_markup=builder.as_markup()
        )
    except Exception:
        await call.message.delete()
        await call.message.answer(
            "❓ <b>Yordam</b>\n\n"
            "🔢 Film kodi: Telegram kanallarimizda har bir film postida kod ko'rsatilgan. "
            "Shu kodni botga yozing — film darhol chiqadi!\n\n"
            "🔍 Qidiruv: Film nomini yozing yoki @macroicebot orqali qidiring\n\n"
            "📢 Muammo yoki taklif bo'lsa adminga yozing 👇",
            reply_markup=builder.as_markup()
        )


@router.callback_query(F.data == "contact_admin")
async def contact_admin_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(ContactAdmin.message)
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="help_menu")
    try:
        await call.message.edit_text("✉️ <b>Adminga xabar</b>\n\nXabaringizni yozing:", reply_markup=builder.as_markup())
    except Exception:
        await call.message.answer("✉️ Xabaringizni yozing:")
    await call.answer()


@router.message(ContactAdmin.message)
async def contact_admin_send(message: Message, state: FSMContext, bot: Bot):
    import os
    admin_id = os.getenv("SUPER_ADMIN_ID")
    user = message.from_user
    text = (
        f"📩 <b>Foydalanuvchidan xabar</b>\n\n"
        f"👤 Ism: {user.full_name}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👤 Username: @{user.username or 'yoq'}\n\n"
        f"💬 Xabar:\n{message.text}"
    )
    try:
        reply_builder = InlineKeyboardBuilder()
        reply_builder.button(text="↩️ Javob berish", callback_data=f"reply_user:{user.id}")
        await bot.send_message(admin_id, text, reply_markup=reply_builder.as_markup())
        await message.answer("✅ Xabaringiz adminga yuborildi!")
    except Exception:
        await message.answer("❌ Xabar yuborilmadi.")
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Bosh sahifa", callback_data="back_main")
    await message.answer("Bosh sahifaga qaytish:", reply_markup=builder.as_markup())


@router.callback_query(F.data == "donate_menu")
async def donate_menu(call: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 iDonate", url="https://idonate.uz/d/MACROICE")
    builder.button(text="💚 Tirikchilik", url="https://tirikchilik.uz/macroice")
    builder.button(text="⬅️ Orqaga", callback_data="back_main")
    builder.adjust(1)
    try:
        await call.message.edit_text(
            "💳 <b>Donat qilish</b>\n\n"
            "MACROICE Cinema botini rivojlantirish uchun donat qilishingiz mumkin!\n\n"
            "Quyidagi usullardan birini tanlang 👇",
            reply_markup=builder.as_markup()
        )
    except Exception:
        await call.message.delete()
        await call.message.answer(
            "💳 <b>Donat qilish</b>\n\n"
            "MACROICE Cinema botini rivojlantirish uchun donat qilishingiz mumkin!\n\n"
            "Quyidagi usullardan birini tanlang 👇",
            reply_markup=builder.as_markup()
        )


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await message.answer("❌ Botdan foydalanish uchun kanalga obuna bo'ling:", reply_markup=subscription_keyboard())
        return
    query = message.text.strip()
    if len(query) < 1:
        return
    movie_by_code = db.get_movie_by_code(query)
    if movie_by_code:
        await show_movie_by_code(message, query, message.from_user.id, bot)
        return
    if len(query) < 2:
        return
    results = db.search_movies(query)
    if not results:
        await message.answer(f"❌ <b>\"{query}\"</b> bo'yicha hech narsa topilmadi.\n\n🔢 Kino kodini ham sinab ko'ring!")
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
    await message.answer(f"🔍 <b>\"{query}\"</b> bo'yicha {len(results)} ta natija:", reply_markup=builder.as_markup())

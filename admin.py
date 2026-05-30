from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db

router = Router()


class AddMovie(StatesGroup):
    title = State()
    link = State()
    genre = State()
    description = State()
    poster = State()
    year = State()


class AddGenre(StatesGroup):
    name = State()


class AddAdmin(StatesGroup):
    user_id = State()


def admin_panel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Kino qo'shish", callback_data="admin:add_movie")
    builder.button(text="📋 Barcha kinolar", callback_data="admin:list_movies")
    builder.button(text="🎭 Janr qo'shish", callback_data="admin:add_genre")
    builder.button(text="📂 Janrlar", callback_data="admin:list_genres")
    builder.button(text="👥 Adminlar", callback_data="admin:list_admins")
    builder.button(text="➕ Admin qo'shish", callback_data="admin:add_admin")
    builder.button(text="📊 Statistika", callback_data="admin:stats")
    builder.adjust(2)
    return builder.as_markup()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not db.is_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz!")
        return
    count = db.get_movies_count()
    users = db.get_users_count()
    await message.answer(
        f"👨‍💼 <b>Admin Panel</b>\n\nKinolar: <b>{count} ta</b> | Foydalanuvchilar: <b>{users} ta</b>",
        reply_markup=admin_panel_keyboard()
    )


@router.callback_query(F.data.startswith("admin:"))
async def admin_callback(call: CallbackQuery, state: FSMContext):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    action = call.data.split(":")[1]

    if action == "add_movie":
        await state.set_state(AddMovie.title)
        await call.message.answer("🎬 Kino nomini kiriting:")
        await call.answer()

    elif action == "list_movies":
        movies = db.get_all_movies()
        if not movies:
            await call.answer("Hali kino yo'q!", show_alert=True)
            return
        builder = InlineKeyboardBuilder()
        for m in movies:
            builder.button(text=f"🗑 {m['title']}", callback_data=f"del_movie:{m['id']}")
        builder.button(text="⬅️ Panel", callback_data="admin:back")
        builder.adjust(1)
        await call.message.edit_text(
            f"📋 <b>Barcha kinolar</b> ({len(movies)} ta)\n\n🗑 O'chirish uchun bosing:",
            reply_markup=builder.as_markup()
        )

    elif action == "add_genre":
        await state.set_state(AddGenre.name)
        await call.message.answer("🎭 Yangi janr nomini kiriting:")
        await call.answer()

    elif action == "list_genres":
        genres = db.get_genres()
        builder = InlineKeyboardBuilder()
        for g in genres:
            builder.button(text=f"🗑 {g['name']}", callback_data=f"del_genre:{g['id']}")
        builder.button(text="⬅️ Panel", callback_data="admin:back")
        builder.adjust(2)
        await call.message.edit_text(
            f"📂 <b>Janrlar</b> ({len(genres)} ta)\n\n🗑 O'chirish uchun bosing:",
            reply_markup=builder.as_markup()
        )

    elif action == "list_admins":
        admins = db.get_all_admins()
        builder = InlineKeyboardBuilder()
        for a in admins:
            name = a["username"] or str(a["user_id"])
            builder.button(text=f"🗑 {name}", callback_data=f"del_admin:{a['user_id']}")
        builder.button(text="⬅️ Panel", callback_data="admin:back")
        builder.adjust(1)
        text = f"👥 <b>Adminlar</b> ({len(admins)} ta)"
        if not admins:
            text += "\n\nHozircha qo'shimcha admin yo'q."
        await call.message.edit_text(text, reply_markup=builder.as_markup())

    elif action == "add_admin":
        await state.set_state(AddAdmin.user_id)
        await call.message.answer(
            "👤 Admin qilmoqchi bo'lgan foydalanuvchining <b>Telegram ID</b> sini kiriting:\n\n"
            "<i>(ID ni bilish uchun @userinfobot ga /start yuboring)</i>"
        )
        await call.answer()

    elif action == "stats":
        count = db.get_movies_count()
        users = db.get_users_count()
        await call.message.edit_text(
            f"📊 <b>Statistika</b>\n\n"
            f"🎬 Kinolar: <b>{count} ta</b>\n"
            f"👥 Foydalanuvchilar: <b>{users} ta</b>",
            reply_markup=admin_panel_keyboard()
        )

    elif action == "back":
        count = db.get_movies_count()
        users = db.get_users_count()
        await call.message.edit_text(
            f"👨‍💼 <b>Admin Panel</b>\n\nKinolar: <b>{count} ta</b> | Foydalanuvchilar: <b>{users} ta</b>",
            reply_markup=admin_panel_keyboard()
        )


@router.callback_query(F.data.startswith("del_movie:"))
async def delete_movie(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    movie_id = int(call.data.split(":")[1])
    movie = db.get_movie(movie_id)
    if movie:
        db.delete_movie(movie_id)
        await call.answer(f"✅ '{movie['title']}' o'chirildi!", show_alert=True)
        movies = db.get_all_movies()
        builder = InlineKeyboardBuilder()
        for m in movies:
            builder.button(text=f"🗑 {m['title']}", callback_data=f"del_movie:{m['id']}")
        builder.button(text="⬅️ Panel", callback_data="admin:back")
        builder.adjust(1)
        if movies:
            await call.message.edit_text(
                f"📋 <b>Barcha kinolar</b> ({len(movies)} ta)\n\n🗑 O'chirish uchun bosing:",
                reply_markup=builder.as_markup()
            )
        else:
            await call.message.edit_text("📋 Hali kino yo'q.", reply_markup=admin_panel_keyboard())


@router.callback_query(F.data.startswith("del_genre:"))
async def delete_genre(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    genre_id = int(call.data.split(":")[1])
    db.delete_genre(genre_id)
    await call.answer("✅ Janr o'chirildi!", show_alert=True)
    genres = db.get_genres()
    builder = InlineKeyboardBuilder()
    for g in genres:
        builder.button(text=f"🗑 {g['name']}", callback_data=f"del_genre:{g['id']}")
    builder.button(text="⬅️ Panel", callback_data="admin:back")
    builder.adjust(2)
    await call.message.edit_text(
        f"📂 <b>Janrlar</b> ({len(genres)} ta)\n\n🗑 O'chirish uchun bosing:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("del_admin:"))
async def delete_admin(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    user_id = int(call.data.split(":")[1])
    db.remove_admin(user_id)
    await call.answer("✅ Admin o'chirildi!", show_alert=True)
    admins = db.get_all_admins()
    builder = InlineKeyboardBuilder()
    for a in admins:
        name = a["username"] or str(a["user_id"])
        builder.button(text=f"🗑 {name}", callback_data=f"del_admin:{a['user_id']}")
    builder.button(text="⬅️ Panel", callback_data="admin:back")
    builder.adjust(1)
    await call.message.edit_text(
        f"👥 <b>Adminlar</b> ({len(admins)} ta)",
        reply_markup=builder.as_markup()
    )


@router.message(AddMovie.title)
async def add_movie_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddMovie.link)
    await message.answer("🔗 Kino linkini kiriting (URL yoki Telegram kanal linki):")


@router.message(AddMovie.link)
async def add_movie_link(message: Message, state: FSMContext):
    await state.update_data(link=message.text.strip())
    await state.set_state(AddMovie.genre)
    genres = db.get_genres()
    builder = InlineKeyboardBuilder()
    for g in genres:
        builder.button(text=g["name"], callback_data=f"setgenre:{g['id']}")
    builder.button(text="⏭ O'tkazib yuborish", callback_data="setgenre:0")
    builder.adjust(2)
    await message.answer("🎭 Janrni tanlang:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("setgenre:"), AddMovie.genre)
async def add_movie_genre(call: CallbackQuery, state: FSMContext):
    genre_id = int(call.data.split(":")[1])
    await state.update_data(genre_id=genre_id if genre_id != 0 else None)
    await state.set_state(AddMovie.year)
    await call.message.answer("📅 Yilini kiriting (masalan: 2024) yoki 0:")
    await call.answer()


@router.message(AddMovie.year)
async def add_movie_year(message: Message, state: FSMContext):
    text = message.text.strip()
    year = None
    if text != "0":
        try:
            year = int(text)
        except ValueError:
            await message.answer("Raqam kiriting yoki 0:")
            return
    await state.update_data(year=year)
    await state.set_state(AddMovie.description)
    await message.answer("📝 Tavsif kiriting (yoki — deb yozing):")


@router.message(AddMovie.description)
async def add_movie_desc(message: Message, state: FSMContext):
    desc = message.text.strip()
    await state.update_data(description=None if desc == "—" else desc)
    await state.set_state(AddMovie.poster)
    await message.answer("🖼 Poster URL kiriting (yoki — deb yozing):")


@router.message(AddMovie.poster)
async def add_movie_poster(message: Message, state: FSMContext):
    poster = message.text.strip()
    await state.update_data(poster_url=None if poster == "—" else poster)
    data = await state.get_data()
    movie_id = db.add_movie(
        title=data["title"],
        link=data["link"],
        genre_id=data.get("genre_id"),
        description=data.get("description"),
        poster_url=data.get("poster_url"),
        year=data.get("year")
    )
    await state.clear()
    await message.answer(
        f"✅ <b>{data['title']}</b> qo'shildi! (ID: {movie_id})\n\n/admin — panelga qaytish"
    )


@router.message(AddGenre.name)
async def add_genre_name(message: Message, state: FSMContext):
    name = message.text.strip()
    db.add_genre(name)
    await state.clear()
    await message.answer(f"✅ <b>{name}</b> janri qo'shildi!\n\n/admin — panelga qaytish")


@router.message(AddAdmin.user_id)
async def add_admin_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID. Raqam kiriting:")
        return
    db.add_admin(user_id)
    await state.clear()
    await message.answer(f"✅ {user_id} ID li foydalanuvchi admin qilindi!\n\n/admin — panelga qaytish")

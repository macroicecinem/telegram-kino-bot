from aiogram import Router, F, Bot
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
    year = State()
    country = State()
    quality = State()
    language = State()
    code = State()
    description = State()
    poster = State()


class AddGenre(StatesGroup):
    name = State()


class AddAdmin(StatesGroup):
    user_id = State()


class AddSaga(StatesGroup):
    genre_id = State()
    name = State()
    sort_order = State()


class AssignSaga(StatesGroup):
    movie_id = State()
    saga_name = State()


class EditMovie(StatesGroup):
    field = State()
    value = State()


class Broadcast(StatesGroup):
    message = State()


def admin_panel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Kino qo'shish", callback_data="admin:add_movie")
    builder.button(text="📋 Barcha kinolar", callback_data="admin:list_movies")
    builder.button(text="🎭 Janr qo'shish", callback_data="admin:add_genre")
    builder.button(text="📂 Janrlar", callback_data="admin:list_genres")
    builder.button(text="👥 Adminlar", callback_data="admin:list_admins")
    builder.button(text="➕ Admin qo'shish", callback_data="admin:add_admin")
    builder.button(text="📊 Statistika", callback_data="admin:stats")
    builder.button(text="📢 Hammaga xabar", callback_data="admin:broadcast")
    builder.button(text="🎭 Sagalar", callback_data="admin:sagas")
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
            builder.button(text=f"🎬 {m['title']}", callback_data=f"movie_actions:{m['id']}")
        builder.button(text="⬅️ Panel", callback_data="admin:back")
        builder.adjust(1)
        await call.message.edit_text(
            f"📋 <b>Barcha kinolar</b> ({len(movies)} ta)\n\nKinoni tanlang:",
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

    elif action == "broadcast":
        await state.set_state(Broadcast.message)
        await call.message.answer(
            "📢 Barcha foydalanuvchilarga yuboriladigan xabarni yozing:\n\n"
            "<i>(Matn, rasm yoki video yuborishingiz mumkin)</i>"
        )
        await call.answer()

    elif action == "sagas":
        genres = db.get_genres()
        builder = InlineKeyboardBuilder()
        for g in genres:
            sagas = db.get_sagas_by_genre(g["id"])
            builder.button(text=f"🎭 {g['name']} ({len(sagas)} saga)", callback_data=f"manage_sagas:{g['id']}")
        builder.button(text="⬅️ Panel", callback_data="admin:back")
        builder.adjust(1)
        await call.message.edit_text("🎭 <b>Saga boshqaruvi</b>\n\nJanrni tanlang:", reply_markup=builder.as_markup())

    elif action == "stats":
        count = db.get_movies_count()
        users = db.get_users_count()
        top_movies = db.get_top_movies(5)

        text = (
            f"📊 <b>Statistika</b>\n\n"
            f"🎬 Kinolar: <b>{count} ta</b>\n"
            f"👥 Foydalanuvchilar: <b>{users} ta</b>\n\n"
            f"🏆 <b>Top 5 ko'rilgan kinolar:</b>\n"
        )
        for i, m in enumerate(top_movies, 1):
            views = m.get("views") or 0
            text += f"{i}. {m['title']} — <b>{views} ko'rish</b>\n"

        await call.message.edit_text(text, reply_markup=admin_panel_keyboard())

    elif action == "back":
        count = db.get_movies_count()
        users = db.get_users_count()
        await call.message.edit_text(
            f"👨‍💼 <b>Admin Panel</b>\n\nKinolar: <b>{count} ta</b> | Foydalanuvchilar: <b>{users} ta</b>",
            reply_markup=admin_panel_keyboard()
        )


@router.callback_query(F.data.startswith("movie_actions:"))
async def movie_actions(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    movie_id = int(call.data.split(":")[1])
    movie = db.get_movie(movie_id)
    if not movie:
        await call.answer("Kino topilmadi!", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Nomini o'zgartir", callback_data=f"edit_movie:{movie_id}:title")
    builder.button(text="🔗 Linkni o'zgartir", callback_data=f"edit_movie:{movie_id}:link")
    builder.button(text="📅 Yilni o'zgartir", callback_data=f"edit_movie:{movie_id}:year")
    builder.button(text="🌍 Davlatni o'zgartir", callback_data=f"edit_movie:{movie_id}:country")
    builder.button(text="🎬 Sifatni o'zgartir", callback_data=f"edit_movie:{movie_id}:quality")
    builder.button(text="🗣 Tilni o'zgartir", callback_data=f"edit_movie:{movie_id}:language")
    builder.button(text="🔢 Kodni o'zgartir", callback_data=f"edit_movie:{movie_id}:code")
    builder.button(text="📝 Tavsifni o'zgartir", callback_data=f"edit_movie:{movie_id}:description")
    builder.button(text="🖼 Posterni o'zgartir", callback_data=f"edit_movie:{movie_id}:poster_url")
    builder.button(text="🗑 O'chirish", callback_data=f"del_movie:{movie_id}")
    builder.button(text="⬅️ Orqaga", callback_data="admin:list_movies")
    builder.adjust(1)

    text = f"🎬 <b>{movie['title']}</b>\n"
    if movie["year"]:
        text += f"📅 {movie['year']}\n"
    if movie["genre_name"]:
        text += f"🎭 {movie['genre_name']}\n"
    text += f"\nNimani o'zgartirmoqchisiz?"

    await call.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("edit_movie:"))
async def edit_movie_start(call: CallbackQuery, state: FSMContext):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    parts = call.data.split(":")
    movie_id = int(parts[1])
    field = parts[2]

    field_names = {
        "title": "yangi nomini",
        "link": "yangi linkini",
        "year": "yangi yilini (masalan: 2024)",
        "description": "yangi tavsifini (o'chirish uchun — yozing)",
        "poster_url": "yangi poster URL ni (o'chirish uchun — yozing)",
        "country": "yangi davlatini (o'chirish uchun — yozing)",
        "quality": "yangi sifatini (masalan: 1080p)",
        "language": "yangi tilini",
        "code": "yangi kodini"
    }

    await state.set_state(EditMovie.value)
    await state.update_data(movie_id=movie_id, field=field)
    await call.message.answer(f"✏️ Kinoning {field_names.get(field, field)}ni kiriting:")
    await call.answer()


@router.message(EditMovie.value)
async def edit_movie_save(message: Message, state: FSMContext):
    import re
    data = await state.get_data()
    movie_id = data["movie_id"]
    field = data["field"]
    value = message.text.strip()

    if value == "—":
        value = None

    if field == "year" and value:
        try:
            value = int(value)
        except ValueError:
            await message.answer("❌ Yil uchun raqam kiriting:")
            return

    # Link o'zgartirilsa channel ma'lumotlarini ham yangilaymiz
    if field == "link" and value:
        match = re.match(r"https?://t\.me/([^/]+)/(\d+)", value)
        if match:
            db.update_movie(movie_id, link=value, channel_username=match.group(1), channel_post_id=int(match.group(2)))
        else:
            db.update_movie(movie_id, link=value, channel_username=None, channel_post_id=None)
    else:
        db.update_movie(movie_id, **{field: value})

    await state.clear()

    movie = db.get_movie(movie_id)
    await message.answer(
        f"✅ <b>{movie['title']}</b> yangilandi!\n\n/admin — panelga qaytish"
    )


@router.callback_query(F.data == "admin:list_movies")
async def back_to_movies(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    movies = db.get_all_movies()
    builder = InlineKeyboardBuilder()
    for m in movies:
        builder.button(text=f"🎬 {m['title']}", callback_data=f"movie_actions:{m['id']}")
    builder.button(text="⬅️ Panel", callback_data="admin:back")
    builder.adjust(1)
    await call.message.edit_text(
        f"📋 <b>Barcha kinolar</b> ({len(movies)} ta)\n\nKinoni tanlang:",
        reply_markup=builder.as_markup()
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
    link = message.text.strip()
    
    # Kanal linkdan post_id va channel_username ajratib olish
    # https://t.me/macroice_marvel/123 -> channel: macroice_marvel, post_id: 123
    channel_username = None
    channel_post_id = None
    
    import re
    match = re.match(r"https?://t\.me/([^/]+)/(\d+)", link)
    if match:
        channel_username = match.group(1)
        channel_post_id = int(match.group(2))
    
    await state.update_data(link=link, channel_username=channel_username, channel_post_id=channel_post_id)
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
    await state.set_state(AddMovie.country)
    await message.answer("🌍 Davlatini kiriting (masalan: USA, O'zbekiston) yoki — :")


@router.message(AddMovie.country)
async def add_movie_country(message: Message, state: FSMContext):
    val = message.text.strip()
    await state.update_data(country=None if val == "—" else val)
    await state.set_state(AddMovie.quality)
    await message.answer("🎬 Sifatini kiriting (masalan: 1080p, 720p) yoki — :")


@router.message(AddMovie.quality)
async def add_movie_quality(message: Message, state: FSMContext):
    val = message.text.strip()
    await state.update_data(quality=None if val == "—" else val)
    await state.set_state(AddMovie.language)
    await message.answer("🗣 Tilini kiriting (masalan: O'zbek tilida) yoki — :")


@router.message(AddMovie.language)
async def add_movie_language(message: Message, state: FSMContext):
    val = message.text.strip()
    await state.update_data(language=None if val == "—" else val)
    # Kod avtomatik generatsiya qilinadi
    await state.update_data(code=None)
    await state.set_state(AddMovie.description)
    await message.answer("📝 Tavsif kiriting (yoki — deb yozing):")


@router.message(AddMovie.code)
async def add_movie_code(message: Message, state: FSMContext):
    val = message.text.strip()
    await state.update_data(code=None if val == "—" else val)
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
        year=data.get("year"),
        country=data.get("country"),
        quality=data.get("quality"),
        language=data.get("language"),
        code=data.get("code"),
        channel_username=data.get("channel_username"),
        channel_post_id=data.get("channel_post_id")
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


# ── Broadcast ──────────────────────────────────────────
@router.message(Broadcast.message)
async def broadcast_send(message: Message, state: FSMContext, bot: Bot):
    await state.clear()

    users = db.get_all_users()
    success = 0
    failed = 0

    status_msg = await message.answer(f"⏳ Yuborilmoqda... 0/{len(users)}")

    for i, user in enumerate(users):
        try:
            await message.copy_to(user["user_id"])
            success += 1
        except Exception:
            failed += 1

        if (i + 1) % 10 == 0:
            try:
                await status_msg.edit_text(f"⏳ Yuborilmoqda... {i+1}/{len(users)}")
            except Exception:
                pass

    await status_msg.edit_text(
        f"✅ <b>Xabar yuborildi!</b>\n\n"
        f"👥 Jami: {len(users)} ta\n"
        f"✅ Muvaffaqiyatli: {success} ta\n"
        f"❌ Yetmadi: {failed} ta"
    )


# ── Saga boshqaruvi ────────────────────────────────────
@router.callback_query(F.data.startswith("manage_sagas:"))
async def manage_sagas(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    genre_id = int(call.data.split(":")[1])
    genre = next((g for g in db.get_genres() if g["id"] == genre_id), None)
    sagas = db.get_sagas_by_genre(genre_id)

    builder = InlineKeyboardBuilder()
    for saga in sagas:
        builder.button(text=f"🗑 {saga['name']}", callback_data=f"del_saga:{saga['id']}")
    builder.button(text="➕ Saga qo'shish", callback_data=f"add_saga:{genre_id}")
    builder.button(text="🎬 Kinoga saga belgilash", callback_data=f"assign_saga_start:{genre_id}")
    builder.button(text="⬅️ Orqaga", callback_data="admin:sagas")
    builder.adjust(1)

    await call.message.edit_text(
        f"🎭 <b>{genre['name']}</b> sagalari ({len(sagas)} ta):\\n\\n"
        f"🗑 O'chirish uchun bosing:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("del_saga:"))
async def delete_saga(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    saga_id = int(call.data.split(":")[1])
    db.delete_saga(saga_id)
    await call.answer("✅ Saga o'chirildi!", show_alert=True)
    await manage_sagas(call)


@router.callback_query(F.data.startswith("add_saga:"))
async def add_saga_start(call: CallbackQuery, state: FSMContext):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    genre_id = int(call.data.split(":")[1])
    await state.set_state(AddSaga.name)
    await state.update_data(genre_id=genre_id)
    await call.message.answer(
        "🎭 Saga nomini kiriting:\\n\\n"
        "Masalan: <b>Faza 1: Avengers boshlang'ich</b>"
    )
    await call.answer()


@router.message(AddSaga.name)
async def add_saga_name(message: Message, state: FSMContext):
    data = await state.get_data()
    genre_id = data["genre_id"]
    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(AddSaga.sort_order)
    await message.answer("📊 Tartib raqamini kiriting (1, 2, 3...):")


@router.message(AddSaga.sort_order)
async def add_saga_order(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        sort_order = int(message.text.strip())
    except ValueError:
        await message.answer("Raqam kiriting:")
        return
    db.add_saga(data["genre_id"], data["name"], sort_order)
    await state.clear()
    await message.answer(
        f"✅ <b>{data['name']}</b> saga qo'shildi!\\n\\n/admin — panelga qaytish"
    )


# ── Kinoga saga belgilash ──────────────────────────────
@router.callback_query(F.data.startswith("assign_saga_start:"))
async def assign_saga_start(call: CallbackQuery, state: FSMContext):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    genre_id = int(call.data.split(":")[1])
    movies = db.get_movies_by_genre(genre_id)

    builder = InlineKeyboardBuilder()
    for m in movies:
        saga_label = f" [{m['saga']}]" if m.get('saga') else ""
        builder.button(text=f"{m['title']}{saga_label}", callback_data=f"assign_saga_movie:{m['id']}:{genre_id}")
    builder.button(text="⬅️ Orqaga", callback_data=f"manage_sagas:{genre_id}")
    builder.adjust(1)

    await call.message.edit_text(
        "🎬 Saga belgilamoqchi bo'lgan kinoni tanlang:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("assign_saga_movie:"))
async def assign_saga_movie(call: CallbackQuery, state: FSMContext):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    parts = call.data.split(":")
    movie_id = int(parts[1])
    genre_id = int(parts[2])

    sagas = db.get_sagas_by_genre(genre_id)
    builder = InlineKeyboardBuilder()
    for saga in sagas:
        builder.button(text=saga["name"], callback_data=f"set_saga:{movie_id}:{saga['name']}")
    builder.button(text="❌ Sagani o'chirish", callback_data=f"set_saga:{movie_id}:__remove__")
    builder.button(text="⬅️ Orqaga", callback_data=f"assign_saga_start:{genre_id}")
    builder.adjust(1)

    movie = db.get_movie(movie_id)
    await call.message.edit_text(
        f"🎬 <b>{movie['title']}</b>\\n\\nQaysi sagaga kiradi?",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("set_saga:"))
async def set_saga(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    parts = call.data.split(":", 2)
    movie_id = int(parts[1])
    saga_name = parts[2]

    if saga_name == "__remove__":
        db.update_movie(movie_id, saga=None)
        await call.answer("✅ Saga o'chirildi!", show_alert=True)
    else:
        db.update_movie(movie_id, saga=saga_name)
        await call.answer(f"✅ {saga_name} saga belgilandi!", show_alert=True)

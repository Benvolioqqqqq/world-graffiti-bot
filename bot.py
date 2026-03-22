import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import init_db, add_graffiti, get_all_graffiti, get_pending_graffiti, update_status, search_graffiti, delete_graffiti, get_stats, save_user, get_users_count, toggle_reaction, get_reactions_count, get_top_liked
from map_generator import generate_map
from aiogram.types import FSInputFile
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web
from web_server import create_app
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from texts import get_text, set_language, get_language
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def get_main_keyboard(user_id):
    t = lambda key: get_text(user_id, key)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_map"), web_app=WebAppInfo(url=WEB_APP_URL)), KeyboardButton(text=t("btn_add"))],
            [KeyboardButton(text=t("btn_gallery")), KeyboardButton(text=t("btn_search"))],
            [KeyboardButton(text=t("btn_stats")), KeyboardButton(text=t("btn_language"))]
        ],
        resize_keyboard=True
    )


def get_cancel_keyboard(user_id):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_text(user_id, "btn_cancel"))]],
        resize_keyboard=True
    )


def get_admin_keyboard(user_id):
    t = lambda key: get_text(user_id, key)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_map"), web_app=WebAppInfo(url=WEB_APP_URL)), KeyboardButton(text=t("btn_add"))],
            [KeyboardButton(text=t("btn_gallery")), KeyboardButton(text=t("btn_search"))],
            [KeyboardButton(text=t("btn_stats")), KeyboardButton(text=t("btn_manage"))],
            [KeyboardButton(text=t("btn_language"))]
        ],
        resize_keyboard=True
    )



# Определяем шаги диалога
class AddGraffiti(StatesGroup):
    photo = State()
    location = State()
    author = State()
    date = State()
    description = State()


class SearchGraffiti(StatesGroup):
    query = State()


# Все возможные тексты кнопок для фильтров
MAP_TEXTS = {"🗺 Карта", "🗺 Map", "🗺 რუკა", "🗺 Mapa", "🗺 Carte", "🗺 Karte", "/map"}
ADD_TEXTS = {"➕ Добавить граффити", "➕ Add graffiti", "➕ გრაფიტის დამატება", "➕ Añadir graffiti", "➕ Ajouter un graffiti", "➕ Graffiti hinzufügen", "/add"}
SEARCH_TEXTS = {"🔍 Поиск", "🔍 Search", "🔍 ძიება", "🔍 Buscar", "🔍 Rechercher", "🔍 Suchen", "/search"}
CANCEL_TEXTS = {"❌ Отмена", "❌ Cancel", "❌ გაუქმება", "❌ Cancelar", "❌ Annuler", "❌ Abbrechen"}
MANAGE_TEXTS = {"⚙️ Управление", "⚙️ Manage", "⚙️ მართვა", "⚙️ Gestionar", "⚙️ Gérer", "⚙️ Verwalten"}
LANGUAGE_TEXTS = {"🌐 Язык", "🌐 Language", "🌐 ენა", "🌐 Idioma", "🌐 Langue", "🌐 Sprache"}
STATS_TEXTS = {"📊 Статистика", "📊 Stats", "📊 სტატისტიკა", "📊 Estadísticas", "📊 Statistiques", "📊 Statistiken"}
GALLERY_TEXTS = {"🖼 Галерея", "🖼 Gallery", "🖼 გალერეა", "🖼 Galería", "🖼 Galerie", "🖼 Galerie"}


# Команда /start
@dp.message(CommandStart())
async def start(message: types.Message):
    uid = message.from_user.id
    save_user(uid, message.from_user.username, message.from_user.full_name)
    kb = get_admin_keyboard(uid) if uid == ADMIN_ID else get_main_keyboard(uid)
    await message.answer(get_text(uid, "start"), reply_markup=kb)


# Выбор языка
@dp.message(F.text.in_(LANGUAGE_TEXTS))
async def choose_language(message: types.Message):
    uid = message.from_user.id
    lang_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
             InlineKeyboardButton(text="🇪🇸 Español", callback_data="lang_es")],
            [InlineKeyboardButton(text="🇫🇷 Français", callback_data="lang_fr"),
             InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_de")],
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
             InlineKeyboardButton(text="🇬🇪 ქართული", callback_data="lang_ka")]
        ]
    )
    await message.answer(get_text(uid, "choose_language"), reply_markup=lang_keyboard)


@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(callback: types.CallbackQuery):
    uid = callback.from_user.id
    lang = callback.data.split("_")[1]
    set_language(uid, lang)
    kb = get_admin_keyboard(uid) if uid == ADMIN_ID else get_main_keyboard(uid)
    await callback.message.answer(get_text(uid, "language_set"), reply_markup=kb)
    await callback.answer()


# Карта
@dp.message(F.text.in_(MAP_TEXTS))
async def show_map(message: types.Message):
    uid = message.from_user.id
    kb = get_admin_keyboard(uid) if uid == ADMIN_ID else get_main_keyboard(uid)
    graffiti_list = get_all_graffiti()
    if not graffiti_list:
        await message.answer(get_text(uid, "no_graffiti"), reply_markup=kb)
        return
    if not os.path.exists("map.html"):
        await generate_map(bot)
    web_app_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=get_text(uid, "btn_open_map"),
                web_app=WebAppInfo(url=WEB_APP_URL)
            )]
        ]
    )
    await message.answer(get_text(uid, "open_map"), reply_markup=web_app_button)


# Отмена
@dp.message(F.text.in_(CANCEL_TEXTS))
async def cancel(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    kb = get_admin_keyboard(uid) if uid == ADMIN_ID else get_main_keyboard(uid)
    await message.answer(get_text(uid, "cancelled"), reply_markup=kb)


# Поиск
@dp.message(F.text.in_(SEARCH_TEXTS))
async def search_start(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    await message.answer(get_text(uid, "search_prompt"), reply_markup=get_cancel_keyboard(uid))
    await state.set_state(SearchGraffiti.query)


@dp.message(SearchGraffiti.query)
async def search_results(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    query = message.text.strip()
    results = search_graffiti(query)
    kb = get_admin_keyboard(uid) if uid == ADMIN_ID else get_main_keyboard(uid)

    if not results:
        await message.answer(get_text(uid, "search_empty").format(query), reply_markup=kb)
        await state.clear()
        return

    await message.answer(get_text(uid, "search_found").format(len(results)))

    for item in results:
        g_id, lat, lon, photo_id, author, date, description, added_by, created_at, status = item
        text = (
            f"🎨 {author}\n"
            f"📅 {date}\n"
            f"📝 {description or get_text(uid, 'no_description')}\n"
            f"📍 {lat}, {lon}"
        )
        counts = get_reactions_count(g_id)
        reaction_keyboard = get_reaction_keyboard(g_id, counts)
        if photo_id:
            await message.answer_photo(photo=photo_id, caption=text, reply_markup=reaction_keyboard)
        else:
            await message.answer(text, reply_markup=reaction_keyboard)


# Добавление граффити
@dp.message(F.text.in_(ADD_TEXTS))
async def add_start(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    await message.answer(get_text(uid, "send_photo"), reply_markup=get_cancel_keyboard(uid))
    await state.set_state(AddGraffiti.photo)


@dp.message(AddGraffiti.photo, F.photo)
async def get_photo(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await message.answer(get_text(uid, "send_location"))
    await state.set_state(AddGraffiti.location)


@dp.message(AddGraffiti.photo)
async def get_photo_wrong(message: types.Message):
    uid = message.from_user.id
    await message.answer(get_text(uid, "send_photo_please"))


@dp.message(AddGraffiti.location, F.location)
async def get_location(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    await state.update_data(
        latitude=message.location.latitude,
        longitude=message.location.longitude
    )
    await message.answer(get_text(uid, "send_author"))
    await state.set_state(AddGraffiti.author)


@dp.message(AddGraffiti.location)
async def get_location_wrong(message: types.Message):
    uid = message.from_user.id
    await message.answer(get_text(uid, "send_location_please"))


@dp.message(AddGraffiti.author)
async def get_author(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    author = message.text.strip()
    no_words = {"нет", "no", "არა", "non", "nein"}
    if author.lower() in no_words:
        author = get_text(uid, "unknown_author")
    await state.update_data(author=author)
    await message.answer(get_text(uid, "send_date"))
    await state.set_state(AddGraffiti.date)


@dp.message(AddGraffiti.date)
async def get_date(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    date = message.text.strip()
    no_words = {"нет", "no", "არა", "non", "nein"}
    if date.lower() in no_words:
        date = get_text(uid, "unknown_date")
    await state.update_data(date=date)
    await message.answer(get_text(uid, "send_description"))
    await state.set_state(AddGraffiti.description)


@dp.message(AddGraffiti.description)
async def get_description(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    description = message.text.strip()
    no_words = {"нет", "no", "არა", "non", "nein"}
    if description.lower() in no_words:
        description = ""

    data = await state.get_data()

    graffiti_id = add_graffiti(
        latitude=data["latitude"],
        longitude=data["longitude"],
        photo_id=data["photo_id"],
        author=data["author"],
        date=data["date"],
        description=description,
        added_by=message.from_user.username or message.from_user.full_name
    )

    kb = get_admin_keyboard(uid) if uid == ADMIN_ID else get_main_keyboard(uid)
    await message.answer(get_text(uid, "added"), reply_markup=kb)

    # Уведомляем админа
    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{graffiti_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{graffiti_id}")
            ]
        ]
    )
    await bot.send_photo(
        ADMIN_ID,
        photo=data["photo_id"],
        caption=f"Новое граффити на модерацию:\n\n"
                f"🎨 Автор: {data['author']}\n"
                f"📅 Дата: {data['date']}\n"
                f"📝 Описание: {description}\n"
                f"📍 Координаты: {data['latitude']}, {data['longitude']}\n"
                f"👤 Добавил: {message.from_user.full_name}",
        reply_markup=admin_keyboard
    )

    await state.clear()


# Модерация
@dp.callback_query(F.data.startswith("approve_"))
async def approve(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    graffiti_id = int(callback.data.split("_")[1])
    update_status(graffiti_id, "approved")
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ ОДОБРЕНО",
        reply_markup=None
    )
    await callback.answer("Одобрено!")
    # Обновляем карту
    await generate_map(bot)
    # Публикуем в канал
    try:
        await bot.send_photo(
            chat_id="@graffiti_map",
            photo=callback.message.photo[-1].file_id,
            caption=callback.message.caption.replace("\n\n✅ ОДОБРЕНО", "") + "\n\n🗺 @graffiti_map_bot"
        )
    except Exception as e:
        print(f"Channel post error: {e}")


@dp.callback_query(F.data.startswith("reject_"))
async def reject(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    graffiti_id = int(callback.data.split("_")[1])
    update_status(graffiti_id, "rejected")
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ ОТКЛОНЕНО",
        reply_markup=None
    )
    await callback.answer("Отклонено!")


# Управление
PAGE_SIZE = 10

@dp.message(F.text.in_(MANAGE_TEXTS))
async def manage_graffiti(message: types.Message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
        await message.answer(get_text(uid, "admin_only"))
        return

    graffiti_list = get_all_graffiti()
    kb = get_admin_keyboard(uid)
    if not graffiti_list:
        await message.answer(get_text(uid, "no_graffiti"), reply_markup=kb)
        return

    await send_graffiti_page(message, uid, graffiti_list, page=0)


async def send_graffiti_page(message, uid, graffiti_list, page: int):
    total = len(graffiti_list)
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    page_items = graffiti_list[start:end]

    await message.answer(f"📋 Граффити {start+1}–{end} из {total} (страница {page+1}/{total_pages})")

    for item in page_items:
        g_id, lat, lon, photo_id, author, date, description, added_by, created_at, status = item
        text = (
            f"ID: {g_id}\n"
            f"🎨 {author}\n"
            f"📅 {date}\n"
            f"📝 {description or get_text(uid, 'no_description')}"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=get_text(uid, "delete"), callback_data=f"delete_{g_id}")]
            ]
        )
        if photo_id:
            await message.answer_photo(photo=photo_id, caption=text, reply_markup=keyboard)
        else:
            await message.answer(text, reply_markup=keyboard)

    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"manage_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"manage_page_{page+1}"))

    if nav_buttons:
        nav_kb = InlineKeyboardMarkup(inline_keyboard=[nav_buttons])
        await message.answer(f"Страница {page+1} из {total_pages}", reply_markup=nav_kb)


@dp.callback_query(F.data.startswith("manage_page_"))
async def manage_page_callback(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    uid = callback.from_user.id
    graffiti_list = get_all_graffiti()
    await callback.answer()
    await send_graffiti_page(callback.message, uid, graffiti_list, page=page)


@dp.callback_query(F.data.startswith("delete_"))
async def delete_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    uid = callback.from_user.id
    graffiti_id = int(callback.data.split("_")[1])
    confirm_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text(uid, "confirm_delete"),
                                     callback_data=f"confirm_delete_{graffiti_id}"),
                InlineKeyboardButton(text=get_text(uid, "cancel_delete_btn"), callback_data="cancel_delete")
            ]
        ]
    )
    await callback.message.edit_reply_markup(reply_markup=confirm_keyboard)
    await callback.answer(get_text(uid, "confirm_deletion"))


@dp.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    uid = callback.from_user.id
    graffiti_id = int(callback.data.split("_")[2])
    delete_graffiti(graffiti_id)
    await callback.message.edit_caption(
        caption=callback.message.caption + f"\n\n{get_text(uid, 'deleted')}",
        reply_markup=None
    )
    await callback.answer(get_text(uid, "deleted"))
    # Обновляем карту
    await generate_map(bot)


@dp.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()


@dp.message(F.text.in_(STATS_TEXTS))
async def show_stats(message: types.Message):
    uid = message.from_user.id
    stats = get_stats()
    text = get_text(uid, "stats").format(
        approved=stats["approved"],
        pending=stats["pending"],
        total=stats["total"]
    )
    users = get_users_count()
    text += get_text(uid, "users_count").format(users)

    if stats["top_users"]:
        text += get_text(uid, "top_users")
        medals = ["🥇", "🥈", "🥉"]
        for i, (user, count) in enumerate(stats["top_users"]):
            medal = medals[i] if i < 3 else f"{i+1}."
            if user and not user.startswith("@"):
                if not user.isdigit():
                    user_display = f"@{user}"
                else:
                    user_display = user
            else:
                user_display = user or "Аноним"
            text += f"\n{medal} {user_display} — {count}"



    await message.answer(text)

def get_reaction_keyboard(graffiti_id, counts=None):
    if not counts:
        counts = {"fire": 0, "like": 0, "puke": 0}
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"🔥 {counts['fire'] or ''}", callback_data=f"react_fire_{graffiti_id}"),
                InlineKeyboardButton(text=f"👍 {counts['like'] or ''}", callback_data=f"react_like_{graffiti_id}"),
                InlineKeyboardButton(text=f"🤮 {counts['puke'] or ''}", callback_data=f"react_puke_{graffiti_id}")
            ]
        ]
    )

def get_gallery_keyboard(index, total, graffiti_id):
    counts = get_reactions_count(graffiti_id)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"🔥 {counts['fire'] or ''}", callback_data=f"react_fire_{graffiti_id}"),
                InlineKeyboardButton(text=f"👍 {counts['like'] or ''}", callback_data=f"react_like_{graffiti_id}"),
                InlineKeyboardButton(text=f"🤮 {counts['puke'] or ''}", callback_data=f"react_puke_{graffiti_id}")
            ],
            [
                InlineKeyboardButton(text="◀️", callback_data=f"gallery_{index - 1}"),
                InlineKeyboardButton(text=f"{index + 1}/{total}", callback_data="gallery_noop"),
                InlineKeyboardButton(text="▶️", callback_data=f"gallery_{index + 1}")
            ]
        ]
    )

async def main():
    init_db()

    # Генерируем карту при старте
    if get_all_graffiti():
        await generate_map(bot)

    # Запускаем веб-сервер
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8081))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Веб-сервер запущен на порту {port}")

    # Запускаем бота
    await dp.start_polling(bot)


@dp.callback_query(F.data.startswith("react_"))
async def react_graffiti(callback: types.CallbackQuery):
    uid = callback.from_user.id
    parts = callback.data.split("_")
    reaction = parts[1]
    graffiti_id = int(parts[2])

    result = toggle_reaction(uid, graffiti_id, reaction)
    counts = get_reactions_count(graffiti_id)

    # Проверяем, есть ли кнопки галереи в текущей клавиатуре
    current_markup = callback.message.reply_markup
    gallery_row = None
    if current_markup:
        for row in current_markup.inline_keyboard:
            for btn in row:
                if btn.callback_data and btn.callback_data.startswith("gallery_"):
                    gallery_row = row
                    break

    if gallery_row:
        # Галерея — сохраняем стрелки
        new_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=f"🔥 {counts['fire'] or ''}", callback_data=f"react_fire_{graffiti_id}"),
                    InlineKeyboardButton(text=f"👍 {counts['like'] or ''}", callback_data=f"react_like_{graffiti_id}"),
                    InlineKeyboardButton(text=f"🤮 {counts['puke'] or ''}", callback_data=f"react_puke_{graffiti_id}")
                ],
                gallery_row
            ]
        )
    else:
        # Обычный поиск — только реакции
        new_keyboard = get_reaction_keyboard(graffiti_id, counts)

    try:
        await callback.message.edit_reply_markup(reply_markup=new_keyboard)
    except:
        pass

    emojis = {"fire": "🔥", "like": "👍", "puke": "🤮"}
    if result:
        await callback.answer(emojis[reaction])
    else:
        await callback.answer("Реакция убрана")


@dp.message(F.text.in_(GALLERY_TEXTS))
async def gallery_start(message: types.Message):
    uid = message.from_user.id
    graffiti_list = get_all_graffiti()
    if not graffiti_list:
        kb = get_admin_keyboard(uid) if uid == ADMIN_ID else get_main_keyboard(uid)
        await message.answer(get_text(uid, "gallery_empty"), reply_markup=kb)
        return

    item = graffiti_list[0]
    g_id, lat, lon, photo_id, author, date, description, added_by, created_at, status = item
    text = (
        f"🎨 {author}\n"
        f"📅 {date}\n"
        f"📝 {description or get_text(uid, 'no_description')}\n"
        f"📍 {lat}, {lon}"
    )
    keyboard = get_gallery_keyboard(0, len(graffiti_list), g_id)
    if photo_id:
        await message.answer_photo(photo=photo_id, caption=text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@dp.callback_query(F.data.startswith("gallery_"))
async def gallery_navigate(callback: types.CallbackQuery):
    if callback.data == "gallery_noop":
        await callback.answer()
        return

    uid = callback.from_user.id
    graffiti_list = get_all_graffiti()
    total = len(graffiti_list)
    index = int(callback.data.split("_")[1])

    if index < 0:
        index = total - 1
    elif index >= total:
        index = 0

    item = graffiti_list[index]
    g_id, lat, lon, photo_id, author, date, description, added_by, created_at, status = item
    text = (
        f"🎨 {author}\n"
        f"📅 {date}\n"
        f"📝 {description or get_text(uid, 'no_description')}\n"
        f"📍 {lat}, {lon}"
    )
    keyboard = get_gallery_keyboard(index, total, g_id)

    try:
        if photo_id:
            media = types.InputMediaPhoto(media=photo_id, caption=text)
            await callback.message.edit_media(media=media, reply_markup=keyboard)
        else:
            await callback.message.edit_text(text=text, reply_markup=keyboard)
    except:
        pass

    await callback.answer()


if __name__ == "__main__":
    asyncio.run(main())
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN
from db import (
    init_db,
    add_task, get_tasks, mark_task_done, delete_task, get_stats,
    add_note, get_notes, get_note_by_user_num, get_note_by_id, search_notes, delete_note,
    add_lesson, get_schedule, delete_lesson, get_all_lessons,
    get_deadline_tasks
)
from keyboards import main_menu, tasks_menu, notes_menu, schedule_menu, weekday_inline
from utils import parse_deadline, format_deadline, days_until
from datetime import datetime, timedelta


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_state = {}


async def reminder_loop():
    while True:
        try:
            await asyncio.sleep(60)
        except Exception:
            pass


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я StudyHelperBot 📚\n\n"
        "Я помогу тебе:\n"
        "📌 вести задачи и дедлайны\n"
        "🧠 хранить заметки\n"
        "🗓 вести расписание\n"
        "📊 смотреть статистику\n\n"
        "Выбирай раздел в меню 👇",
        reply_markup=main_menu()
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ Команды бота:\n\n"
        "/start — запуск\n"
        "/help — помощь\n\n"
        "Все функции доступны через кнопки меню."
    )


@dp.message(F.text == "ℹ️ Помощь")
async def help_btn(message: Message):
    await cmd_help(message)


@dp.message(F.text == "📌 Задачи")
async def tasks_section(message: Message):
    await message.answer("Раздел задач 📌", reply_markup=tasks_menu())


@dp.message(F.text == "🧠 Заметки")
async def notes_section(message: Message):
    await message.answer("Раздел заметок 🧠", reply_markup=notes_menu())


@dp.message(F.text == "🗓 Расписание")
async def schedule_section(message: Message):
    await message.answer("Раздел расписания 🗓", reply_markup=schedule_menu())


@dp.message(F.text == "⬅️ Назад")
async def back_to_main(message: Message):
    user_state.pop(message.from_user.id, None)
    await message.answer("Главное меню:", reply_markup=main_menu())


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@dp.message(F.text == "➕ Добавить задачу")
async def task_add_start(message: Message):
    user_state[message.from_user.id] = {"mode": "add_task_title"}
    await message.answer("Введите название задачи:")


@dp.message(F.text == "📋 Мои задачи")
async def task_list(message: Message):
    tasks = await get_tasks(message.from_user.id, only_active=True)

    if not tasks:
        await message.answer("Активных задач нет ✅")
        return

    text = "📋 Твои активные задачи:\n\n"
    for num, title, deadline, done in tasks:
        text += f"#{num} — {title} (⏰ {format_deadline(deadline)})\n"

    await message.answer(text)


@dp.message(F.text == "✅ Выполнить задачу")
async def task_done_start(message: Message):
    user_state[message.from_user.id] = {"mode": "done_task"}
    await message.answer("Введите номер задачи (например: 3):")


@dp.message(F.text == "🗑 Удалить задачу")
async def task_delete_start(message: Message):
    user_state[message.from_user.id] = {"mode": "delete_task"}
    await message.answer("Введите номер задачи для удаления:")


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

@dp.message(F.text == "➕ Добавить заметку")
async def note_add_start(message: Message):
    user_state[message.from_user.id] = {"mode": "add_note_title"}
    await message.answer("Введите заголовок заметки:")


@dp.message(F.text == "📒 Мои заметки")
async def notes_list(message: Message):
    notes = await get_notes(message.from_user.id)
    if not notes:
        await message.answer("Заметок пока нет 🧠")
        return

    text = "📒 Твои заметки:\n\n"
    for num, title, created_at in notes:
        text += f"#{num} — {title}\n"

    text += "\nЧтобы прочитать заметку, напиши: /note <номер>"

    await message.answer(text)


@dp.message(Command("note"))
async def read_note(message: Message):
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Используй формат: /note 3")
        return

    user_num = int(parts[1])
    note = await get_note_by_user_num(message.from_user.id, user_num)

    if not note:
        await message.answer("Заметка не найдена.")
        return

    title, content, created_at = note
    await message.answer(f"🧠 {title}\n\n{content}")


@dp.message(F.text == "🔍 Поиск заметки")
async def note_search_start(message: Message):
    user_state[message.from_user.id] = {"mode": "search_note"}
    await message.answer("Введите слово или фразу для поиска:")


@dp.message(F.text == "🗑 Удалить заметку")
async def note_delete_start(message: Message):
    user_state[message.from_user.id] = {"mode": "delete_note"}
    await message.answer("Введите номер заметки для удаления:")


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

@dp.message(F.text == "➕ Добавить пару")
async def schedule_add_start(message: Message):
    user_state[message.from_user.id] = {"mode": "add_lesson_day"}
    await message.answer("Выберите день недели:", reply_markup=weekday_inline())


@dp.callback_query(F.data.startswith("day:"))
async def choose_day(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_state or user_state[user_id].get("mode") != "add_lesson_day":
        await callback.answer()
        return

    day = int(callback.data.split(":")[1])
    user_state[user_id] = {"mode": "add_lesson_time", "day": day}

    await callback.message.answer("Введите время пары (например 09:30):")
    await callback.answer()


@dp.message(F.text == "📅 Показать расписание")
async def show_schedule(message: Message):
    lessons = await get_all_lessons(message.from_user.id)

    if not lessons:
        await message.answer("Расписание пустое 🗓")
        return

    days = {
        1: "Понедельник", 2: "Вторник", 3: "Среда",
        4: "Четверг", 5: "Пятница", 6: "Суббота", 7: "Воскресенье"
    }

    text = "🗓 Твоё расписание:\n\n"
    current_day = None

    for num, weekday, time, subject in lessons:
        if weekday != current_day:
            current_day = weekday
            text += f"\n📌 {days[weekday]}:\n"
        text += f"#{num} 🕒 {time} — {subject}\n"

    await message.answer(text)


@dp.message(F.text == "🗑 Удалить пару")
async def delete_lesson_start(message: Message):
    user_state[message.from_user.id] = {"mode": "delete_lesson"}
    await message.answer(
        "Введите номер пары для удаления.\n"
        "Номера видны в списке расписания (📅 Показать расписание)."
    )


@dp.message(F.text == "📊 Статистика")
async def stats(message: Message):
    total, done = await get_stats(message.from_user.id)
    active = total - done

    await message.answer(
        f"📊 Статистика:\n\n"
        f"Всего задач: {total}\n"
        f"Выполнено: {done}\n"
        f"Активно: {active}"
    )


# ---------------------------------------------------------------------------
# Universal text handler (FSM via user_state)
# ---------------------------------------------------------------------------

@dp.message()
async def handle_text(message: Message):
    user_id = message.from_user.id
    if user_id not in user_state:
        return

    state = user_state[user_id]
    mode = state.get("mode")

    # ---- TASK ADD ----
    if mode == "add_task_title":
        title = message.text.strip()
        user_state[user_id] = {"mode": "add_task_deadline", "title": title}
        await message.answer(
            "Введите дедлайн в формате:\n"
            "YYYY-MM-DD или YYYY-MM-DD HH:MM\n\n"
            "Если дедлайн не нужен — напишите: нет"
        )
        return

    if mode == "add_task_deadline":
        title = state["title"]
        text = message.text.strip()

        deadline = None
        if text.lower() != "нет":
            dt = parse_deadline(text)
            if not dt:
                await message.answer("Неверный формат. Попробуйте снова.")
                return
            deadline = dt.isoformat()

        await add_task(user_id, title, deadline)
        user_state.pop(user_id, None)
        await message.answer("✅ Задача добавлена!", reply_markup=tasks_menu())
        return

    if mode == "done_task":
        if not message.text.isdigit():
            await message.answer("Введите число (номер задачи).")
            return

        user_num = int(message.text)
        found = await mark_task_done(user_id, user_num)
        user_state.pop(user_id, None)
        if found:
            await message.answer("✅ Задача отмечена как выполненная.", reply_markup=tasks_menu())
        else:
            await message.answer("Задача с таким номером не найдена.", reply_markup=tasks_menu())
        return

    if mode == "delete_task":
        if not message.text.isdigit():
            await message.answer("Введите число (номер задачи).")
            return

        user_num = int(message.text)
        found = await delete_task(user_id, user_num)
        user_state.pop(user_id, None)
        if found:
            await message.answer("🗑 Задача удалена.", reply_markup=tasks_menu())
        else:
            await message.answer("Задача с таким номером не найдена.", reply_markup=tasks_menu())
        return

    # ---- NOTE ADD ----
    if mode == "add_note_title":
        title = message.text.strip()
        user_state[user_id] = {"mode": "add_note_content", "title": title}
        await message.answer("Введите текст заметки:")
        return

    if mode == "add_note_content":
        title = state["title"]
        content = message.text.strip()

        await add_note(user_id, title, content)
        user_state.pop(user_id, None)
        await message.answer("✅ Заметка сохранена!", reply_markup=notes_menu())
        return

    if mode == "search_note":
        query = message.text.strip()
        results = await search_notes(user_id, query)

        if not results:
            await message.answer("Ничего не найдено.")
        else:
            text = "🔍 Найдено:\n\n"
            for num, title in results:
                text += f"#{num} — {title}\n"
            text += "\nЧтобы открыть: /note <номер>"
            await message.answer(text)

        user_state.pop(user_id, None)
        return

    if mode == "delete_note":
        if not message.text.isdigit():
            await message.answer("Введите число (номер заметки).")
            return

        user_num = int(message.text)
        found = await delete_note(user_id, user_num)
        user_state.pop(user_id, None)
        if found:
            await message.answer("🗑 Заметка удалена.", reply_markup=notes_menu())
        else:
            await message.answer("Заметка с таким номером не найдена.", reply_markup=notes_menu())
        return

    # ---- SCHEDULE ADD ----
    if mode == "add_lesson_time":
        time = message.text.strip()
        if len(time) != 5 or time[2] != ":":
            await message.answer("Введите время в формате HH:MM (например 09:30).")
            return

        user_state[user_id]["time"] = time
        user_state[user_id]["mode"] = "add_lesson_subject"
        await message.answer("Введите название предмета:")
        return

    if mode == "add_lesson_subject":
        subject = message.text.strip()
        day = state["day"]
        time = state["time"]

        await add_lesson(user_id, day, time, subject)
        user_state.pop(user_id, None)
        await message.answer("✅ Пара добавлена!", reply_markup=schedule_menu())
        return

    if mode == "delete_lesson":
        if not message.text.isdigit():
            await message.answer("Введите номер пары числом.")
            return

        user_num = int(message.text)
        found = await delete_lesson(user_id, user_num)
        user_state.pop(user_id, None)
        if found:
            await message.answer("🗑 Пара удалена.", reply_markup=schedule_menu())
        else:
            await message.answer("Пара с таким номером не найдена.", reply_markup=schedule_menu())
        return


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
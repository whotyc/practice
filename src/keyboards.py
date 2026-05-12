from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📌 Задачи"), KeyboardButton(text="🧠 Заметки")],
            [KeyboardButton(text="🗓 Расписание"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )


def tasks_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить задачу"), KeyboardButton(text="📋 Мои задачи")],
            [KeyboardButton(text="✅ Выполнить задачу"), KeyboardButton(text="🗑 Удалить задачу")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )


def notes_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить заметку"), KeyboardButton(text="📒 Мои заметки")],
            [KeyboardButton(text="🔍 Поиск заметки"), KeyboardButton(text="🗑 Удалить заметку")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )


def schedule_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить пару"), KeyboardButton(text="📅 Показать расписание")],
            [KeyboardButton(text="🗑 Удалить пару")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )


def weekday_inline():
    builder = InlineKeyboardBuilder()
    days = [
        ("Пн", 1), ("Вт", 2), ("Ср", 3),
        ("Чт", 4), ("Пт", 5), ("Сб", 6), ("Вс", 7)
    ]
    for name, num in days:
        builder.button(text=name, callback_data=f"day:{num}")
    builder.adjust(4, 3)
    return builder.as_markup()
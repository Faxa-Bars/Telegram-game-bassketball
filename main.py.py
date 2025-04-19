# bot.py
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import random
import time

API_TOKEN = "YOUR_TOKEN_BOT"

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        score INTEGER DEFAULT 0,
        hits INTEGER DEFAULT 0,
        misses INTEGER DEFAULT 0,
        rank TEXT DEFAULT "Новичок",
        last_play REAL DEFAULT 0
    )''')
    conn.commit()
    conn.close()

def get_rank(score):
    if score >= 10000:
        return "🏆 Легенда"
    elif score >= 8000:
        return "🔥 Миф"
    elif score >= 7000:
        return "🎯 Профи"
    elif score >= 3000:
        return "⚡ Игрок"
    elif score >= 1000:
        return "💪 Любитель"
    else:
        return "👶 Новичок"

def update_user_stats(user_id, username, hit, clean_hit=False):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT score, hits, misses FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        score, hits, misses = row
        old_rank = get_rank(score)
        if hit:
            points = 100 if clean_hit else 5
            score += points
            hits += 1
        else:
            misses += 1
        new_rank = get_rank(score)
        cursor.execute(
            "UPDATE users SET username=?, score=?, hits=?, misses=?, rank=?, last_play=? WHERE user_id=?",
            (username, score, hits, misses, new_rank, time.time(), user_id)
        )
    else:
        score = 100 if clean_hit else (5 if hit else 0)
        hits = 1 if hit else 0
        misses = 0 if hit else 1
        new_rank = get_rank(score)
        cursor.execute(
            "INSERT INTO users (user_id, username, score, hits, misses, rank, last_play) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, score, hits, misses, new_rank, time.time())
        )
        old_rank = None
    conn.commit()
    conn.close()
    return old_rank, new_rank

def get_stats(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT score, hits, misses, rank FROM users WHERE user_id = ?", (user_id,))
    stats = cursor.fetchone()
    conn.close()
    return stats

def get_top_users():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, score, rank FROM users ORDER BY score DESC LIMIT 10")
    top_users = cursor.fetchall()
    conn.close()
    return top_users

def can_play(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT last_play FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return True
    last_play = row[0]
    return time.time() - last_play >= 3

def main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🏀 Играть"), KeyboardButton("📊 Статистика"))
    keyboard.add(KeyboardButton("🏆 Рейтинг"))
    return keyboard

def contact_admin_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📩 Связаться с админом", url="https://t.me/@@@@"))
    return keyboard

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        f"👋 <b>Привет, {message.from_user.first_name}!</b>\n"


        "🏀 Добро пожаловать в <b>баскетбольную игру</b>!"

        "Попробуй попасть мячом в кольцо и набирай очки, чтобы подняться в рейтинге! 🔥"


        "🎯 Чистое попадание без касания — <b>+100 очков</b>"

        "✅ Просто попадание — <b>+5 очков</b>"

        "❌ Промах — баллы не начисляются"


        "Выбирай действие ниже 👇",
        reply_markup=main_menu()
    )
    await message.answer(
        "📩 Если возникли вопросы или идеи — напиши админу!",
        reply_markup=contact_admin_keyboard()
    )

@dp.message_handler(lambda m: m.text == "📊 Статистика")
async def stats(message: types.Message):
    stats = get_stats(message.from_user.id)
    if stats:
        score, hits, misses, rank = stats
        await message.answer(
            f"📊 <b>Твоя статистика:</b>\n"

            f"🏅 Ранг: <b>{rank}</b>\n"

            f"💯 Очки: <b>{score}</b>\n"

            f"🏀 Попадания: <b>{hits}</b>\n"

            f"❌ Промахи: <b>{misses}</b>"
        )
    else:
        await message.answer("Статистика пока недоступна. Сыграй хотя бы одну игру!")

@dp.message_handler(lambda m: m.text == "🏆 Рейтинг")
async def leaderboard(message: types.Message):
    top_users = get_top_users()
    text = "🏆 <b>Топ игроков:</b>\n"


    for i, (name, score, rank) in enumerate(top_users, 1):
        text += f"{i}. {name} — {score} очков ({rank})\n"

    await message.answer(text)

@dp.message_handler(lambda m: m.text == "🏀 Играть")
async def play_game(message: types.Message):
    if not can_play(message.from_user.id):
        await message.answer("⏳ Подожди немного перед следующим броском!")
        return

    msg = await message.answer_dice(emoji="🏀")
    await asyncio.sleep(3)
    result = msg.dice.value

    clean_hit = result == 6
    hit = result >= 4

    old_rank, new_rank = update_user_stats(
        user_id=message.from_user.id,
        username=message.from_user.username or message.from_user.first_name,
        hit=hit,
        clean_hit=clean_hit
    )

    if clean_hit:
        await message.answer("🔥 Чистое попадание без касания! +100 очков! 🏀")
    elif hit:
        await message.answer("✅ Отлично! Попадание! +5 очков 🏀")
    else:
        await message.answer("❌ Увы, мимо! Попробуй ещё раз 😉")

    if new_rank != old_rank:
        await message.answer(f"🎉 Поздравляем! Ты достиг нового ранга: <b>{new_rank}</b>!")

if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)

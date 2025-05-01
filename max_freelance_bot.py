import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from datetime import datetime, timedelta
import json
import os
import openai
import random

API_TOKEN = "YOUR_TELEGRAM_BOT_API_KEY"
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

DATA_FILE = "user_data.json"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        user_data = json.load(f)
else:
    user_data = {}

SYSTEM_PROMPT = """Ты — профессиональный наставник по заработку через нейросети. Тебя зовут Макс...
(обрезан для краткости — вставить полный SYSTEM_PROMPT из исходника)"""

motivations = [
    "Ты отлично справляешься!",
    "Каждый день — шаг к цели 💪",
    "Ты на правильном пути!",
    "Вдохновляешь своим стремлением!",
    "Даже если кажется сложно — я рядом."
]

jokes = [
    "Нейросети — как спортзал: эффект появляется, если не сдаваться 😉",
    "GPT — твой интеллектуальный штангист!",
    "Midjourney не судит за вкус — и это прекрасно! 😄",
    "Заработок рядом, просто не забывай дышать (и писать мне)!"
]

class Onboarding(StatesGroup):
    waiting_for_name = State()
    waiting_for_goal = State()

def save_user_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(user_data, f)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = str(message.from_user.id)
    user_data[user_id] = {
        "last_interaction": str(datetime.utcnow()),
        "state": "onboarding",
        "message_count": 0
    }
    save_user_data()
    await message.answer("Привет! Меня зовут Макс. Я буду твоим наставником. Как мне к тебе обращаться?")
    await Onboarding.waiting_for_name.set()

@dp.message_handler(state=Onboarding.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    name = message.text.strip()
    user_data[user_id]["name"] = name
    user_data[user_id]["last_interaction"] = str(datetime.utcnow())
    save_user_data()
    await message.answer(f"Отлично, {name}! А какая твоя цель по заработку с нейросетями?")
    await Onboarding.waiting_for_goal.set()

@dp.message_handler(state=Onboarding.waiting_for_goal)
async def process_goal(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    goal = message.text.strip()
    user_data[user_id]["goal"] = goal
    user_data[user_id]["last_interaction"] = str(datetime.utcnow())
    user_data[user_id]["state"] = "active"
    save_user_data()
    await message.answer("Супер! Вместе мы придем к твоей цели. 🚀 Готов начинать?")
    await state.finish()

async def generate_response(user_id, message_text):
    name = user_data.get(user_id, {}).get("name", "друг")
    prompt = f"Имя пользователя: {name}\nСообщение пользователя: {message_text}"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message['content']

@dp.message_handler()
async def handle_message(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"message_count": 0}
    user_data[user_id]["last_interaction"] = str(datetime.utcnow())
    user_data[user_id]["message_count"] += 1
    save_user_data()

    base_reply = await generate_response(user_id, message.text)
    extra = ""

    if user_data[user_id]["message_count"] % 5 == 0:
        extra += f"\n\n{random.choice(motivations)}"
    if user_data[user_id]["message_count"] % 8 == 0:
        extra += f"\n\n{random.choice(jokes)}"

    await message.answer(base_reply + extra)

async def pause_checker():
    while True:
        now = datetime.utcnow()
        for uid, data in user_data.items():
            try:
                last = datetime.fromisoformat(data.get("last_interaction"))
                delta = now - last
                if data.get("state") == "active":
                    if timedelta(hours=2) < delta < timedelta(hours=3):
                        await bot.send_message(uid, "Привет! Я здесь, если ты готов(а) продолжить 😊")
                    elif timedelta(days=1) < delta < timedelta(days=2):
                        await bot.send_message(uid, "Ты вернулся(ась) — это главное. Двигаемся вперёд!")
            except Exception as e:
                logging.warning(f"Ошибка при проверке пользователя {uid}: {e}")
        await asyncio.sleep(3600)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(pause_checker())
    executor.start_polling(dp, skip_updates=True)

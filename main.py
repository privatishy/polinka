"""
Бот для моей любимой девушки - Полины. От Сени на годовщину! ❤️
Версия 3.0: локальная нейросеть Ollama + 33% ГС
"""

import os
import random
import datetime
import re
import pytz
import asyncio
from pathlib import Path
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode
import httpx
from dotenv import load_dotenv

# ============ ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ============
load_dotenv()

# ============ НАСТРОЙКИ ============
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
VOICES_DIR = Path("voices")
MSK_TZ = pytz.timezone("Europe/Moscow")
VOICE_PROBABILITY = 0.33  # Фиксированные 33% на голосовое
USE_NEURAL_FALLBACK = True
NEURAL_TIMEOUT = 10  # Секунд (локальная модель может быть медленнее)

# Нейросеть: Ollama (локальная)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "tinyllama:1.1b-chat-v1-q4_0")

# ============ КОНТЕКСТНАЯ ПАМЯТЬ ============
user_context = {}

# ============ ТЕКСТОВЫЕ ФРАЗЫ ============
TEXT_PHRASES = {
    "goodnight": [
        "Спокойной ночи, Полиночка любименькая. Сладеньких снов, зайка моя. Я тебя люблю очень сильно, целую и обнимаю. Пока-пока! 💋💋💋"
    ],
    "goodnight_soft": [
        "Спатеньки?",
        "Пора ложиться спать.",
        "Пойдем отдыхать, зая."
    ],
    "howareyou": [
        "Все хорошо!",
        "Отдыхаю.",
        "coding rn///"
    ],
    "why": [
        "Потому что я тебя очень сильно люблю!",
        "Потому что мне лень.",
        "Потому что я аллах!"
    ],
    "when": [
        "Обещаю сделать.",
        "Когда захочешь!",
        "..."
    ],
    "where": [
        "Дома!",
        "В кроватке.",
        "Работаю..."
    ],
    "what_doing": [
        "coding rn///",
        "no risk = no money",
        "работаем нахуй"
    ],
    "love_question": [
        "Люблю тебя больше всех!",
        "Вместе навсегда!",
        "Очень-очень сильно, зая!"
    ],
    "future_question": [
        "Все получится!",
        "Будем жить вместе!",
        "Малыши будут по дому бегать."
    ],
    "question_other": [
        "???",
        "Не знаю...",
        "Это секрет! :)"
    ],
    "laugh": [
        "Хахахах, Полина, я тебя люблю!",
        "Хахаха, извини!"
    ],
    "greeting": [
        "Привет, Полиночка! Что ты, как ты? Рассказывай.",
        "Привет, Полина. Чо там, чо там, как там у тебя дела?",
        "Даров, мабой. Мне Альфредо сказал — тебя надо щелкнуть. Ты хочешь, чтобы тебя щелкнули, мабой? Ладно, извини, Полина, я тебя люблю!"
    ],
    "love": [
        "Привет, Полина, я тебя люблю очень сильно. Это первое голосовое получается.",
        "Полина, я тебя люблю. Ты не видишь, но я тебе показываю сердечко тут маленькое.",
        "Полина, все хорошо, все супер. Ты отлично выглядишь, очень тебя люблю сильно. Очень красивая 💋",
        "Привет, Полина. Я тебя люблю очень сильно. Вот...",
        "Ой, это так мило!",
        "Полина, я тебя люблю очень-очень сильно. Ты очень хорошенькая!",
        "Полин, ты, ты очень красивая!",
        "Я тоже тебя очень сильно люблю! 💋",
        "Ты очень няшная. Ой, это так мило, Полина!",
        "Полиночка, я тебя тоже очень сильно люблю.",
        "Полиночка, я тебя люблю. Не грусти, пожалуйста, писюлька.",
        "Полина пиструнчик.",
        "Полиночка, я очень сильно тебя люблю.",
        "💋",
        "💋💋💋",
        "Полин, если бы у тебя был выбор: родиться червячком-вормисом или родиться человеком-вормисом, что бы ты выбрала?",
        "Полиночка, я тебя люблю очень сильно. Если чо, все хорошо, да, все нормально, ничо не это. Ничо-ничо.",
        "💋💋💋💋💋💋💋💋💋💋💋💋",
        "мур-мур-мур-мур-мур-мур—мяу-мяу-мяу-мяу-мяу-мяу",
        "💋",
        "муэ 👅",
        "Полиночка, я тебя люблю очень сильно, писюлинька. Хорошенькая моя — ты, Полиночка.",
        "💋",
        "💋💋💋💋💋",
        "Ты не поверишь, но я тебя тоже очень люблю сильно.",
        "Полиночка, я тебя люблю очень сильно.",
        "Я тебя тоже очень сильно люблю, Полина.",
        "Полиночка, я тебя тоже люблю очень сильно.",
        "Полиночка, я тебя люблю очень сильно, писечка.",
        "Полина, я тебя люблю.",
        "Полиночка, я тебя люблю очень сильно. Надеюсь, что у тебя все будет хорошо. Вот, я очень за тебя переживаю. Ох... Ты мне очень сильно нравишься! Все очень хорошо, все очень нравится — спасибо! 💋"
    ],
    "love_intense": [
        "Солнышко, ты у меня самая хорошенькая!",
        "Полиночка, я тебя очень сильно люблю, писюлька, муа 💋",
        "Полиночка, я тебя люблю очень сильно, писечка моя, хорошенькая такая, как шушик.",
        "Мне кажется, или мы буквально самая, типо, лучшая пара будем?"
    ],
    "love_personal": [
        "Я люблю тебя больше всех на свете!",
        "Ты - моя единственная!",
        "Давай будем вместе всегда?"
    ],
    "comfort": [
        "Все будет хорошо, Полиночка, обещаю!",
        "Люблю, целую, обнимаю!",
        "Вместе? Навсегда.",
        "Обнимаю крепко-крепко и целую сильно-сильно!",
    ],
    "tired_day": [
        "Отдыхай, малышка.",
        "Скоро будем валяться вместе!",
        "Валяйся, писюн.",
    ],
    "yes_no": [
        "дооооо",
        "седня не",
        "не знаю"
    ]
}

# ============ УМНОЕ РАСПОЗНАВАНИЕ ВОПРОСОВ ============

def is_question(text: str) -> tuple[bool, str | None]:
    """
    Точно определяет вопросы с подкатегориями, включая фразы без '?'.
    Возвращает: (является_вопросом, тип_вопроса_или_None)
    """
    text_lower = text.lower().strip()
    has_q_mark = "?" in text_lower
    
    # ===== 1. ЛОЖНЫЕ СРАБАТЫВАНИЯ (только если нет '?') =====
    false_positive_patterns = [
        r"\bкак будто\b",
        r"\bкак обычно\b",
        r"\bкак всегда\b",
        r"\bне знаю как\b",
        r"\bкак сделать\b",
        r"\bкак это работает\b",
        r"\bкак думаешь ли\b"  # утвердительный контекст
    ]
    
    is_false_positive = not has_q_mark and any(re.search(pat, text_lower) for pat in false_positive_patterns)
    
    # ===== 2. ПРИОРИТЕТНЫЕ ПАТТЕРНЫ ВОПРОСОВ (работают БЕЗ '?') =====
    # "Как дела" и синонимы — главный кейс
    if re.search(r"(^|\s)(как дела|как ты|как настроение|как жизнь|как оно|чо там|чо как|ты как|как поживаешь|как сам)($|\s|\?)", text_lower):
        if not is_false_positive:
            return True, "howareyou"
    
    # Другие вопросительные слова (даже без '?')
    q_patterns = {
        "why": r"(^|\s)(почему|зачем)($|\s|\?)",
        "when": r"(^|\s)(когда|во сколько)($|\s|\?)",
        "where": r"(^|\s)(где|куда|откуда)($|\s|\?)",
        "what_doing": r"(^|\s)(что делаешь|чем занимаешься|что ты делаешь)($|\s|\?)",
        "love_question": r"(любишь меня|ты меня любишь|меня любишь\?|мы вместе\?)",
        "future_question": r"(будем вместе|увидимся|встретимся|когда увидимся)",
        "yes_no": r"^\s*(да\?|нет\?|правда\?|точно\?|серьёзно\?|ага\?|угу\?)\s*$"
    }
    
    for q_type, pattern in q_patterns.items():
        if re.search(pattern, text_lower):
            return True, q_type
    
    # ===== 3. КОРОТКИЕ ВОПРОСЫ (1-3 слова) =====
    words = text_lower.split()
    if len(words) <= 3:
        short_q = [
            (r"^(ты как|как ты|как дела)$", "howareyou"),
            (r"^(почему|зачем|когда|где|куда)$", "question_other"),
            (r"^(да|нет|правда|ага|угу)$", "yes_no"),
            (r"^(а ты|ты тоже|сам)$", "howareyou")
        ]
        for pat, q_type in short_q:
            if re.search(pat, text_lower):
                return True, q_type
    
    # ===== 4. ОБЩИЙ ВОПРОС ПО ЗНАКУ '?' =====
    if has_q_mark:
        return True, "question_other"
    
    # ===== 5. ИНВЕРСИЯ (без '?') =====
    if re.search(r"\b(а ты|а я)\s+(хочешь|любишь|будешь|делаешь|сделаешь)\b", text_lower):
        return True, "question_other"
    
    return False, None

# ============ ПРОВЕРКА ВРЕМЕНИ СНА ============

def is_night_time() -> bool:
    """Проверяет, сейчас ли время сна Полины (23:00–04:00 МСК)"""
    now_msk = datetime.datetime.now(MSK_TZ)
    hour = now_msk.hour
    return hour >= 23 or hour < 4

# ============ УМНОЕ ОПРЕДЕЛЕНИЕ КАТЕГОРИИ ============

def detect_category(text: str, user_id: int) -> str:
    """Определяет категорию с приоритетом на вопросы и семантику"""
    text_lower = text.lower().strip()
    
    # Инициализация контекста
    if user_id not in user_context:
        user_context[user_id] = {
            "history": [],
            "last_category": None,
            "mood": "neutral",
            "mentioned_name": False
        }
    context = user_context[user_id]
    history = context["history"]
    
    # ===== 1. ПЕРВЫЙ ПРИОРИТЕТ: ВОПРОСЫ =====
    is_q, q_type = is_question(text)
    if is_q:
        # Контекстная обработка "а ты?" после вопроса о делах
        if q_type == "howareyou" and history:
            last_msg = history[-1].lower() if history else ""
            if "дела" in last_msg or "настроение" in last_msg or "как ты" in last_msg:
                return "howareyou"
        
        # Контекстная обработка "правда?" после комплимента/признания
        if q_type == "yes_no" and history:
            last_msg = history[-1].lower()
            if any(word in last_msg for word in ["люблю", "красив", "хорош", "лучш", "няшн"]):
                return "love_question"
        
        return q_type or "question_other"
    
    # ===== 2. АНАЛИЗ НАСТРОЕНИЯ =====
    if re.search(r"(грустно|плохо|тоска|печаль|не хочу|хочу плакать|грущу|одиноко)", text_lower):
        context["mood"] = "sad"
    elif re.search(r"(устал[ао]|вымотал[ао]сь|задолбало|надоело|энергии нет|спать хочу)", text_lower):
        context["mood"] = "tired"
    elif re.search(r"(отлично|супер|радость|круто|хорошо|люблю|счастлив[ао]|ура|класс)", text_lower):
        context["mood"] = "happy"
    
    # ===== 3. СЕМАНТИЧЕСКИЕ ФРАЗЫ (ТОЧНЫЙ АНАЛИЗ) =====
    
    # Спокойной ночи — всегда приоритет
    if re.search(r"(спокойной ночи|споки|спокойненьких|спокойняшка|спасть\s+пора|спокойного|спи сладко)", text_lower):
        return "goodnight"
    
    # Хочу спать / устала — с учётом времени сна!
    if re.search(r"(хочу спать|пора спать|надо спать|ложиться спать|засыпаю|сонная|спать хочу|глаза слипаются)", text_lower):
        return "goodnight" if is_night_time() else "goodnight_soft"
    
    if re.search(r"(устал[ао]|вымотал[ао]сь|задолбало|надоело)", text_lower):
        return "goodnight" if is_night_time() else "tired_day"
    
    # Смех
    if re.search(r"(хаха|ахаха|смешно|ржу|смеюсь|😂|🤣|лол|кек|рофл|ахах|хи-хи)", text_lower):
        return "laugh"
    
    # Приветствия
    if re.search(r"(привет|здравствуй|хай|йоу|даров|прив|хеллоу|ку|здарова|приветик|здравствуйте)", text_lower):
        return "greeting"
    
    # Упоминание имени/ласковых
    if re.search(r"(полин[а-я]*|полюш|полюсик|писюл|писечк|шушик|зайк[ау]|любим[а-я]*|солнышко|малышк[ау])", text_lower):
        context["mentioned_name"] = True
        return "love_personal"
    
    # Эмоциональное эхо "люблю"
    if "люблю" in text_lower:
        if history and any("люблю" in msg.lower() for msg in history[-2:]):
            return "love_intense"
        return "love"
    
    # ===== 4. КОРОТКИЕ ОТВЕТЫ С КОНТЕКСТОМ =====
    if history and len(text_lower.split()) <= 3:
        last_category = context.get("last_category")
        if last_category == "goodnight" and re.search(r"(ты\?|а ты|сам[а]?|тоже|и я)", text_lower):
            return "goodnight"
        if last_category in ["howareyou", "greeting"] and re.search(r"(а ты\?|ты как|сам[а]?)", text_lower):
            return "howareyou"
    
    # ===== 5. ФОЛБЭК ПО НАСТРОЕНИЮ =====
    if context["mood"] == "sad":
        return "comfort"
    if context["mood"] == "tired" and not is_night_time():
        return "tired_day"
    
    return "unknown"

# ============ ВЫБОР ГОЛОСОВОГО ============

def get_voice_files(category: str) -> list:
    """Возвращает голосовые с точным соответствием категории"""
    if not VOICES_DIR.exists():
        return []
    
    all_files = sorted(list(VOICES_DIR.glob("*.ogg")) + list(VOICES_DIR.glob("*.oga")))
    
    category_map = {
        "goodnight": ["01_", "goodnight", "спокойной", "ноч", "спат", "спи", "сон", "споки"],
        "goodnight_soft": ["спать", "устал", "сон", "засыпа", "спат", "отдых", "спатеньки"],
        "tired_day": ["устал", "отдых", "энергия", "выдох", "валяйся"],
        "howareyou": ["дела", "как ты", "настроение", "ты как"],
        "why": ["почему", "зачем"],
        "when": ["когда", "во сколько"],
        "where": ["где", "куда"],
        "what_doing": ["делаешь", "занимаешься"],
        "love_question": ["люблю", "любишь", "вместе"],
        "future_question": ["будем", "встретимся", "увидимся"],
        "yes_no": ["да", "нет", "правда"],
        "question_other": ["вопрос", "почему", "зачем", "когда", "где"],
        "laugh": ["02_", "laugh", "смех", "хаха", "ахах", "смеш"],
        "greeting": ["03_", "greet", "hello", "привет", "даров", "хай"],
        "love_intense": ["intense", "сильн", "очень", "тысяч", "сильнее", "бесконеч", "бесконечно"],
        "love_personal": ["personal", "полин", "имя", "писюл", "шушик", "зайка", "солнышко"],
        "comfort": ["comfort", "груст", "обнима", "поддерж", "лучше", "плак", "не грусти"]
    }
    
    keywords = category_map.get(category, [])
    if keywords:
        candidates = [
            f for f in all_files
            if any(kw in f.name.lower() for kw in keywords)
            and not f.name.startswith("00_")
        ]
        if candidates:
            return candidates
    
    # Для вопросов — НЕ используем случайные любовные голосовые (только релевантные)
    if category in ["howareyou", "question_other", "why", "when", "where"]:
        question_voices = [f for f in all_files if any(kw in f.name.lower() for kw in ["дела", "как ты", "почему", "когда", "где"])]
        return question_voices if question_voices else []
    
    # Для усталости днём — мягкие голосовые
    if category == "tired_day":
        soft_candidates = [f for f in all_files if any(kw in f.name.lower() for kw in ["soft", "тихо", "нежн", "обнима", "отдых"])]
        return soft_candidates if soft_candidates else []
    
    # Фолбэк: общие любовные голосовые
    return [
        f for f in all_files
        if not any(prefix in f.name.lower() for prefix in ["00_", "01_", "02_", "03_"])
        and "first" not in f.name.lower()
        and "goodnight" not in f.name.lower()
        and "laugh" not in f.name.lower()
        and "greet" not in f.name.lower()
    ]

# ============ НЕЙРОСЕТЬ: ГЕНЕРАЦИЯ ОТВЕТА ЧЕРЕЗ OLLAMA ============

async def generate_neural_response(user_message: str, category: str, user_id: int) -> str | None:
    """Генерирует ответ через локальную модель Ollama с обучением на шаблонах"""
    if not USE_NEURAL_FALLBACK:
        return None
    
    # Получаем примеры из нужной категории + общие любовные фразы для стиля
    category_examples = TEXT_PHRASES.get(category, [])
    love_examples = TEXT_PHRASES["love"][:4]
    
    # Формируем промпт с примерами в стиле "few-shot learning"
        # === ИСПРАВЛЕННЫЙ ПРОМПТ ДЛЯ tinyllama / большинства простых моделей ===
        # Примеры для стиля
    examples = []
    for ex in (TEXT_PHRASES.get(category, [])[:2] + TEXT_PHRASES["love"][:2]):
        examples.append(f"Полина: ...\nСеня: {ex}")
    
    examples_text = "\n".join(examples)
    
    # История диалога
    history_lines = []
    for msg in user_context.get(user_id, {}).get("history", [])[-2:]:
        history_lines.append(f"Полина: {msg}")
    history_str = "\n".join(history_lines) if history_lines else "Полина: Привет!"
    
    # ЧИСТЫЙ ПРОМПТ БЕЗ ТЕГОВ
    prompt = (
        f"Ты — Сеня, парень Полины. Ты всегда отвечаешь коротко (1-3 предложения), максимум 75 символов, "
        f"ласково, на русском языке! Если что, можешь ориентироваться на примеры.\n\n"
        f"Примеры:\n{examples_text}\n\n"
        f"Диалог:\n{history_str}\nПолина: {user_message}\nСеня:"
    )
    
    try:
        async with httpx.AsyncClient(timeout=NEURAL_TIMEOUT) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 60,
                        "stop": ["\n", "Полина:", "<|"]
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("response", "").strip()
                
                # Очищаем ответ
                answer = re.sub(r'^Сеня[:\-\s]*', '', answer, flags=re.IGNORECASE)
                answer = re.sub(r'^["\'*#]+|["\'*#]+$', '', answer)
                answer = ' '.join(answer.split())[:120]
                
                # === НОВЫЕ ПРОВЕРКИ: ОТКЛОНЕНИЕ ПЛОХИХ ОТВЕТОВ ===
                # Отклонять ответы на других языках (нет русских букв)
                if answer and not re.search(r'[а-яА-Я]', answer):
                    print(f"❌ Ответ не на русском: {answer[:50]}...")
                    return None

                # Отклонять ответы с иностранными именами/приветствиями
                if answer and re.search(r'(Seyna|Señora|Hey|Hello|Dear|Hi\b)', answer, re.IGNORECASE):
                    print(f"❌ Иностранное имя/приветствие: {answer[:50]}...")
                    return None

                # Отклонять слишком короткие или странные ответы
                if not answer or len(answer) < 8 or answer.count(' ') < 1:
                    print(f"❌ Слишком короткий/странный ответ: '{answer}'")
                    return None
                # ================================================

                # Добавляем эмодзи для стиля
                if answer and "💋" not in answer and "❤️" not in answer and random.random() < 0.6:
                    answer += " 💋"
                
                return answer if answer else None
            else:
                print(f"⚠️ Ollama error {response.status_code}: {response.text[:100]}")
                return None
                
    except Exception as e:
        print(f"⚠️ Ollama generation failed: {str(e)[:100]}")
        return None

# ============ ОБРАБОТЧИКИ ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    first_voice = VOICES_DIR / "00_first.ogg"
    
    if first_voice.exists():
        with open(first_voice, "rb") as f:
            await update.message.reply_voice(voice=f)
        await update.message.reply_text(
            "<b><tg-emoji emoji-id='5202087689112790102'>❤️</tg-emoji> Полиночка, это мое первое голосовое, отправленное тебе.</b>\n"
            "<b>Пиши мне когда угодно и что угодно, я всегда отвечу! <tg-emoji emoji-id='5402288583069408773'>💕</tg-emoji></b>",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            "⚠️ Файл 00_first.ogg не найден в папке voices/\n"
            "Положи первое голосовое с именем 00_first.ogg"
        )

async def reply_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    user_text = (update.message.text or "").strip()
    
    if not user_text:
        return
    
    # Инициализация контекста
    if user_id not in user_context:
        user_context[user_id] = {
            "history": [],
            "last_category": None,
            "mood": "neutral",
            "mentioned_name": False
        }
    
    # Обновление истории
    user_context[user_id]["history"].append(user_text)
    if len(user_context[user_id]["history"]) > 3:
        user_context[user_id]["history"].pop(0)
    
    # Определение категории
    # Определение категории
    category = detect_category(user_text, user_id)
    user_context[user_id]["last_category"] = category

    # Если категория unknown — всегда использовать нейросеть
    if category == "unknown":
        neural_response = await generate_neural_response(user_text, "question_other", user_id)
        if neural_response:
            await update.message.reply_text(f"<b>{neural_response}</b>", parse_mode=ParseMode.HTML)
            print(f"🤖 Neural (unknown): {neural_response[:50]}...")
            return
        else:
            # Если нейросеть не ответила — дать нейтральный ответ
            await update.message.reply_text(
                "<b>Хм... не знаю, что сказать. Но я тебя люблю! ❤️</b>",
                parse_mode=ParseMode.HTML
            )
            return
    
    # === КРИТИЧЕСКАЯ ПРОВЕРКА: является ли категория РЕЛЕВАНТНОЙ? ===
    # Считаем категорию "любовной" (любая из подкатегорий) НЕРЕЛЕВАНТНОЙ фолбэком, если:
    # 1. В сообщении пользователя нет любовной/аффективной семантики
    # 2. И это не вопрос про любовь/отношения
    love_categories = ["love", "love_intense", "love_personal", "comfort"]
    has_love_semantics = bool(re.search(
        r"(люблю|обожаю|обнимаю|целую|скучаю|лучш|красив|хорош|мил|няш|солнышко|зайк|писюл|полин|ушк|русин|очк|❤️|💋|💕|обожа|безумно|страстно)",
        user_text.lower()
    ))
    is_actual_question, q_type = is_question(user_text)
    is_love_question = q_type in ["love_question", "future_question"]
    
    # Категория считается НЕРЕЛЕВАНТНЫМ ФОЛБЭКОМ если:
    # - это любовная категория БЕЗ любовной семантики в сообщении И НЕ вопрос про любовь
    
    # === ПРОВЕРКА НАЛИЧИЯ ШАБЛОНОВ ===
    has_text_template = category in TEXT_PHRASES and TEXT_PHRASES[category]
    has_voice_template = bool(get_voice_files(category))
    
    # === РЕШЕНИЕ: использовать нейросеть ЕСЛИ ===
    # 1. Категория — нерелевантный фолбэк на любовь ИЛИ
    # 2. Нет текстовых шаблонов для категории ИЛИ
    # 3. Это вопрос без точной классификации и без шаблонов
    use_neural = False
    neural_response = None
    
    # === ШАГ 3: Выбор формата ответа (фиксированные 33% ГС) ===
    use_voice = random.random() < VOICE_PROBABILITY
    
    # Отладка
    print(f"\n📥 [{datetime.datetime.now(MSK_TZ).strftime('%H:%M:%S')}] '{user_text[:40]}'")
    print(f"🧠 Категория: {category:15s} | Фолбэк: {str("unknown"):5s} | Нейросеть: {str(use_neural):5s} | ГС: {str(use_voice):5s}")
    
    try:
        if use_neural:
            # Отправляем нейросетевой ответ (только текст)
            await update.message.reply_text(
                f"<b>{neural_response}</b>",
                parse_mode=ParseMode.HTML
            )
            print(f"🤖 Neural: {neural_response[:50]}...")
            
        elif use_voice and has_voice_template:
            # Отправляем голосовое из шаблона
            candidates = get_voice_files(category)
            if candidates:
                voice_path = random.choice(candidates)
                with open(voice_path, "rb") as f:
                    await update.message.reply_voice(voice=f)
                print(f"🎤 Voice: {voice_path.name}")
            else:
                # Фолбэк на текст
                phrase = random.choice(TEXT_PHRASES.get(category, TEXT_PHRASES["love"]))
                await update.message.reply_text(phrase, parse_mode=ParseMode.HTML)
                print(f"💬 Fallback text")
                
        else:
            # Отправляем текстовый шаблон
            phrase = random.choice(TEXT_PHRASES.get(category, TEXT_PHRASES["love"]))
            await update.message.reply_text(phrase, parse_mode=ParseMode.HTML)
            print(f"💬 Text: {phrase[:50]}...")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await update.message.reply_text(
            "<b>Что-то пошло не так, но я всё равно тебя люблю! ❤️</b>",
            parse_mode=ParseMode.HTML
        )

# ============ ЗАПУСК ============

def main():
    # Проверка токена
    if not BOT_TOKEN:
        print("❌ ОШИБКА: BOT_TOKEN не задан в .env файле!")
        print("\nСоздайте файл .env с содержимым:")
        print("BOT_TOKEN=ваш_токен_от_@BotFather")
        print("\nКак получить токен:")
        print("1. Напишите @BotFather в Telegram")
        print("2. Отправьте команду /newbot")
        print("3. Следуйте инструкциям и скопируйте токен")
        exit(1)
    
    # Проверка папки с голосовыми
    if not VOICES_DIR.exists():
        print(f"⚠️ Папка {VOICES_DIR} не найдена. Создаём...")
        VOICES_DIR.mkdir(exist_ok=True)
    
    # Проверка Ollama
    try:
        import httpx
        response = httpx.get(f"{OLLAMA_URL}/api/version", timeout=3)
        if response.status_code == 200:
            print(f"✅ Ollama доступен: {response.json().get('version', 'unknown')}")
        else:
            print(f"⚠️ Ollama вернул статус {response.status_code}")
    except Exception as e:
        print(f"⚠️ Не удалось подключиться к Ollama: {e}")
        print(f"   URL: {OLLAMA_URL}")
        print(f"   Убедитесь, что Ollama запущен: 'ollama serve'")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_random))
    
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  ✅ Бот «Полиночка от Сени» запущен! ❤️                 ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  🎤 Голосовые: {VOICE_PROBABILITY*100:.0f}%")
    print(f"║  🤖 Нейросеть: {'✓ активна (локальная)' if USE_NEURAL_FALLBACK else 'отключена'}")
    print(f"║  🧠 Модель: {OLLAMA_MODEL}")
    print("╚══════════════════════════════════════════════════════════╝")
    print("\n💡 Логи показывают категорию и тип ответа в реальном времени")
    app.run_polling()

if __name__ == "__main__":
    main()


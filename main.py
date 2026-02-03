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

async def generate_neural_response(user_message: str, category: str, user_id: int, attempt: int = 1) -> str | None:
    """Генерирует ответ через Ollama с защитой от отказных ответов. Поддерживает 2 попытки."""
    if not USE_NEURAL_FALLBACK:
        return None

    # === ИСТОРИЯ ДИАЛОГА (последние 2 сообщения Полины) ===
    context = user_context.get(user_id, {"history": []})
    history = context["history"][-2:]
    
    # Формируем историю в формате диалога
    history_lines = []
    for msg in history:
        history_lines.append(f"Полина: {msg}")
        # Добавляем пример ответа Сени для контекста
        history_lines.append("Сеня: Люблю тебя, зайка 💋")
    
    history_str = "\n".join(history_lines) if history_lines else "Полина: Привет"

    # === МОЩНЫЙ ПРОМПТ В ФОРМАТЕ, ПОНЯТНОМ TINYLLAMA/QWEN ===
    # Tinyllama НЕ понимает сложные системные инструкции — только примеры диалога!
    prompt = (
        "Полина: Привет\n"
        "Сеня: Привет, Полиночка! Что ты, как ты? Рассказывай 💋\n"
        "Полина: Как дела?\n"
        "Сеня: Всё хорошо, зайка! Скучаю по тебе ❤️\n"
        "Полина: Я устала\n"
        "Сеня: Отдыхай, малышка. Я тебя люблю 💕\n"
        "Полина: Ты меня любишь?\n"
        "Сеня: Больше всех на свете! 💋💋💋\n"
        f"{history_str}\n"
        f"Полина: {user_message}\n"
        "Сеня:"
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
                        "temperature": 0.9,   # Выше для креативности
                        "top_p": 0.95,
                        "num_predict": 60,    # Хватит на 1-2 предложения
                        "stop": ["\n", "Полина:", "Сеня:", "<|", "###", "—", ":", "?", "!"]
                    }
                }
            )
            
            if response.status_code != 200:
                print(f"⚠️ Ollama error {response.status_code}")
                return None

            data = response.json()
            raw_answer = data.get("response", "").strip()
            
            # === ОЧИСТКА ОТВЕТА ===
            answer = re.sub(r'^(Сеня|Я)[:\-\s]*', '', raw_answer, flags=re.IGNORECASE)
            answer = re.sub(r'^["\'*#\s]+|["\'*#\s]+$', '', answer)
            answer = ' '.join(answer.split())[:120].strip(".,!?;: ")

            # === АГРЕССИВНАЯ ФИЛЬТРАЦИЯ ОТКАЗНЫХ ОТВЕТОВ ===
            bad_patterns = [
                r'извини(те)?\b',
                r'не (могу|умею|знаю|понимаю|вижу)',
                r'недоступно',
                r'отказываюсь',
                r'я (— )?ассистент',
                r'я (— )?искусственный интеллект',
                r'я (— )?нейросеть',
                r'я не (Сеня|парень)',
                r'пользователь',
                r'запрещено',
                r'нельзя',
                r'только текст',
                r'английском',
                r'русском языке',  # Модель часто упоминает это при отказе
                r'^[А-Я][а-я]{0,3}$',  # Одно слово с большой буквы (часто "Да", "Нет" — плохой ответ)
                r'^\.{2,}$'  # Многоточие
            ]
            
            if not answer or len(answer) < 5:
                print(f"❌ Попытка {attempt}: пустой/короткий ответ")
                return await _retry_or_fallback(user_message, category, user_id, attempt)
            
            if re.search(r'[a-zA-Z]{4,}', answer) and not re.search(r'[а-яА-Я]{3,}', answer):
                print(f"❌ Попытка {attempt}: ответ не на русском")
                return await _retry_or_fallback(user_message, category, user_id, attempt)
            
            for pattern in bad_patterns:
                if re.search(pattern, answer, re.IGNORECASE):
                    print(f"❌ Попытка {attempt}: отклонён по паттерну '{pattern}' → '{answer[:40]}'")
                    return await _retry_or_fallback(user_message, category, user_id, attempt)
            
            # === ДОБАВЛЕНИЕ ЭМОДЗИ (если нет) ===
            if answer and not re.search(r'[💋❤️💕🥰😘]', answer) and random.random() < 0.7:
                emoji = random.choice(["💋", "❤️", "💕", "💋💋"])
                answer = f"{answer.rstrip('.!?)}] ')} {emoji}".strip()
            
            # Финальная проверка на осмысленность
            if len(answer.split()) < 2 or answer.count(' ') == 0:
                print(f"❌ Попытка {attempt}: бессмысленный ответ '{answer}'")
                return await _retry_or_fallback(user_message, category, user_id, attempt)
            
            print(f"✅ Нейросеть (попытка {attempt}): '{answer}'")
            return answer
            
    except Exception as e:
        print(f"⚠️ Ollama failed (попытка {attempt}): {str(e)[:100]}")
        return await _retry_or_fallback(user_message, category, user_id, attempt)

async def _retry_or_fallback(user_message: str, category: str, user_id: int, attempt: int) -> str | None:
    """Повторная генерация (макс. 2 попытки) или фолбэк на шаблоны"""
    if attempt < 2:
        print(f"🔄 Повторная генерация (попытка {attempt + 1})...")
        return await generate_neural_response(user_message, category, user_id, attempt + 1)
    
    # Фолбэк на шаблоны после 2 неудачных попыток
    print(f"⚠️ Нейросеть не ответила после 2 попыток. Фолбэк на шаблоны.")
    fallback_category = category if category in TEXT_PHRASES and TEXT_PHRASES[category] else "love"
    phrase = random.choice(TEXT_PHRASES[fallback_category])
    return f"<b>{phrase}</b>"

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
    
    category = detect_category(user_text, user_id)
    user_context[user_id]["last_category"] = category

    # === НЕЙРОСЕТЬ КАК ОСНОВНОЙ ГЕНЕРАТОР ===
    # Используем нейросеть ВСЕГДА, кроме явных кейсов (спокойной ночи, смех)
    force_template_categories = ["goodnight", "laugh", "greeting"]
    use_neural = category not in force_template_categories
    
    neural_response = None
    if use_neural:
        neural_response = await generate_neural_response(user_text, category, user_id)
    
    # === ВЫБОР ФОРМАТА ОТВЕТА ===
    use_voice = random.random() < VOICE_PROBABILITY
    
    print(f"\n📥 [{datetime.datetime.now(MSK_TZ).strftime('%H:%M:%S')}] '{user_text[:40]}'")
    print(f"🧠 Категория: {category:15s} | Нейросеть: {str(bool(neural_response)):5s} | ГС: {str(use_voice):5s}")
    
    try:
        if neural_response and not neural_response.startswith("<b>"):  # Не шаблонный фолбэк
            # Отправляем чистый нейросетевой ответ
            await update.message.reply_text(
                f"<b>{neural_response}</b>",
                parse_mode=ParseMode.HTML
            )
            print(f"🤖 Neural: {neural_response[:60]}...")
            
        elif use_voice:
            # Голосовое из шаблонов
            candidates = get_voice_files(category)
            if candidates:
                voice_path = random.choice(candidates)
                with open(voice_path, "rb") as f:
                    await update.message.reply_voice(voice=f)
                print(f"🎤 Voice: {voice_path.name}")
            else:
                # Фолбэк на текст
                phrase = random.choice(TEXT_PHRASES.get(category, TEXT_PHRASES["love"]))
                await update.message.reply_text(f"<b>{phrase}</b>", parse_mode=ParseMode.HTML)
                
        else:
            # Текстовый шаблон
            phrase = random.choice(TEXT_PHRASES.get(category, TEXT_PHRASES["love"]))
            await update.message.reply_text(f"<b>{phrase}</b>", parse_mode=ParseMode.HTML)
            print(f"💬 Text: {phrase[:60]}...")

    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        await update.message.reply_text(
            "<b>💋💋💋</b>",
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

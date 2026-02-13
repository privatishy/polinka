"""
Бот для моей любимой девушки - Полины. От Сени на годовщину! ❤️
Версия 4.0: обучение с подкреплением (лайк/дизлайк) + 33% ГС
✅ Исправлено: защита от двойного запуска + стабильные эмодзи-кнопки
"""

# ============ ЗАЩИТА ОТ ДВОЙНОГО ЗАПУСКА (КРИТИЧЕСКИ ВАЖНО) ============
import fcntl
import sys
import os

def single_instance_lock():
    """Гарантирует, что запущен только один экземпляр бота"""
    lock_path = "/tmp/polina_bot_v4.lock"
    try:
        lock_file = open(lock_path, "w")
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Сохраняем дескриптор в глобальную переменную, чтобы не закрылся
        globals()["_BOT_LOCK_FILE"] = lock_file
        print(f"✅ Единственный экземпляр бота запущен (блокировка: {lock_path})")
        return True
    except BlockingIOError:
        print(f"❌ ОШИБКА: Бот уже запущен! (блокировка: {lock_path})")
        print("   Остановите текущий экземпляр: sudo systemctl stop polina-bot")
        sys.exit(1)

# СРАЗУ ВЫЗЫВАЕМ ПРИ СТАРТЕ СКРИПТА
single_instance_lock()

# ============ СТАНДАРТНЫЕ ИМПОРТЫ ============
import os
import random
import datetime
import re
import pytz
import sqlite3
import hashlib
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode
from dotenv import load_dotenv

# ============ ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ============
load_dotenv()

# ============ НАСТРОЙКИ ============
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
VOICES_DIR = Path("voices")
DB_PATH = Path("polina_rl.db")
MSK_TZ = pytz.timezone("Europe/Moscow")
VOICE_PROBABILITY = 0.33  # Фиксированные 33% на голосовое
EXPLORATION_RATE = 0.2    # 20% шанс случайного выбора для исследования

# ============ ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ============
def init_db():
    """Создает таблицы БД при первом запуске"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            context_hash TEXT NOT NULL,
            category TEXT NOT NULL,
            response_type TEXT NOT NULL CHECK(response_type IN ('text', 'voice')),
            response_id TEXT NOT NULL,
            rating INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(context_hash, response_type, response_id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_context ON responses(context_hash, response_type)')
    conn.commit()
    conn.close()
    print(f"✅ База данных инициализирована: {DB_PATH}")

def get_rating(context_hash: str, response_type: str, response_id: str) -> int:
    """Получает текущий рейтинг ответа"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT rating FROM responses WHERE context_hash = ? AND response_type = ? AND response_id = ?',
            (context_hash, response_type, response_id)
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception as e:
        print(f"⚠️ Ошибка БД (get_rating): {e}")
        return 0

def ensure_response_exists(context_hash: str, category: str, response_type: str, response_id: str):
    """Создает запись в БД, если её нет"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT OR IGNORE INTO responses 
               (context_hash, category, response_type, response_id, rating) 
               VALUES (?, ?, ?, ?, 0)''',
            (context_hash, category, response_type, response_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Ошибка БД (ensure_response): {e}")

def update_rating(context_hash: str, response_type: str, response_id: str, delta: int):
    """Обновляет рейтинг ответа (+1 или -5)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT OR IGNORE INTO responses 
               (context_hash, category, response_type, response_id, rating) 
               VALUES (?, ?, ?, ?, 0)''',
            (context_hash, "unknown", response_type, response_id)
        )
        cursor.execute(
            '''UPDATE responses 
               SET rating = rating + ? 
               WHERE context_hash = ? AND response_type = ? AND response_id = ?''',
            (delta, context_hash, response_type, response_id)
        )
        conn.commit()
        conn.close()
        print(f"📊 Рейтинг обновлён: {response_id} ({response_type}) {delta:+d}")
    except Exception as e:
        print(f"⚠️ Ошибка БД (update_rating): {e}")

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
        "Полиночка, я тебя люблю очень-очень сильно. Ты очень хорошенькая!",
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
    text_lower = text.lower().strip()
    has_q_mark = "?" in text_lower
    
    false_positive_patterns = [
        r"\bкак будто\b",
        r"\bкак обычно\b",
        r"\bкак всегда\b",
        r"\bне знаю как\b",
        r"\bкак сделать\b",
        r"\bкак это работает\b",
        r"\bкак думаешь ли\b"
    ]
    
    is_false_positive = not has_q_mark and any(re.search(pat, text_lower) for pat in false_positive_patterns)
    
    if re.search(r"(^|\s)(как дела|как ты|как настроение|как жизнь|как оно|чо там|чо как|ты как|как поживаешь|как сам)($|\s|\?)", text_lower):
        if not is_false_positive:
            return True, "howareyou"
    
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
    
    if has_q_mark:
        return True, "question_other"
    
    if re.search(r"\b(а ты|а я)\s+(хочешь|любишь|будешь|делаешь|сделаешь)\b", text_lower):
        return True, "question_other"
    
    return False, None

# ============ ПРОВЕРКА ВРЕМЕНИ СНА ============
def is_night_time() -> bool:
    now_msk = datetime.datetime.now(MSK_TZ)
    hour = now_msk.hour
    return hour >= 23 or hour < 4

# ============ УМНОЕ ОПРЕДЕЛЕНИЕ КАТЕГОРИИ ============
def detect_category(text: str, user_id: int) -> str:
    text_lower = text.lower().strip()
    
    if user_id not in user_context:
        user_context[user_id] = {
            "history": [],
            "last_category": None,
            "mood": "neutral",
            "mentioned_name": False
        }
    context = user_context[user_id]
    history = context["history"]
    
    is_q, q_type = is_question(text)
    if is_q:
        if q_type == "howareyou" and history:
            last_msg = history[-1].lower() if history else ""
            if "дела" in last_msg or "настроение" in last_msg or "как ты" in last_msg:
                return "howareyou"
        
        if q_type == "yes_no" and history:
            last_msg = history[-1].lower()
            if any(word in last_msg for word in ["люблю", "красив", "хорош", "лучш", "няшн"]):
                return "love_question"
        
        return q_type or "question_other"
    
    if re.search(r"(грустно|плохо|тоска|печаль|не хочу|хочу плакать|грущу|одиноко)", text_lower):
        context["mood"] = "sad"
    elif re.search(r"(устал[ао]|вымотал[ао]сь|задолбало|надоело|энергии нет|спать хочу)", text_lower):
        context["mood"] = "tired"
    elif re.search(r"(отлично|супер|радость|круто|хорошо|люблю|счастлив[ао]|ура|класс)", text_lower):
        context["mood"] = "happy"
    
    if re.search(r"(спокойной ночи|споки|спокойненьких|спокойняшка|спасть\s+пора|спокойного|спи сладко)", text_lower):
        return "goodnight"
    
    if re.search(r"(хочу спать|пора спать|надо спать|ложиться спать|засыпаю|сонная|спать хочу|глаза слипаются)", text_lower):
        return "goodnight" if is_night_time() else "goodnight_soft"
    
    if re.search(r"(устал[ао]|вымотал[ао]сь|задолбало|надоело)", text_lower):
        return "goodnight" if is_night_time() else "tired_day"
    
    if re.search(r"(хаха|ахаха|смешно|ржу|смеюсь|😂|🤣|лол|кек|рофл|ахах|хи-хи)", text_lower):
        return "laugh"
    
    if re.search(r"(привет|здравствуй|хай|йоу|даров|прив|хеллоу|ку|здарова|приветик|здравствуйте)", text_lower):
        return "greeting"
    
    if re.search(r"(полин[а-я]*|полюш|полюсик|писюл|писечк|шушик|зайк[ау]|любим[а-я]*|солнышко|малышк[ау])", text_lower):
        context["mentioned_name"] = True
        return "love_personal"
    
    if "люблю" in text_lower:
        if history and any("люблю" in msg.lower() for msg in history[-2:]):
            return "love_intense"
        return "love"
    
    if history and len(text_lower.split()) <= 3:
        last_category = context.get("last_category")
        if last_category == "goodnight" and re.search(r"(ты\?|а ты|сам[а]?|тоже|и я)", text_lower):
            return "goodnight"
        if last_category in ["howareyou", "greeting"] and re.search(r"(а ты\?|ты как|сам[а]?)", text_lower):
            return "howareyou"
    
    if context["mood"] == "sad":
        return "comfort"
    if context["mood"] == "tired" and not is_night_time():
        return "tired_day"
    
    return "unknown"

# ============ ВЫБОР ГОЛОСОВОГО ============
def get_voice_files(category: str) -> list:
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
    
    if category in ["howareyou", "question_other", "why", "when", "where"]:
        question_voices = [f for f in all_files if any(kw in f.name.lower() for kw in ["дела", "как ты", "почему", "когда", "где"])]
        return question_voices if question_voices else []
    
    if category == "tired_day":
        soft_candidates = [f for f in all_files if any(kw in f.name.lower() for kw in ["soft", "тихо", "нежн", "обнима", "отдых"])]
        return soft_candidates if soft_candidates else []
    
    return [
        f for f in all_files
        if not any(prefix in f.name.lower() for prefix in ["00_", "01_", "02_", "03_"])
        and "first" not in f.name.lower()
        and "goodnight" not in f.name.lower()
        and "laugh" not in f.name.lower()
        and "greet" not in f.name.lower()
    ]

# ============ ВЫБОР ОТВЕТА С УЧЁТОМ РЕЙТИНГА ============
def choose_best_candidate(context_hash: str, category: str, candidates: list, response_type: str):
    if not candidates:
        return None, None
    
    rated_candidates = []
    for cand in candidates:
        if response_type == 'text':
            response_id = hashlib.md5(cand[:50].encode()).hexdigest()[:8]
        else:
            response_id = cand.stem[:20]
        
        rating = get_rating(context_hash, response_type, response_id)
        rated_candidates.append((cand, rating, response_id))
    
    if random.random() < EXPLORATION_RATE:
        chosen = random.choice(rated_candidates)
        print(f"🎲 Исследование: случайный выбор (рейтинги: {[r[1] for r in rated_candidates]})")
        return chosen[0], chosen[2]
    
    max_rating = max(r[1] for r in rated_candidates)
    best_candidates = [r for r in rated_candidates if r[1] == max_rating]
    chosen = random.choice(best_candidates)
    
    print(f"🧠 Эксплуатация: выбор по рейтингу (макс: {max_rating}, кандидатов: {len(best_candidates)})")
    return chosen[0], chosen[2]

# ============ ОБРАБОТЧИКИ ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    first_voice = VOICES_DIR / "00_first.ogg"
    
    if first_voice.exists():
        with open(first_voice, "rb") as f:
            await update.message.reply_voice(voice=f)
        await update.message.reply_text(
            "<b><tg-emoji emoji-id='5202087689112790102'>❤️</tg-emoji> Полиночка, это мое первое голосовое, отправленное тебе.</b>\n"
            "<b>Пиши мне когда угодно и что угодно, я всегда отвечу! <tg-emoji emoji-id='5402288583069408773'>💕</tg-emoji></b>\n\n"
            "<i>Теперь я учусь на твоих реакциях! Ставь 💚 если ответ понравился или 💔 если нет — я стану лучше для тебя ❤️</i>",
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
    
    if user_id not in user_context:
        user_context[user_id] = {
            "history": [],
            "last_category": None,
            "mood": "neutral",
            "mentioned_name": False
        }
    
    user_context[user_id]["history"].append(user_text)
    if len(user_context[user_id]["history"]) > 3:
        user_context[user_id]["history"].pop(0)
    
    history = user_context[user_id]["history"]
    context_string = " || ".join(history[-2:]) if len(history) >= 2 else (history[0] if history else user_text)
    context_hash = hashlib.md5(context_string.encode()).hexdigest()[:6]
    
    category = detect_category(user_text, user_id)
    user_context[user_id]["last_category"] = category

    use_voice = random.random() < VOICE_PROBABILITY
    has_voice_template = bool(get_voice_files(category))
    
    print(f"\n📥 [{datetime.datetime.now(MSK_TZ).strftime('%H:%M:%S')}] '{user_text[:40]}'")
    print(f"🧠 Категория: {category:15s} | Контекст: {context_hash}")
    
    try:
        if use_voice and has_voice_template:
            voice_candidates = get_voice_files(category)
            chosen_voice, response_id = choose_best_candidate(context_hash, category, voice_candidates, 'voice')
            
            if chosen_voice:
                short_resp_id = response_id[:6]
                callback_like = f"r:1:{context_hash}v{short_resp_id}"
                callback_dislike = f"r:0:{context_hash}v{short_resp_id}"
                
                # ✅ ЦВЕТНЫЕ КНОПКИ ЧЕРЕЗ api_kwargs (Bot API 9.4)
                keyboard = [[
                    InlineKeyboardButton(
                        text="💚",
                        callback_data=callback_like,
                        api_kwargs={"style": "success"}
                    ),
                    InlineKeyboardButton(
                        text="🤍",
                        callback_data=callback_dislike,
                        api_kwargs={"style": "primary"}
                    )
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                with open(chosen_voice, "rb") as f:
                    await update.message.reply_voice(voice=f, reply_markup=reply_markup)
                
                ensure_response_exists(context_hash, category, 'voice', response_id)
                print(f"🎤 Voice: {chosen_voice.name} (ID: {response_id})")
            else:
                # Fallback на текст с цветными кнопками
                text_candidates = TEXT_PHRASES.get(category, TEXT_PHRASES["love"])
                chosen_text, response_id = choose_best_candidate(context_hash, category, text_candidates, 'text')
                short_resp_id = response_id[:6]
                keyboard = [[
                    InlineKeyboardButton("💚", callback_data=f"r:1:{context_hash}t{short_resp_id}", api_kwargs={"style": "success"}),
                    InlineKeyboardButton("🤍", callback_data=f"r:0:{context_hash}t{short_resp_id}", api_kwargs={"style": "primary"})
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(chosen_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
                ensure_response_exists(context_hash, category, 'text', response_id)
                print(f"💬 Text (fallback): {chosen_text[:60]}...")
        
        else:
            text_candidates = TEXT_PHRASES.get(category, TEXT_PHRASES["love"])
            chosen_text, response_id = choose_best_candidate(context_hash, category, text_candidates, 'text')
            short_resp_id = response_id[:6]
            keyboard = [[
                InlineKeyboardButton("💚", callback_data=f"r:1:{context_hash}t{short_resp_id}", api_kwargs={"style": "success"}),
                InlineKeyboardButton("🤍", callback_data=f"r:0:{context_hash}t{short_resp_id}", api_kwargs={"style": "primary"})
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(chosen_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            ensure_response_exists(context_hash, category, 'text', response_id)
            print(f"💬 Text: {chosen_text[:60]}... (ID: {response_id})")

    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "<b>💋💋💋</b>",
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "<b>💋💋💋</b>",
            parse_mode=ParseMode.HTML
        )

async def handle_rl_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("r:"):
        return
    
    try:
        parts = data.split(":", 2)
        if len(parts) != 3:
            return
        
        _, action, payload = parts
        
        if len(payload) < 8:
            return
        
        context_hash = payload[:6]
        response_type_char = payload[6]
        short_response_id = payload[7:13] if len(payload) >= 13 else payload[7:]
        
        response_type = 'text' if response_type_char == 't' else 'voice'
        delta = 1 if action == '1' else -5
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            '''SELECT response_id FROM responses 
               WHERE context_hash = ? AND response_type = ? 
               AND response_id LIKE ? 
               ORDER BY rating DESC LIMIT 1''',
            (context_hash, response_type, f"{short_response_id}%")
        )
        row = cursor.fetchone()
        
        if row:
            full_response_id = row[0]
            cursor.execute(
                '''UPDATE responses 
                   SET rating = rating + ? 
                   WHERE context_hash = ? AND response_type = ? AND response_id = ?''',
                (delta, context_hash, response_type, full_response_id)
            )
            print(f"✅ RL обновлён: {full_response_id} ({response_type}) {delta:+d}")
        else:
            cursor.execute(
                '''INSERT INTO responses 
                   (context_hash, category, response_type, response_id, rating) 
                   VALUES (?, ?, ?, ?, ?)''',
                (context_hash, "unknown", response_type, short_response_id or "unknown", delta)
            )
            print(f"🆕 Новая запись RL: {short_response_id} ({response_type}) {delta:+d}")
        
        conn.commit()
        conn.close()
        
        if action == '1':
            new_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("Я стал лучше!", callback_data="noop", style="primary")
            ]])
        else:
            new_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("Я стану лучше!", callback_data="noop", style="primary")
            ]])
        
        await query.edit_message_reply_markup(reply_markup=new_markup)
        print(f"✅ Фидбек обработан: {'лайк' if action == '1' else 'дизлайк'} для контекста {context_hash}")

    except Exception as e:
        print(f"❌ Ошибка обработки колбэка: {e}")
        import traceback
        traceback.print_exc()
        try:
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⚠️", callback_data="noop")
                ]])
            )
        except:
            pass

# ============ ЗАПУСК ============
def main():
    init_db()
    
    if not BOT_TOKEN:
        print("❌ ОШИБКА: BOT_TOKEN не задан в .env файле!")
        print("\nСоздайте файл .env с содержимым:")
        print("BOT_TOKEN=ваш_токен_от_@BotFather")
        exit(1)
    
    if not VOICES_DIR.exists():
        print(f"⚠️ Папка {VOICES_DIR} не найдена. Создаём...")
        VOICES_DIR.mkdir(exist_ok=True)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_random))
    # ✅ ИСПРАВЛЕННЫЙ ПАТТЕРН КОЛБЭКОВ
    app.add_handler(CallbackQueryHandler(handle_rl_callback, pattern=r"^r:[01]:[a-f0-9]{6}[tv].{1,10}$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern=r"^noop$"))
    
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║  ✅ Бот «Полиночка от Сени» с обучением запущен! ❤️               ║")
    print("╠════════════════════════════════════════════════════════════════════╣")
    print(f"║  🔒 Защита от двойного запуска: АКТИВНА                           ║")
    print(f"║  💚 Кнопки: эмодзи (стабильно) | 🎤 Голосовые: {VOICE_PROBABILITY*100:.0f}%          ║")
    print(f"║  💚 Лайк: +1 балл | 💔 Дизлайк: -5 баллов                         ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print("\n💡 Бот учится на твоих реакциях — ставь 💚/💔 под каждым ответом!")
    app.run_polling()

if __name__ == "__main__":
    main()

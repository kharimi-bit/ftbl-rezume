# -*- coding: utf-8 -*-
"""Сервис спортивного резюме — ядро: база, файлы, вспомогательные функции.

Живёт на российском сервере рядом с CRM. Здесь персональные данные:
ФИО, дата рождения, гражданство, фотография, контакты, места работы,
файлы портфолио. По 152-ФЗ (ст. 18 ч. 5) их первичная база обязана
находиться в России — поэтому сервис не на Railway и никогда туда не уедет.
"""
import os, re, sqlite3, secrets, datetime, hashlib, mimetypes

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("REZUME_DATA", os.path.join(BASE, "data"))
DB = os.path.join(DATA, "rezume.db")
UPLOADS = os.path.join(DATA, "uploads")

# Что принимаем в портфолио. Исполняемое и архивы не берём: файл лежит
# на нашем диске и отдаётся людям, значит отвечаем за него мы.
ALLOWED = {
    ".pdf": "документ", ".doc": "документ", ".docx": "документ",
    ".xls": "таблица", ".xlsx": "таблица", ".csv": "таблица",
    ".ppt": "презентация", ".pptx": "презентация",
    ".jpg": "изображение", ".jpeg": "изображение", ".png": "изображение",
    ".webp": "изображение", ".gif": "изображение",
    ".mp4": "видео", ".mov": "видео",
}
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE = 25 * 1024 * 1024      # 25 МБ на файл
MAX_TOTAL = 50 * 1024 * 1024     # 50 МБ на резюме: на сервере 40 ГБ, и там же CRM

SCHEMA = """
CREATE TABLE IF NOT EXISTS rezume(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,
  token TEXT UNIQUE NOT NULL,
  created TEXT NOT NULL,
  updated TEXT NOT NULL,
  fio TEXT DEFAULT '', born TEXT DEFAULT '',
  citizenship TEXT DEFAULT '', city TEXT DEFAULT '',
  email TEXT DEFAULT '', phone TEXT DEFAULT '', tg TEXT DEFAULT '',
  photo TEXT DEFAULT '',
  role_now TEXT DEFAULT '',
  edu TEXT DEFAULT '', edu_place TEXT DEFAULT '', licence TEXT DEFAULT '',
  skills TEXT DEFAULT '',
  now_roles TEXT DEFAULT '', work TEXT DEFAULT '',
  play TEXT DEFAULT '', referee TEXT DEFAULT '', programs TEXT DEFAULT '',
  act_coach TEXT DEFAULT '', act_analyst TEXT DEFAULT '', act_manage TEXT DEFAULT '',
  links TEXT DEFAULT '',
  consent_pd INTEGER DEFAULT 0,
  consent_pub INTEGER DEFAULT 0,
  status TEXT DEFAULT 'draft',
  moder_note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS files(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rezume_id INTEGER NOT NULL,
  stored TEXT NOT NULL,
  orig TEXT NOT NULL,
  kind TEXT DEFAULT '',
  size INTEGER DEFAULT 0,
  added TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS refs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rezume_id INTEGER NOT NULL,
  name TEXT DEFAULT '', role TEXT DEFAULT '', text TEXT DEFAULT '',
  ord INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE INDEX IF NOT EXISTS i_files ON files(rezume_id);
CREATE INDEX IF NOT EXISTS i_refs ON refs(rezume_id);
CREATE INDEX IF NOT EXISTS i_status ON rezume(status);
"""


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def db():
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(UPLOADS, exist_ok=True)
    con = sqlite3.connect(DB, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con


def setting(con, k, default=""):
    r = con.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
    return r["v"] if r else default


def set_setting(con, k, v):
    con.execute("INSERT INTO settings(k,v) VALUES(?,?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))
    con.commit()


TRANS = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
         "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
         "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
         "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
         "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"}


def translit(s):
    out = "".join(TRANS.get(c, c) for c in (s or "").lower())
    out = re.sub(r"[^a-z0-9]+", "-", out).strip("-")
    return out[:48]


def make_slug(con, fio):
    base = translit(fio) or "rezume"
    slug, n = base, 2
    while con.execute("SELECT 1 FROM rezume WHERE slug=?", (slug,)).fetchone():
        slug = f"{base}-{n}"
        n += 1
    return slug


def age(born):
    """«23.08.2001» → 24. Пустая или кривая дата возраста не даёт."""
    m = re.match(r"^\s*(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\s*$", born or "")
    if not m:
        return None
    d, mo, y = (int(x) for x in m.groups())
    try:
        b = datetime.date(y, mo, d)
    except ValueError:
        return None
    t = datetime.date.today()
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day))


def plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def safe_name(orig):
    """Имя на диске никогда не берётся от пользователя — только случайное."""
    ext = os.path.splitext(orig or "")[1].lower()
    if ext not in ALLOWED and ext not in PHOTO_EXT:
        return None, None
    return secrets.token_hex(16) + ext, ALLOWED.get(ext, "изображение")


def total_size(con, rid):
    r = con.execute("SELECT COALESCE(SUM(size),0) s FROM files WHERE rezume_id=?", (rid,)).fetchone()
    return r["s"] or 0


def lines(text):
    """Многострочное поле → список непустых строк. Так человек пишет
       свободно, а на выходе получается аккуратный список."""
    return [l.strip() for l in (text or "").split("\n") if l.strip()]

# -*- coding: utf-8 -*-
"""Уведомление в Telegram, когда резюме отправили на проверку.

Зачем. Человек нажимает «Отправить на проверку» — и дальше тишина:
запись просто появляется в /admin, а зайти туда надо догадаться.
Три резюме пролежали так до 29.09.2026, и узнали мы о них только
потому, что автор одного из них написал в общий чат.

Настройки — в notify.json рядом с этим файлом:

    {"token": "токен бота", "chat": "кому слать"}

Файла нет в репозитории и быть не должно: в нём токен. Нет файла или
он пустой — уведомления просто выключены, сервис работает как раньше.

Отправка идёт в отдельном потоке: если Telegram недоступен или тянет
время, человек не должен ждать этого на кнопке «Отправить».
"""
import json
import os
import threading
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(ROOT, "notify.json")
API = "https://api.telegram.org/bot%s/sendMessage"


def settings():
    """Токен и адресат. Пусто — уведомления выключены."""
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            s = json.load(f)
    except (OSError, ValueError):
        return None
    if not s.get("token") or not s.get("chat"):
        return None
    # Заглушка из notify.json.example — это «не настроено», а не токен.
    if "СЮДА" in str(s["token"]):
        return None
    return s


def _send(text):
    s = settings()
    if not s:
        return
    data = urllib.parse.urlencode({
        "chat_id": s["chat"],
        "text": text,
        "parse_mode": "HTML",
        # Ссылка на /admin не должна разворачиваться карточкой.
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    try:
        urllib.request.urlopen(API % s["token"], data=data, timeout=10).read()
    except Exception:
        # Уведомление — не та задача, ради которой можно уронить сохранение
        # анкеты. Не дошло, значит не дошло: запись всё равно в /admin.
        pass


def na_proverku(r, host):
    """Резюме отправлено на проверку. Шлём только то, что и так видно
       в списке модерации: имя, город и ссылку — без контактов."""
    if not settings():
        return
    fio = (r["fio"] or "").strip() or "Без имени"
    gorod = (r["city"] or "").strip()
    text = ("📝 <b>Резюме на проверку</b>\n"
            f"{fio}" + (f" · {gorod}" if gorod else "") + "\n"
            f"https://{host}/admin")
    threading.Thread(target=_send, args=(text,), daemon=True).start()

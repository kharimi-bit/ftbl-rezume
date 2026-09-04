# -*- coding: utf-8 -*-
"""Приём оплаты через интернет-эквайринг Т-Банка.

Зачем этот файл вообще есть. Т-Банк требует, чтобы каждый запрос на
создание платежа был подписан паролем терминала. Пароль нельзя положить
в страницу сайта — её исходный код видит любой посетитель. Значит
подписывать должен сервер. Ровно это же делает Tilda: у неё в настройках
лежит пароль, и её сервер подписывает платежи. Здесь то же самое,
только сервер свой.

Как это работает по шагам:

  1. Страница на futbologik.ru отправляет обычную форму сюда, на /pay/.
     Никакого JavaScript, никаких запросов между доменами — браузер
     просто переходит по адресу.
  2. Мы собираем запрос, считаем подпись паролем и зовём метод Init
     у Т-Банка.
  3. Т-Банк возвращает адрес своей платёжной формы, и мы отправляем
     туда браузер. Карту человек вводит уже на стороне банка — ни сайт,
     ни этот сервер её не видят.

Настройки лежат в pay.json рядом с этим файлом. Файла нет в репозитории
и не должно быть: в нём пароль.
"""
import hashlib
import json
import os
import re
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(ROOT, "pay.json")
API = "https://securepay.tinkoff.ru/v2/Init"

# Разрешённые адреса, куда можно вернуть человека после оплаты.
# Список закрытый: иначе ссылку на нашу форму можно было бы использовать
# как открытый редирект на чужой сайт.
BACK = "https://www.futbologik.ru"


def settings():
    """Терминал и пароль. Пусто — приём оплаты выключен целиком."""
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            s = json.load(f)
    except (OSError, ValueError):
        return None
    if not s.get("terminal") or not s.get("password"):
        return None
    s.setdefault("min", 500)
    s.setdefault("max", 300000)
    s.setdefault("taxation", "usn_income")
    s.setdefault("vat", "none")
    s.setdefault("receipt", True)
    return s


def token(payload, password):
    """Подпись запроса по правилам Т-Банка.

       Берём только поля верхнего уровня и только простые значения —
       вложенные объекты Receipt и DATA в подпись не входят. Добавляем
       пароль, сортируем по имени поля, склеиваем значения подряд
       и считаем SHA-256."""
    pairs = {k: v for k, v in payload.items()
             if not isinstance(v, (dict, list)) and k != "Token"}
    pairs["Password"] = password
    joined = "".join(str(pairs[k]) for k in sorted(pairs))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def receipt(s, email, name, amount_kop):
    """Фискальный чек. Состав повторяет то, что настроено на терминале
       в Tilda: система налогообложения, ставка НДС, признак предмета
       и способа расчёта. Наименование — то, что плательщик написал
       в назначении платежа."""
    return {
        "Email": email,
        "Taxation": s["taxation"],
        "Items": [{
            "Name": name[:128],
            "Price": amount_kop,
            "Quantity": 1,
            "Amount": amount_kop,
            "Tax": s["vat"],
            "PaymentMethod": "full_prepayment",
            "PaymentObject": "service",
        }],
    }


def order_id():
    """Номер заказа. Т-Банк требует уникальный; берём случайные байты —
       счётчика заказов у нас нет и заводить его незачем."""
    return "F" + os.urandom(8).hex()


def init(amount_rub, description, name, email):
    """Создаёт платёж и возвращает (адрес формы Т-Банка, текст ошибки).
       Ровно одно из двух будет пустым."""
    s = settings()
    if not s:
        return "", "Приём оплаты не настроен."

    try:
        amount = int(amount_rub)
    except (TypeError, ValueError):
        return "", "Сумма указана неверно."
    if amount < s["min"] or amount > s["max"]:
        return "", f"Сумма должна быть от {s['min']} до {s['max']} ₽."

    description = (description or "").strip()[:140]
    name = (name or "").strip()[:120]
    email = (email or "").strip()[:120]
    if len(description) < 3:
        return "", "Напишите, за что платите."
    if len(name) < 3:
        return "", "Укажите фамилию и имя."
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return "", "Проверьте почту — на неё придёт чек."

    kop = amount * 100
    payload = {
        "TerminalKey": s["terminal"],
        "Amount": kop,
        "OrderId": order_id(),
        "Description": description,
        "SuccessURL": BACK + "/oplata/gotovo/",
        "FailURL": BACK + "/oplata/oshibka/",
    }
    payload["Token"] = token(payload, s["password"])
    # DATA и Receipt добавляем ПОСЛЕ подписи: в неё они не входят.
    payload["DATA"] = {"Email": email, "Name": name}
    if s["receipt"]:
        payload["Receipt"] = receipt(s, email, description, kop)

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API, data=body,
        headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            answer = json.loads(resp.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, ValueError, OSError):
        return "", "Банк не ответил. Попробуйте ещё раз через минуту."

    if answer.get("Success") and answer.get("PaymentURL"):
        return answer["PaymentURL"], ""
    # Текст банка показываем как есть: он объясняет причину лучше,
    # чем любая наша формулировка.
    return "", (answer.get("Message") or "Банк отклонил платёж.") + \
        ((" " + answer["Details"]) if answer.get("Details") else "")

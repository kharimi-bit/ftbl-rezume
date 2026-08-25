# -*- coding: utf-8 -*-
"""Отрисовка резюме: лист, который человек показывает клубу."""
import html as H
from core import age, lines, plural
from style import CSS

E = H.escape
LINK = __import__("re").compile(r"(https?://[^\s<]+)")


def linkify(s):
    """Ссылки на портфолио в тексте становятся кликабельными.
       Внутрь разметки не лезем: текст уже экранирован."""
    return LINK.sub(lambda m: f'<a href="{m.group(1)}" rel="noopener nofollow" target="_blank">{m.group(1)}</a>', s)


def li_list(items):
    return "".join(f"<li>{linkify(E(x))}</li>" for x in items)


def page(title, body, extra=""):
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="robots" content="noindex">
<style>{CSS}{extra}</style>
</head><body>{body}</body></html>"""


def sheet(r, files, refs, photo_url):
    """Сам лист. Пустые блоки не рисуются — резюме без судейского опыта
       не должно показывать пустую строку «Судейский опыт»."""
    a = age(r["born"])
    born = E(r["born"] or "")
    if a is not None:
        born += f" ({a} {plural(a, 'год', 'года', 'лет')})"

    facts = []
    for label, val in [
        ("ФИО", r["fio"]), ("Дата рождения (возраст)", born),
        ("Гражданство", r["citizenship"]), ("Место жительства", r["city"]),
        ("Лицензия", r["licence"]), ("Образование", r["edu"]),
        ("Учебное заведение", r["edu_place"]),
    ]:
        if (val or "").strip():
            v = val if label == "Дата рождения (возраст)" else E(val)
            facts.append(f'<div class="fact"><dt>{label}</dt><dd>{v}</dd></div>')

    contacts = []
    if r["email"]:
        contacts.append(f'<a href="mailto:{E(r["email"])}">{E(r["email"])}</a>')
    if r["phone"]:
        contacts.append(E(r["phone"]))
    if r["tg"]:
        t = r["tg"].lstrip("@")
        contacts.append(f'<a href="https://t.me/{E(t)}" rel="noopener">@{E(t)}</a>')
    if contacts:
        facts.append(f'<div class="fact"><dt>Контактные данные</dt>'
                     f'<dd>{" · ".join(contacts)}</dd></div>')

    ph = (f'<img src="{E(photo_url)}" alt="">' if photo_url
          else '<div class="none">Фотография<br>не загружена</div>')

    out = [f'<div class="sheet"><div class="bar">Общая информация</div>',
           f'<div class="top"><div class="photo">{ph}</div>',
           f'<div class="facts">{"".join(facts)}</div></div>']

    def block(title, items, small=False):
        if not items:
            return
        rows = "".join(f'<div class="row">{linkify(E(x))}</div>' for x in items)
        out.append(f'<div class="bar{" sm" if small else ""}">{title}</div>'
                   f'<div class="block">{rows}</div>')

    block("В настоящее время", lines(r["now_roles"]))

    exp = lines(r["work"])
    subs = []
    for h, key in [("Игровой опыт", "play"), ("Судейский опыт", "referee"),
                   ("Программы и треки", "programs"), ("Навыки", "skills")]:
        it = lines(r[key])
        if it:
            subs.append(f'<div class="sub"><h4>{h}</h4><ul>{li_list(it)}</ul></div>')
    if exp or subs:
        rows = "".join(f'<div class="row">{linkify(E(x))}</div>' for x in exp)
        out.append('<div class="bar">Опыт работы</div>'
                   f'<div class="block">{rows}{"".join(subs)}</div>')

    block("Тренерская деятельность", lines(r["act_coach"]))
    block("Аналитическая деятельность", lines(r["act_analyst"]))
    block("Менеджмент", lines(r["act_manage"]))
    block("Материалы и ссылки", lines(r["links"]))

    if files:
        cards = "".join(
            f'<a class="file" href="/f/{E(f["stored"])}" target="_blank" rel="noopener">'
            f'<span>{E(f["orig"])}</span><span class="k">{E(f["kind"])}</span></a>'
            for f in files)
        out.append('<div class="bar">Портфолио</div>'
                   f'<div class="block"><div class="files">{cards}</div></div>')

    if refs:
        out.append('<div class="bar">Рекомендации</div>')
        for x in refs:
            who = f'<div class="who">{E(x["name"])}</div>' if x["name"] else ""
            role = f'<div class="role">{E(x["role"])}</div>' if x["role"] else ""
            out.append(
                '<div class="ref"><div class="ref-ph"><div class="none"></div></div>'
                f'<div class="ref-tx">«{linkify(E(x["text"]))}»{who}{role}</div></div>')

    out.append("</div>")
    return "".join(out)

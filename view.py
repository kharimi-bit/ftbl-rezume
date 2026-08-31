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


# Яндекс.Метрика — тот же счётчик, что на futbologik.ru: домен считается
# с поддоменами, поэтому переход «сайт → резюме» виден одним визитом.
METRIKA = "112073076"


# Адреса, под которыми страницы видны в Метрике. Ключ — вид страницы,
# значение — что уйдёт в отчёт. Всё, чего нет в этом словаре, не считается.
SCHET = {"anketa": "Анкета резюме", "rezume": "Лист резюме"}
CELI = {"rezume_gotovo"}


def counter(goal=None):
    """Сам счётчик. Вебвизор, карта кликов и трекинг ссылок выключены:
       на сервисе персональные данные, и Метрика не должна видеть,
       что человек печатает."""
    if not METRIKA:
        return ""
    cel = f'ym({METRIKA},"reachGoal","{goal}");' if goal else ""
    return f"""<script>
(function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};
m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],
k.async=1,k.referrerPolicy="no-referrer",k.src=r,a.parentNode.insertBefore(k,a)}})
(window,document,"script","https://mc.yandex.ru/metrika/tag.js","ym");
ym({METRIKA},"init",{{accurateTrackBounce:true,webvisor:false,clickmap:false,trackLinks:false}});{cel}
</script>"""


def schet_page(kind, goal=None):
    """Страница-счётчик, которую анкета и лист резюме грузят в невидимом кадре.

       Так надо, потому что Метрика при запуске отправляет технический запрос
       с настоящим адресом страницы — даже если сам просмотр отложить через
       defer. А в адресе анкеты лежит токен, дающий право её править, и в
       адресе листа — имя человека. Внутри кадра адрес свой и чистый:
       /schet/anketa. Настоящий адрес туда не попадает ни адресной строкой,
       ни заголовком Referer — кадр загружается без него."""
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>{E(SCHET.get(kind, kind))}</title>
<meta name="robots" content="noindex">
<meta name="referrer" content="no-referrer">
{counter(goal)}
</head><body></body></html>"""


def frame(kind, goal=None):
    """Невидимый кадр со счётчиком. Ставится вместо счётчика на те страницы,
       адрес которых в Яндекс отдавать нельзя."""
    if not METRIKA or kind not in SCHET:
        return ""
    src = f"/schet/{kind}" + (f"?c={goal}" if goal in CELI else "")
    return (f'<iframe src="{src}" referrerpolicy="no-referrer" loading="eager"'
            f' aria-hidden="true" tabindex="-1" title="счётчик"'
            f' style="position:absolute;width:0;height:0;border:0;left:-9999px"></iframe>')


def page(title, body, extra="", schet=False, hit=None, goal=None):
    """schet=False — счётчика на странице нет вовсе (модерация, вход, ошибки).
       hit=None при schet=True — титульная: адрес настоящий, источник нужен.
       hit="anketa" или "rezume" — счётчик уезжает в кадр с чистым адресом."""
    tiho = ('\n<meta name="referrer" content="no-referrer">' if hit else "")
    if not schet:
        golova, hvost = "", ""
    elif hit is None:
        golova, hvost = counter(), (
            f'\n<noscript><div><img src="https://mc.yandex.ru/watch/{METRIKA}"'
            f' style="position:absolute;left:-9999px" alt=""></div></noscript>')
    else:
        golova, hvost = "", "\n" + frame(hit, goal)
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="robots" content="noindex">{tiho}
<style>{CSS}{extra}</style>
{golova}
</head><body>{body}{hvost}</body></html>"""


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
        # Ссылкой делаем только то, что похоже на почту: mailto: на «ываыа»
        # выглядит поломкой, а не заботой.
        m = "@" in r["email"] and "." in r["email"].split("@")[-1]
        contacts.append(f'<a href="mailto:{E(r["email"])}">{E(r["email"])}</a>'
                        if m else E(r["email"]))
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

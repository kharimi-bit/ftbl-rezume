# -*- coding: utf-8 -*-
"""Анкета: человек заполняет слева, справа сразу видит свой лист."""
import html as H
from style import CSS

E = H.escape

FORM_CSS = """
.split{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.05fr);
  gap:30px;max-width:1360px;margin:0 auto;padding:26px 22px 80px;align-items:start}
@media(max-width:1080px){.split{grid-template-columns:1fr}}
.pane{position:sticky;top:22px}
@media(max-width:1080px){.pane{position:static}}
.pane .sheet{box-shadow:0 1px 2px rgba(27,67,50,.06),0 14px 40px -20px rgba(27,67,50,.35)}
.pane-h{font-size:.8rem;letter-spacing:.1em;text-transform:uppercase;
  color:var(--muted);font-weight:700;margin:0 0 10px}

.f{margin-bottom:14px}
.f:last-child{margin-bottom:0}
.f label{display:block;font-weight:700;font-size:.9rem;margin-bottom:5px}
.f .sub{display:block;margin-top:5px;color:var(--muted);font-size:.84rem;line-height:1.35}
.two .f{margin-bottom:0}
input[type=text],input[type=email],input[type=tel],textarea,select{
  width:100%;padding:11px 14px;border:2px solid var(--line);border-radius:10px;
  font-family:inherit;font-size:.97rem;color:var(--ink);background:#fff;
  transition:border-color .15s}
input:focus,textarea:focus{outline:none;border-color:var(--jade)}
textarea{min-height:104px;resize:vertical;line-height:1.5}
.two{display:grid;grid-template-columns:1fr 1fr;gap:14px;
  align-items:start;margin-bottom:14px}
@media(max-width:620px){.two{grid-template-columns:1fr}}

.drop{border:2px dashed var(--line);border-radius:12px;padding:18px;
  text-align:center;color:var(--muted);font-size:.92rem;background:var(--ground)}
.drop input{display:none}
.drop label{cursor:pointer;color:var(--jade);font-weight:700;display:inline}
.flist{display:grid;gap:7px;margin-top:11px}
.frow{display:flex;align-items:center;gap:10px;font-size:.9rem;
  border:1px solid var(--line);border-radius:9px;padding:8px 12px;background:#fff}
.frow .k{margin-left:auto;color:var(--muted);font-size:.78rem;text-transform:uppercase}
.frow a.del{color:var(--accent);text-decoration:none;font-weight:700}

.ref-edit{border:1px solid var(--line);border-radius:12px;padding:14px;
  margin-bottom:11px;background:var(--ground)}
.consent{display:flex;gap:11px;align-items:flex-start;margin-bottom:13px;
  font-size:.92rem;line-height:1.45}
.consent input{margin-top:3px;width:18px;height:18px;flex:none;accent-color:var(--jade)}
.bar-save{position:sticky;bottom:0;background:#fff;border-top:2px solid var(--line);
  padding:14px 22px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;
  margin:0 -24px -22px;border-radius:0 0 14px 14px}
.ok{color:var(--jade);font-weight:700;font-size:.9rem}
.err{color:var(--accent);font-weight:700;font-size:.9rem}
"""


def field(name, label, val, hint="", kind="text", ph=""):
    """Подсказка идёт под полем, а не рядом с меткой: в паре колонок
       длинная подсказка ломала бы высоту метки и разъезжало выравнивание."""
    sub = f'<span class="sub">{hint}</span>' if hint else ""
    if kind == "area":
        el = (f'<textarea name="{name}" id="{name}" placeholder="{E(ph)}">'
              f'{E(val or "")}</textarea>')
    else:
        el = (f'<input type="{kind}" name="{name}" id="{name}" '
              f'value="{E(val or "")}" placeholder="{E(ph)}">')
    return f'<div class="f"><label for="{name}">{label}</label>{el}{sub}</div>'


def render(r, files, refs, saved=""):
    g = lambda k: (r[k] if r else "") or ""
    token = g("token")

    photo = (f'<div class="frow"><span>Фотография загружена</span>'
             f'<a class="del" href="/photo/del?t={token}">убрать</a></div>'
             if g("photo") else "")

    flist = "".join(
        f'<div class="frow"><span>{E(f["orig"])}</span>'
        f'<span class="k">{E(f["kind"])}</span>'
        f'<a class="del" href="/file/del?t={token}&id={f["id"]}">убрать</a></div>'
        for f in files)

    refs_html = ""
    for i in range(3):
        x = refs[i] if i < len(refs) else None
        rn = (x["name"] if x else "")
        rr = (x["role"] if x else "")
        rt = (x["text"] if x else "")
        refs_html += f'''<div class="ref-edit">
<div class="two">
{field(f"ref_name_{i}", "Кто рекомендует", rn, ph="Фамилия Имя Отчество")}
{field(f"ref_role_{i}", "Должность", rr, ph="главный тренер ФК …")}
</div>
{field(f"ref_text_{i}", "Текст рекомендации", rt, kind="area", ph="Прямая речь без кавычек — кавычки поставим сами.")}
</div>'''

    status_line = {
        "draft": "Черновик — виден только по вашей ссылке",
        "sent": "Отправлено на проверку в «Люди футбола»",
        "published": "Опубликовано в разделе «Люди футбола»",
        "rejected": "Возвращено на доработку",
    }.get(g("status"), "")

    pub_block = ""
    if g("status") in ("draft", "rejected"):
        pub_block = f'''<div class="card">
<h2>Профиль в «Людях футбола»</h2>
<p class="hint">Раздел на futbologik.ru, где собраны специалисты, работающие в клубах.
Попадание туда — по решению редакции, автоматически профиль не публикуется.</p>
<div class="consent"><input type="checkbox" name="consent_pub" id="consent_pub"
  {"checked" if g("consent_pub") else ""}>
<label for="consent_pub" style="font-weight:400">Прошу опубликовать мой профиль
в разделе «Люди футбола». Понимаю, что публикуются имя, город, направление
и опыт; <b>телефон и почта не публикуются никогда</b> — связь идёт через форму.</label></div>
<button class="btn btn-jade" name="send" value="1">Отправить на проверку</button>
</div>'''

    return f'''<div class="hdr"><div class="hdr-in">
<span class="mk"><i></i><i></i><i></i></span><b>Спортивное резюме</b>
<div class="sp">
  {'<small>' + status_line + '</small>' if status_line else ''}
  <a class="btn btn-ghost" href="/r/{E(g("slug"))}" target="_blank">Посмотреть лист</a>
</div></div></div>

<form class="split" method="post" action="/save?t={token}" enctype="multipart/form-data" id="f">
<div>

<div class="card">
<h2>Кто вы</h2>
<p class="hint">Это шапка резюме. Заполняется один раз и дальше не меняется.</p>
<div class="f"><label>Фотография</label>
<div class="drop"><input type="file" name="photo" id="photo" accept="image/*">
<label for="photo">Выбрать фотографию</label> — jpg, png или webp до 25 МБ</div>
<span class="sub">Портрет, лучше вертикальный: он встаёт в левую колонку резюме.</span>{photo}</div>
{field("fio", "ФИО", g("fio"), ph="Фамилия Имя Отчество")}
<div class="two">
{field("born", "Дата рождения", g("born"), "возраст посчитаем сами", ph="23.08.2001")}
{field("citizenship", "Гражданство", g("citizenship"), ph="Россия")}
</div>
{field("city", "Место жительства", g("city"), ph="Россия, Москва")}
<div class="two">
{field("email", "Почта", g("email"), kind="email", ph="name@mail.ru")}
{field("phone", "Телефон", g("phone"), kind="tel", ph="+7 900 000-00-00")}
</div>
{field("tg", "Telegram", g("tg"), "без ссылки, просто имя", ph="@username")}
</div>

<div class="card">
<h2>Образование и лицензии</h2>
<p class="hint">Основное образование и футбольные лицензии, если они есть.</p>
{field("edu", "Образование", g("edu"), ph="Высшее (спортивное)")}
{field("edu_place", "Учебное заведение", g("edu_place"), ph="РУС «ГЦОЛИФК», кафедра ТиМ футбола (2021–2025)")}
{field("licence", "Лицензия", g("licence"), "UEFA C, B, A или Pro", ph="C-UEFA")}
</div>

<div class="card">
<h2>Чем занимаетесь сейчас</h2>
<p class="hint">Текущие роли. Каждая с новой строки — так они встанут списком.</p>
{field("now_roles", "В настоящее время", g("now_roles"), kind="area",
       ph="Аналитик МФК «2DROTS» Москва с августа 2024\\nСпортивный директор «2DROTS ACADEMY»")}
</div>

<div class="card">
<h2>Опыт</h2>
<p class="hint">Каждый пункт с новой строки. Ссылки вставляйте прямо в текст —
они станут кликабельными.</p>
{field("work", "Опыт работы", g("work"), kind="area",
       ph="Видеооператор-аналитик ФК «Сочи» в сезоне 2023/24 Российской Премьер-лиги")}
{field("play", "Игровой опыт", g("play"), kind="area", ph="ДЮСШ «Алтай» с 2013 по 2016")}
{field("referee", "Судейский опыт", g("referee"), kind="area", ph="если его нет — оставьте пустым")}
{field("programs", "Программы и треки", g("programs"), kind="area",
       ph="Треки «Футбологики» по скаутингу и видеоаналитике")}
{field("skills", "Навыки", g("skills"), kind="area", ph="Nacsport, Hudl Sportscode, Wyscout")}
</div>

<div class="card">
<h2>Что вы умеете делать</h2>
<p class="hint">Самый важный раздел. Не «умею готовить отчёт», а отчёт, который можно
открыть. Ссылку ставьте в ту же строку — работодатель откроет и посмотрит.</p>
{field("act_coach", "Тренерская деятельность", g("act_coach"), kind="area",
       ph="Подготовка и разбор тренировочных занятий — https://disk.yandex.ru/…")}
{field("act_analyst", "Аналитическая деятельность", g("act_analyst"), kind="area",
       ph="Отчёт по сопернику к матчу РПЛ — https://disk.yandex.ru/…")}
{field("act_manage", "Менеджмент", g("act_manage"), kind="area",
       ph="Формирование концепции академии")}
{field("links", "Другие материалы", g("links"), kind="area")}
</div>

<div class="card">
<h2>Портфолио файлами</h2>
<p class="hint">До 50 МБ на резюме. Документы, таблицы, презентации, изображения и видео.</p>
<div class="drop"><input type="file" name="files" id="files" multiple>
<label for="files">Выбрать файлы</label> — можно сразу несколько</div>
<div class="flist">{flist}</div>
</div>

<div class="card">
<h2>Рекомендации</h2>
<p class="hint">Чужое слово весит больше своего. До трёх рекомендаций.</p>
{refs_html}
</div>

{pub_block}

<div class="card">
<h2>Согласие</h2>
<div class="consent"><input type="checkbox" name="consent_pd" id="consent_pd" required
  {"checked" if g("consent_pd") else ""}>
<label for="consent_pd" style="font-weight:400">Даю согласие на обработку персональных
данных, указанных в анкете. Данные хранятся на сервере в России и используются
только для сборки резюме. Посещаемость страниц считает Яндекс.Метрика: она получает
обезличенный адрес страницы и не получает того, что вы вводите в анкету.</label></div>
<div class="bar-save">
<button class="btn btn-main" type="submit">Сохранить</button>
<span class="{"ok" if saved == "ok" else "err"}">{E(saved if saved != "ok" else "Сохранено")}</span>
</div>
</div>

</div>

<div class="pane">
<p class="pane-h">Как это выглядит</p>
<div id="prev"></div>
</div>
</form>

<script>
const f = document.getElementById("f"), prev = document.getElementById("prev");
let t = null;
function draw(){{
  const d = new FormData(f);
  d.delete("photo"); d.delete("files");
  fetch("/preview?t={token}", {{method:"POST", body:d}})
    .then(r => r.text()).then(h => {{ prev.innerHTML = h; }})
    .catch(() => {{}});
}}
f.addEventListener("input", () => {{ clearTimeout(t); t = setTimeout(draw, 400); }});
draw();
</script>'''

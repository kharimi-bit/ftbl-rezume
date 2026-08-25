# -*- coding: utf-8 -*-
"""Сервис спортивного резюме. Запуск: python3 app.py --port 8080

Всё на стандартной библиотеке: ни pip, ни зависимостей. Тот же приём,
что в CRM, — обновление сервиса это git pull и перезапуск службы.
"""
import os, re, sys, html, sqlite3, secrets, argparse, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core, view, form
from core import db, now, setting, set_setting, UPLOADS, ALLOWED, PHOTO_EXT
from style import CSS

E = html.escape

FIELDS = ["fio", "born", "citizenship", "city", "email", "phone", "tg",
          "edu", "edu_place", "licence", "skills", "now_roles", "work",
          "play", "referee", "programs", "act_coach", "act_analyst",
          "act_manage", "links"]


# ─────────────────── разбор multipart ───────────────────
def parse_multipart(body, boundary):
    """Минимальный разбор multipart/form-data. Модуль cgi из стандартной
       библиотеки убран, поэтому разбираем сами — тут ровно один формат."""
    fields, files = {}, []
    sep = b"--" + boundary
    for part in body.split(sep):
        if not part or part in (b"--\r\n", b"--"):
            continue
        part = part.lstrip(b"\r\n")
        head, _, data = part.partition(b"\r\n\r\n")
        if not _:
            continue
        data = data[:-2] if data.endswith(b"\r\n") else data
        try:
            head_s = head.decode("utf-8", "replace")
        except Exception:
            continue
        m = re.search(r'name="([^"]*)"', head_s)
        if not m:
            continue
        name = m.group(1)
        fn = re.search(r'filename="([^"]*)"', head_s)
        if fn:
            if fn.group(1) and data:
                files.append((name, fn.group(1), data))
        else:
            fields.setdefault(name, data.decode("utf-8", "replace"))
    return fields, files


def parse_urlencoded(body):
    q = urllib.parse.parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True)
    return {k: v[0] for k, v in q.items()}


# ─────────────────── работа с записью ───────────────────
def load(con, token=None, slug=None):
    if token:
        return con.execute("SELECT * FROM rezume WHERE token=?", (token,)).fetchone()
    return con.execute("SELECT * FROM rezume WHERE slug=?", (slug,)).fetchone()


def kids(con, rid):
    f = con.execute("SELECT * FROM files WHERE rezume_id=? ORDER BY id", (rid,)).fetchall()
    r = con.execute("SELECT * FROM refs WHERE rezume_id=? ORDER BY ord,id", (rid,)).fetchall()
    return f, r


def photo_url(r):
    return f'/f/{r["photo"]}' if r and r["photo"] else ""


def create(con):
    tok = secrets.token_urlsafe(24)
    slug = "rezume-" + secrets.token_hex(4)
    con.execute("INSERT INTO rezume(slug,token,created,updated) VALUES(?,?,?,?)",
                (slug, tok, now(), now()))
    con.commit()
    return tok


def save_fields(con, r, d):
    vals = [d.get(k, "").strip() for k in FIELDS]
    con.execute(f"UPDATE rezume SET {','.join(k+'=?' for k in FIELDS)}, "
                "consent_pd=?, consent_pub=?, updated=? WHERE id=?",
                vals + [1 if d.get("consent_pd") else 0,
                        1 if d.get("consent_pub") else 0, now(), r["id"]])
    # слаг подтягивается к имени, но только пока резюме не опубликовано
    fio = d.get("fio", "").strip()
    if fio and r["status"] in ("draft", "rejected") and r["slug"].startswith("rezume-"):
        con.execute("UPDATE rezume SET slug=? WHERE id=?",
                    (core.make_slug(con, fio), r["id"]))
    con.execute("DELETE FROM refs WHERE rezume_id=?", (r["id"],))
    for i in range(3):
        t = d.get(f"ref_text_{i}", "").strip()
        n = d.get(f"ref_name_{i}", "").strip()
        if t or n:
            con.execute("INSERT INTO refs(rezume_id,name,role,text,ord) VALUES(?,?,?,?,?)",
                        (r["id"], n, d.get(f"ref_role_{i}", "").strip(), t, i))
    con.commit()


def store_files(con, r, files):
    """Возвращает текст ошибки или пусто. Имя на диске всегда случайное:
       имя от пользователя на файловой системе — это дыра."""
    for name, orig, data in files:
        if len(data) > core.MAX_FILE:
            return f"Файл «{orig}» больше 25 МБ"
        stored, kind = core.safe_name(orig)
        if not stored:
            return f"Такой тип файла не принимаем: «{orig}»"
        if name == "photo":
            if os.path.splitext(stored)[1] not in PHOTO_EXT:
                return "Фотография должна быть jpg, png или webp"
            old = r["photo"]
            with open(os.path.join(UPLOADS, stored), "wb") as fh:
                fh.write(data)
            con.execute("UPDATE rezume SET photo=? WHERE id=?", (stored, r["id"]))
            if old:
                try:
                    os.remove(os.path.join(UPLOADS, old))
                except OSError:
                    pass
        else:
            if core.total_size(con, r["id"]) + len(data) > core.MAX_TOTAL:
                return "Портфолио превысило 200 МБ — уберите лишнее"
            with open(os.path.join(UPLOADS, stored), "wb") as fh:
                fh.write(data)
            con.execute("INSERT INTO files(rezume_id,stored,orig,kind,size,added) "
                        "VALUES(?,?,?,?,?,?)", (r["id"], stored, orig[:120], kind,
                                                len(data), now()))
    con.commit()
    return ""


# ─────────────────── страницы ───────────────────
def landing():
    return view.page("Спортивное резюме — Футбологика", f"""
<div class="hdr"><div class="hdr-in">
<span class="mk"><i></i><i></i><i></i></span><b>Спортивное резюме</b>
<div class="sp"><a class="btn btn-ghost" href="https://futbologik.ru/" rel="noopener">Футбологика</a><a class="btn btn-main" href="/new">Собрать резюме</a></div>
</div></div>
<div class="wrap" style="max-width:760px">
<h1 style="font-size:clamp(1.8rem,4vw,2.6rem);line-height:1.12;margin:34px 0 14px">
Резюме, которое в клубе дочитают до конца</h1>
<p style="font-size:1.12rem;color:var(--muted);margin:0 0 26px">
Обычное резюме говорит, что вы умеете. Спортивное — показывает.
Отчёт по сопернику, разбор тренировки, план на игру: ссылка, которую
спортивный директор открывает и смотрит сам.</p>
<div class="card" style="background:#fff;border:2px solid var(--line);
  border-radius:16px;padding:24px 26px">
<h2 style="margin:0 0 12px;font-size:1.1rem">Что получится на выходе</h2>
<ul style="margin:0;padding-left:20px;line-height:1.75">
<li><b>Постоянная ссылка</b> — отправляете в клуб вместо файла, она всегда свежая.</li>
<li><b>PDF</b> — тот же лист, сохранённый на компьютер.</li>
<li><b>Профиль в «Людях футбола»</b> — по желанию и после проверки редакцией.</li>
</ul></div>
<p style="margin:26px 0 0;color:var(--muted);font-size:.92rem">
Данные хранятся на сервере в России. Телефон и почта не публикуются никогда —
даже если профиль попадёт в открытый раздел.</p>
<p style="margin:24px 0 0"><a class="btn btn-main" href="/new">Собрать резюме</a></p>
</div>""")


def public(r, files, refs, owner):
    tools = ""
    if owner:
        tools = (f'<div class="tools"><a class="btn btn-ghost" href="/e/{E(r["token"])}">'
                 f'← Править</a>'
                 f'<button class="btn btn-main" onclick="window.print()">Скачать PDF</button>'
                 f'<span class="note" style="margin:0">Печать → «Сохранить как PDF»</span></div>')
    else:
        tools = ('<div class="tools">'
                 '<button class="btn btn-main" onclick="window.print()">Скачать PDF</button></div>')
    podpis = ('<p class="noprint" style="text-align:center;margin:26px 0 40px;'
              'font-size:.92rem;color:var(--muted)">Резюме собрано в сервисе '
              '<a href="https://futbologik.ru/" rel="noopener">«Футбологики»</a>. '
              'Своё — <a href="/new">за пятнадцать минут</a>.</p>')
    body = (f'<div class="wrap">{tools}'
            f'{view.sheet(r, files, refs, photo_url(r))}{podpis}</div>')
    return view.page(f'{r["fio"] or "Спортивное резюме"} — резюме', body)


def admin_page(con, msg=""):
    rows = con.execute("SELECT * FROM rezume WHERE status IN ('sent','published') "
                       "ORDER BY CASE status WHEN 'sent' THEN 0 ELSE 1 END, updated DESC"
                       ).fetchall()
    items = ""
    for r in rows:
        badge = {"sent": "на проверке", "published": "опубликовано"}.get(r["status"], "")
        act = ""
        if r["status"] == "sent":
            act = (f'<a class="btn btn-jade" href="/admin/act?id={r["id"]}&do=pub">Опубликовать</a> '
                   f'<a class="btn btn-ghost" href="/admin/act?id={r["id"]}&do=back">Вернуть</a>')
        else:
            act = f'<a class="btn btn-ghost" href="/admin/act?id={r["id"]}&do=hide">Снять</a>'
        items += f'''<div class="card" style="margin-bottom:12px">
<div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap">
<b style="font-size:1.05rem">{E(r["fio"] or "без имени")}</b>
<span class="note" style="margin:0">{E(r["city"] or "")} · {badge} · {E(r["updated"])}</span>
<span style="margin-left:auto;display:flex;gap:8px;flex-wrap:wrap">
<a class="btn btn-ghost" href="/r/{E(r["slug"])}?t={E(r["token"])}" target="_blank">Открыть</a>
{act}</span></div></div>'''
    if not items:
        items = '<p class="note">Пока никто не просился в «Люди футбола».</p>'
    return view.page("Модерация резюме", f'''
<div class="hdr"><div class="hdr-in">
<span class="mk"><i></i><i></i><i></i></span><b>Модерация резюме</b></div></div>
<div class="wrap" style="max-width:900px">
{'<p class="ok" style="color:var(--jade);font-weight:700">' + E(msg) + '</p>' if msg else ''}
{items}</div>''')


def ask_pass(msg=""):
    return view.page("Вход", f'''<div class="wrap" style="max-width:420px">
<div class="card" style="background:#fff;border:2px solid var(--line);
  border-radius:16px;padding:26px;margin-top:60px">
<h2 style="margin:0 0 14px;font-size:1.15rem">Модерация</h2>
{'<p class="note" style="color:var(--accent)">' + E(msg) + '</p>' if msg else ''}
<form method="post" action="/admin/login">
<input type="password" name="p" placeholder="Пароль" autofocus
  style="width:100%;padding:11px 14px;border:2px solid var(--line);border-radius:10px;
  font-family:inherit;font-size:.97rem;margin-bottom:12px">
<button class="btn btn-main" type="submit">Войти</button>
</form></div></div>''')


# ─────────────────── маршруты ───────────────────
MIME = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif",
        ".mp4": "video/mp4", ".mov": "video/quicktime", ".csv": "text/csv"}


class H(BaseHTTPRequestHandler):
    server_version = "ftbl-rezume"

    def log_message(self, *a):
        pass

    # ── ответы ──
    def send(self, body, code=200, ctype="text/html; charset=utf-8", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def go(self, url, extra=None):
        self.send_response(303)
        self.send_header("Location", url)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()

    def q(self):
        u = urllib.parse.urlparse(self.path)
        return u.path, {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > core.MAX_TOTAL + 5 * 1024 * 1024:
            return b""
        return self.rfile.read(n)

    def read_form(self):
        ct = self.headers.get("Content-Type") or ""
        raw = self.body()
        if ct.startswith("multipart/form-data"):
            m = re.search(r"boundary=([^;]+)", ct)
            if not m:
                return {}, []
            return parse_multipart(raw, m.group(1).strip('"').encode())
        return parse_urlencoded(raw), []

    def is_admin(self):
        con = db()
        want = setting(con, "admin_sid")
        con.close()
        ck = self.headers.get("Cookie") or ""
        m = re.search(r"sid=([A-Za-z0-9_\-]+)", ck)
        return bool(want) and bool(m) and m.group(1) == want

    # ── GET ──
    def do_GET(self):
        path, qs = self.q()
        con = db()
        try:
            if path == "/":
                return self.send(landing())

            if path == "/new":
                return self.go("/e/" + create(con))

            if path.startswith("/e/"):
                r = load(con, token=path[3:])
                if not r:
                    return self.send(view.page("Не найдено", '<div class="wrap">'
                                     '<p class="note">Ссылка не подходит. Возможно, '
                                     'резюме удалено.</p></div>'), 404)
                f, rf = kids(con, r["id"])
                return self.send(view.page("Анкета резюме",
                                           form.render(r, f, rf, qs.get("saved", "")),
                                           form.FORM_CSS))

            if path.startswith("/r/"):
                r = load(con, slug=path[3:].strip("/"))
                if not r:
                    return self.send(view.page("Не найдено", '<div class="wrap">'
                                     '<p class="note">Такого резюме нет.</p></div>'), 404)
                owner = qs.get("t") == r["token"]
                if r["status"] != "published" and not owner:
                    return self.send(view.page("Резюме скрыто", '<div class="wrap">'
                                     '<p class="note">Это резюме ещё не опубликовано.'
                                     '</p></div>'), 403)
                f, rf = kids(con, r["id"])
                return self.send(public(r, f, rf, owner))

            if path.startswith("/f/"):
                name = os.path.basename(path[3:])
                p = os.path.join(UPLOADS, name)
                if not os.path.isfile(p):
                    return self.send("нет файла", 404, "text/plain; charset=utf-8")
                ext = os.path.splitext(name)[1].lower()
                with open(p, "rb") as fh:
                    return self.send(fh.read(), 200,
                                     MIME.get(ext, "application/octet-stream"),
                                     {"Cache-Control": "private, max-age=3600"})

            if path == "/photo/del":
                r = load(con, token=qs.get("t", ""))
                if r:
                    if r["photo"]:
                        try:
                            os.remove(os.path.join(UPLOADS, r["photo"]))
                        except OSError:
                            pass
                    con.execute("UPDATE rezume SET photo='' WHERE id=?", (r["id"],))
                    con.commit()
                    return self.go(f"/e/{r['token']}")
                return self.send("нет", 404, "text/plain; charset=utf-8")

            if path == "/file/del":
                r = load(con, token=qs.get("t", ""))
                if r:
                    row = con.execute("SELECT * FROM files WHERE id=? AND rezume_id=?",
                                      (qs.get("id", "0"), r["id"])).fetchone()
                    if row:
                        try:
                            os.remove(os.path.join(UPLOADS, row["stored"]))
                        except OSError:
                            pass
                        con.execute("DELETE FROM files WHERE id=?", (row["id"],))
                        con.commit()
                    return self.go(f"/e/{r['token']}")
                return self.send("нет", 404, "text/plain; charset=utf-8")

            if path == "/admin":
                if not self.is_admin():
                    return self.send(ask_pass())
                return self.send(admin_page(con, qs.get("m", "")))

            if path == "/admin/act":
                if not self.is_admin():
                    return self.send(ask_pass())
                r = con.execute("SELECT * FROM rezume WHERE id=?",
                                (qs.get("id", "0"),)).fetchone()
                if r:
                    do = qs.get("do", "")
                    st = {"pub": "published", "back": "rejected", "hide": "draft"}.get(do)
                    if st:
                        con.execute("UPDATE rezume SET status=?, updated=? WHERE id=?",
                                    (st, now(), r["id"]))
                        con.commit()
                        m = {"published": "Опубликовано", "rejected": "Возвращено автору",
                             "draft": "Снято с публикации"}[st]
                        return self.go("/admin?m=" + urllib.parse.quote(m))
                return self.go("/admin")

            if path == "/healthz":
                return self.send("ok", 200, "text/plain; charset=utf-8")

            return self.send(view.page("Не найдено",
                                       '<div class="wrap"><p class="note">Страницы нет.</p></div>'), 404)
        finally:
            con.close()

    # ── POST ──
    def do_POST(self):
        path, qs = self.q()
        con = db()
        try:
            if path == "/save":
                r = load(con, token=qs.get("t", ""))
                if not r:
                    return self.send("нет", 404, "text/plain; charset=utf-8")
                d, files = self.read_form()
                if not d.get("consent_pd"):
                    return self.go(f"/e/{r['token']}?saved=" +
                                   urllib.parse.quote("Без согласия сохранить нельзя"))
                save_fields(con, r, d)
                r = load(con, token=r["token"])
                err = store_files(con, r, files)
                if d.get("send") and d.get("consent_pub"):
                    con.execute("UPDATE rezume SET status='sent', updated=? WHERE id=?",
                                (now(), r["id"]))
                    con.commit()
                    err = err or "Отправлено на проверку"
                return self.go(f"/e/{r['token']}?saved=" +
                               urllib.parse.quote(err or "ok"))

            if path == "/preview":
                r = load(con, token=qs.get("t", ""))
                if not r:
                    return self.send("", 404, "text/plain; charset=utf-8")
                d, _ = self.read_form()
                tmp = dict(r)
                for k in FIELDS:
                    tmp[k] = d.get(k, "")
                rf = [{"name": d.get(f"ref_name_{i}", ""), "role": d.get(f"ref_role_{i}", ""),
                       "text": d.get(f"ref_text_{i}", "")} for i in range(3)
                      if d.get(f"ref_text_{i}", "").strip() or d.get(f"ref_name_{i}", "").strip()]
                f, _old = kids(con, r["id"])
                return self.send(view.sheet(tmp, f, rf, photo_url(r)))

            if path == "/admin/login":
                d, _ = self.read_form()
                con2 = db()
                real = setting(con2, "admin_pass")
                if not real:
                    real = os.environ.get("REZUME_PASS", "")
                if real and d.get("p") == real:
                    sid = secrets.token_urlsafe(24)
                    set_setting(con2, "admin_sid", sid)
                    con2.close()
                    return self.go("/admin", {"Set-Cookie":
                                   f"sid={sid}; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800"})
                con2.close()
                return self.send(ask_pass("Пароль не подошёл"))

            return self.send("нет", 404, "text/plain; charset=utf-8")
        finally:
            con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()
    con = db()
    if not setting(con, "admin_pass") and os.environ.get("REZUME_PASS"):
        set_setting(con, "admin_pass", os.environ["REZUME_PASS"])
    con.close()
    print(f"  Резюме: http://{a.host}:{a.port}  ·  база {core.DB}")
    ThreadingHTTPServer((a.host, a.port), H).serve_forever()


if __name__ == "__main__":
    main()

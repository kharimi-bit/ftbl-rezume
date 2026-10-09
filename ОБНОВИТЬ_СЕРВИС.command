#!/bin/bash
# Обновляет сервис резюме на сервере. Двойной щелчок из Finder.
#
# 1. Код из этой папки → GitHub и /opt/ftbl-rezume, перезапуск службы.
# 2. Разовая правка 09.10.2026: в резюме Данила Красносвободцева
#    добавляются рекомендация Григория Агафонова и сертификат.
#    Повторный запуск ничего не дублирует.
# 3. Проверка: в открытом листе Данила нет контактов, есть кнопка запроса.
cd "$(dirname "$0")" || exit 1
SERVER=root@2.59.42.152
APP=/opt/ftbl-rezume
SLUG=krasnosvobodcev-danil-sergeevich
CERT="../Красносвободцев_Данил_Сергеевич/Выпуск/Сертификат_Красносвободцев_Данил_29сентября2026.pdf"

echo ""
echo "── Код в GitHub"
git push -q 2>/dev/null && echo "   ок" || echo "   GitHub не ответил — на сервер код всё равно уйдёт"

echo ""
echo "── Копирую код на сервер"
scp -q app.py core.py view.py form.py notify.py pay.py obrazec.py style.py "$SERVER:$APP/" \
  || { echo "   ✖ не скопировалось, сервер не тронут"; read -r; exit 1; }
[ -f "$CERT" ] && scp -q "$CERT" "$SERVER:/tmp/sertifikat_dk.pdf"
echo "   ок"

echo ""
echo "── Перезапускаю службу"
ssh $SERVER 'systemctl restart ftbl-rezume && sleep 1 && echo "   служба: $(systemctl is-active ftbl-rezume)"'

echo ""
echo "── Резюме Данила: рекомендация и сертификат"
ssh $SERVER "chmod 644 /tmp/sertifikat_dk.pdf 2>/dev/null; cd $APP && sudo -u www-data REZUME_DATA=/var/lib/ftbl-rezume python3 - ; rm -f /tmp/sertifikat_dk.pdf" <<'PY'
# -*- coding: utf-8 -*-
import os, sys, shutil
sys.path.insert(0, "/opt/ftbl-rezume")
import core

SLUG = "krasnosvobodcev-danil-sergeevich"
NOMER = "ФТБЛ-2026-0929-ДК"
FAJL = "Сертификат_Красносвободцев_Данил_29сентября2026.pdf"

con = core.db()
r = con.execute("SELECT * FROM rezume WHERE slug=?", (SLUG,)).fetchone()
if not r:
    raise SystemExit("   ✖ резюме Данила не найдено — ничего не менял")

prog = (r["programs"] or "").rstrip()
if NOMER not in prog:
    stroka = ("Сертификат № " + NOMER + ": трек «Скаутинг», итоговая работа "
              "принята куратором Григорием Агафоновым 29.09.2026")
    con.execute("UPDATE rezume SET programs=?, updated=? WHERE id=?",
                ((prog + "\n" + stroka).strip(), core.now(), r["id"]))
    print("   + сертификат строкой в «Программы и треки»")
else:
    print("   = сертификат строкой уже есть")

if not con.execute("SELECT 1 FROM refs WHERE rezume_id=? AND name LIKE ?",
                   (r["id"], "%Агафонов%")).fetchone():
    n = con.execute("SELECT COALESCE(MAX(ord),-1)+1 FROM refs WHERE rezume_id=?",
                    (r["id"],)).fetchone()[0]
    con.execute("INSERT INTO refs(rezume_id,name,role,text,ord) VALUES(?,?,?,?,?)", (
        r["id"], "Агафонов Григорий",
        "скаут ФК «Оренбург», куратор трека «Скаутинг»",
        "Умение чётко и качественно определять сильные и слабые стороны игрока "
        "и умение анализировать статистическую информацию. Мне кажется, он мог бы "
        "в молодёжном футболе на старте себя попробовать.", n))
    print("   + рекомендация Григория Агафонова")
else:
    print("   = рекомендация уже есть")

src = "/tmp/sertifikat_dk.pdf"
if os.path.exists(src) and not con.execute(
        "SELECT 1 FROM files WHERE rezume_id=? AND orig=?", (r["id"], FAJL)).fetchone():
    stored, kind = core.safe_name(FAJL)
    dst = os.path.join(core.UPLOADS, stored)
    try:
        shutil.copyfile(src, dst)
    except OSError as e:
        con.commit()
        raise SystemExit("   ✖ сертификат файлом не лёг: %s" % e)
    con.execute("INSERT INTO files(rezume_id,stored,orig,kind,size,added) "
                "VALUES(?,?,?,?,?,?)",
                (r["id"], stored, FAJL, kind, os.path.getsize(dst), core.now()))
    print("   + сертификат файлом в портфолио")
else:
    print("   = сертификат файлом уже есть или не скопировался")
con.commit()
PY

echo ""
echo "── Проверка открытого листа"
if curl -s "https://rezume.futbologik.ru/r/$SLUG" | grep -q "Запросить через редакцию"; then
  echo "   ✓ контактов в открытом листе нет, есть кнопка запроса"
else
  echo "   ✖ кнопки запроса нет — пришли этот экран в чат"
fi
echo ""
echo "Готово. Окно можно закрыть."
read -r

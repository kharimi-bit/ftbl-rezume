#!/bin/bash
# Включает уведомления о новых резюме в тот же бот, где CRM.
#
# Токен и номер чата уже лежат в базе CRM на сервере — здесь они только
# переносятся в настройки сервиса резюме. На мак ничего не скачивается,
# в переписку ничего не попадает, на экран токен не выводится.
#
# Запускать двойным щелчком из Finder. Повторный запуск ничего не портит.
SERVER=root@2.59.42.152

echo ""
echo "── Переношу настройки бота на сервере"
ssh $SERVER 'python3 - ' <<'REMOTE'
# -*- coding: utf-8 -*-
import json, os, shutil, sqlite3

CRM = "/var/ftbl/crm.db"          # база CRM: там настройки бота
OUT = "/opt/ftbl-rezume/notify.json"   # куда смотрит сервис резюме

con = sqlite3.connect("file:%s?mode=ro" % CRM, uri=True)
def get(k):
    r = con.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
    return (r[0] if r else "") or ""

tok, chat = get("tg_token"), get("tg_chat_id")
if not tok or not chat:
    raise SystemExit("   ✖ в базе CRM нет настроек бота (токен %s, чат %s).\n"
                     "     Значит и CRM сейчас не шлёт — сначала чиним её."
                     % ("есть" if tok else "пусто", "есть" if chat else "пусто"))

with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"token": tok, "chat": chat}, f)
os.chmod(OUT, 0o600)              # читать может только служба и root
shutil.chown(OUT, "www-data", "www-data")
print("   ок, настройки на месте (токен %d знаков, чат %s)" % (len(tok), chat))
REMOTE

echo ""
echo "── Перезапускаю службу и шлю пробное сообщение"
ssh $SERVER 'bash -s' <<'REMOTE'
systemctl restart ftbl-rezume
sleep 1
echo "   служба: $(systemctl is-active ftbl-rezume)"
cd /opt/ftbl-rezume && python3 - <<'PY'
# -*- coding: utf-8 -*-
import notify
if not notify.settings():
    raise SystemExit("   ✖ сервис настройки не видит")
notify._send("✅ Уведомления о новых резюме включены.\n"
             "Теперь сюда будет падать каждая анкета, "
             "отправленная на проверку.")
print("   пробное сообщение отправлено — проверьте бот")
PY
REMOTE

echo ""
echo "── Готово. Закройте окно."
echo ""

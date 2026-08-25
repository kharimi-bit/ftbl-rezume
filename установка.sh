#!/usr/bin/env bash
# Установка сервиса резюме на российский сервер.
# Запуск:  bash установка.sh rezume.futbologik.ru
#
# Ставит службу рядом с CRM, поднимает nginx и сертификат,
# включает ежедневную резервную копию базы и файлов.
# Повторный запуск безопасен: обновляет код и перезапускает службу.

set -euo pipefail
DOMAIN="${1:-}"
APP=/opt/ftbl-rezume
DATA=/var/lib/ftbl-rezume
PORT=8090

say(){ printf "\n\033[1;32m▸ %s\033[0m\n" "$1"; }
die(){ printf "\n\033[1;31m✖ %s\033[0m\n" "$1"; exit 1; }
[ "$(id -u)" = 0 ] || die "Запускать от root: sudo bash установка.sh $DOMAIN"

say "Проверяю Python"
python3 -c 'import sqlite3, http.server, secrets' 2>/dev/null \
  || die "Нет рабочего Python 3. Нужен Ubuntu 22.04 или новее."

say "Ставлю nginx и утилиты"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx ufw ca-certificates >/dev/null
[ -n "$DOMAIN" ] && apt-get install -y -qq certbot python3-certbot-nginx >/dev/null

say "Готовлю каталоги"
mkdir -p "$APP" "$DATA/uploads"
cp -f ./*.py "$APP"/ 2>/dev/null || die "Запускать из папки с файлами сервиса"
chown -R www-data:www-data "$DATA"
chmod 750 "$DATA"

# ─────────────────── пароль модератора ───────────────────
PASSFILE="$DATA/.pass"
if [ ! -f "$PASSFILE" ]; then
  PASS=$(python3 -c 'import secrets,string;a=string.ascii_letters+string.digits;print("".join(secrets.choice(a) for _ in range(14)))')
  printf '%s' "$PASS" > "$PASSFILE"
  chmod 600 "$PASSFILE"; chown www-data:www-data "$PASSFILE"
  NEWPASS=1
else
  PASS=$(cat "$PASSFILE"); NEWPASS=0
fi

say "Завожу службу"
cat > /etc/systemd/system/ftbl-rezume.service <<EOF
[Unit]
Description=FTBL Резюме
After=network-online.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$APP
Environment=REZUME_DATA=$DATA
Environment=REZUME_PASS=$PASS
ExecStart=/usr/bin/python3 $APP/app.py --host 127.0.0.1 --port $PORT
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$DATA

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now ftbl-rezume >/dev/null
systemctl restart ftbl-rezume
sleep 2
systemctl is-active --quiet ftbl-rezume || die "Служба не поднялась: journalctl -u ftbl-rezume -n 40"

say "Настраиваю веб-сервер"
SRV="${DOMAIN:-_}"
cat > /etc/nginx/sites-available/ftbl-rezume <<EOF
server {
    listen 80;
    server_name $SRV;

    # Портфолио — файлы до 25 МБ, анкета целиком до 200
    client_max_body_size 210m;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
}
EOF
ln -sf /etc/nginx/sites-available/ftbl-rezume /etc/nginx/sites-enabled/ftbl-rezume
rm -f /etc/nginx/sites-enabled/default
nginx -t >/dev/null 2>&1 || die "nginx не принял конфиг: nginx -t"
systemctl reload nginx

say "Закрываю лишние порты"
ufw allow OpenSSH >/dev/null 2>&1 || true
ufw allow 'Nginx Full' >/dev/null 2>&1 || true
ufw --force enable >/dev/null 2>&1 || true

if [ -n "$DOMAIN" ]; then
  say "Получаю сертификат для $DOMAIN"
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
    -m kharimi@gmail.com --redirect >/dev/null 2>&1 \
    && echo "  сертификат выдан" \
    || echo "  ⚠ сертификат не выдан — проверь, что А-запись $DOMAIN указывает сюда, потом: certbot --nginx -d $DOMAIN"
fi

say "Включаю ежедневную копию"
cat > /etc/cron.daily/ftbl-rezume-backup <<EOF
#!/bin/sh
D=$DATA/backup
mkdir -p "\$D"
sqlite3 $DATA/rezume.db ".backup '\$D/rezume-\$(date +%F).db'" 2>/dev/null || \
  cp $DATA/rezume.db "\$D/rezume-\$(date +%F).db"
tar -czf "\$D/uploads-\$(date +%F).tgz" -C $DATA uploads 2>/dev/null
find "\$D" -type f -mtime +14 -delete
EOF
chmod +x /etc/cron.daily/ftbl-rezume-backup

printf "\n\033[1;32m════ ГОТОВО ════\033[0m\n"
echo "  Адрес:     ${DOMAIN:+https://$DOMAIN}${DOMAIN:-http://$(hostname -I | awk '{print $1}')}"
echo "  Модерация: ${DOMAIN:+https://$DOMAIN}/admin"
if [ "$NEWPASS" = 1 ]; then
  echo "  Пароль:    $PASS"
  echo "  ↑ запиши сейчас, второй раз он не покажется"
else
  echo "  Пароль:    прежний, лежит в $PASSFILE"
fi
echo "  Данные:    $DATA  (копии — $DATA/backup, хранятся 14 дней)"
echo "  Логи:      journalctl -u ftbl-rezume -f"

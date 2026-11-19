#!/bin/sh
# Yetkilendirme penceresi, yalnızca XFCE oturumu için çalışır.
# Paketlerin eski/yeni libexec yerleşimlerini ve iki mimariyi destekle.
set -eu
for agent in \
    /usr/lib/mate-polkit/polkit-mate-authentication-agent-1 \
    /usr/libexec/polkit-mate-authentication-agent-1 \
    /usr/libexec/mate-polkit/polkit-mate-authentication-agent-1 \
    /usr/lib/*-linux-gnu/mate-polkit/polkit-mate-authentication-agent-1; do
    if [ -x "$agent" ]; then exec "$agent"; fi
done
printf 'OğuzDows yetkilendirme aracısı bulunamadı.\n' >&2
exit 1

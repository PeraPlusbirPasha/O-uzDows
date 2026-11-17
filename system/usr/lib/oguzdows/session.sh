#!/bin/sh
# Yalnızca bu oturumun görünümünü ayarlar; ağ isteği ve root yetkisi yoktur.
set -eu
sleep 1
WP=/usr/share/backgrounds/oguzdows/wallpaper.png
set_value() {
    xfconf-query -c "$1" -p "$2" -s "$4" 2>/dev/null || \
        xfconf-query -c "$1" -p "$2" -n -t "$3" -s "$4" 2>/dev/null || true
}
MEMORY_KB=$(awk '/^MemTotal:/ { print $2 }' /proc/meminfo)
LIGHT=false
if [ "${MEMORY_KB:-0}" -le 2097152 ]; then LIGHT=true; fi
case " $(cat /proc/cmdline) " in
    *' oguzdows.profile=light '*|*' nomodeset '*) LIGHT=true ;;
esac
if "$LIGHT"; then
    set_value xfwm4 /general/use_compositing bool false
    set_value xsettings /Gtk/EnableAnimations bool false
fi
# Xfce'nin gerçekten oluşturduğu monitör/çalışma alanı yollarını kullan.
xfconf-query -c xfce4-desktop -l 2>/dev/null | \
    grep -E '^/backdrop/.*/last-image$' | while IFS= read -r property; do
        set_value xfce4-desktop "$property" string "$WP"
        set_value xfce4-desktop "${property%/last-image}/image-style" int 5
    done
for monitor in $(xrandr 2>/dev/null | awk '/ connected/ { print $1 }') 0; do
    for workspace in 0 1 2 3; do
        prefix="/backdrop/screen0/monitor$monitor/workspace$workspace"
        set_value xfce4-desktop "$prefix/last-image" string "$WP"
        set_value xfce4-desktop "$prefix/image-style" int 5
    done
done
exit 0

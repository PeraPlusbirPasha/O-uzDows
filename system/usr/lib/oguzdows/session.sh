#!/bin/sh
# Yalnızca bu oturumun görünümünü ayarlar; ağ isteği ve root yetkisi yoktur.
set -eu
sleep 1
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
# Yalnızca ilk girişte uygula; sonraki girişler kullanıcının seçimini korur.
python3 /usr/lib/oguzdows/wallpapers.py --initialize
exit 0

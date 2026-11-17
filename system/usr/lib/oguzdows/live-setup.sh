#!/bin/sh
# Bu yardımcı kurulu sisteme bir canlı kullanıcı ASLA eklememelidir.
set -eu
case " $(cat /proc/cmdline) " in
    *' boot=live '*) ;;
    *) exit 0 ;;
esac
if ! getent passwd oguz >/dev/null; then
    useradd -m -s /bin/bash -c 'OğuzDows Canlı Oturum' oguz
fi
usermod -c 'OğuzDows Canlı Oturum' oguz
printf 'oguz:oguz\n' | chpasswd
for group in sudo audio video plugdev netdev cdrom dip lpadmin scanner bluetooth; do
    if getent group "$group" >/dev/null; then usermod -aG "$group" oguz; fi
done
install -d -m 0755 /etc/sudoers.d /etc/lightdm/lightdm.conf.d
printf 'oguz ALL=(ALL:ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/oguzdows-live
chmod 0440 /etc/sudoers.d/oguzdows-live
cat > /etc/lightdm/lightdm.conf.d/99-oguzdows-live.conf <<'CONF'
[Seat:*]
autologin-user=oguz
autologin-user-timeout=0
user-session=oguzdows
CONF

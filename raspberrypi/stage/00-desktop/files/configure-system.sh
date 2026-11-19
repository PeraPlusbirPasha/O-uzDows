#!/bin/bash
set -euo pipefail
# pi-gen'in geçici hesabı hiçbir zaman dağıtılmaz.
if id oguz-build >/dev/null 2>&1; then
    userdel --remove oguz-build
fi
usermod --lock root
rm -f /etc/sudoers.d/010_pi-nopasswd /etc/sudoers.d/010_wiz-nopasswd \
    /etc/sudoers.d/oguzdows-live /etc/xdg/autostart/piwiz.desktop
# Zram varken SD üzerinde sürekli swap dosyası çalıştırma.
systemctl disable dphys-swapfile.service
systemctl mask dphys-swapfile.service
rm -f /var/swap
systemctl disable ssh.service
systemctl disable NetworkManager-wait-online.service
systemctl enable NetworkManager.service lightdm.service bluetooth.service zramswap.service \
    oguzdows-pi-tune.service oguzdows-pi-firstboot.service
systemctl set-default graphical.target
printf '/usr/sbin/lightdm\n' > /etc/X11/default-display-manager
if [ -z "$(dpkg-divert --list /usr/lib/os-release)" ]; then
    dpkg-divert --local --add --rename --divert /usr/lib/os-release.upstream /usr/lib/os-release
fi
install -m 0644 /usr/share/oguzdows/os-release /usr/lib/os-release
ln -sfn ../usr/lib/os-release /etc/os-release
locale-gen
update-locale LANG=tr_TR.UTF-8 LANGUAGE=tr:en
ln -sfn /usr/share/zoneinfo/Europe/Istanbul /etc/localtime
python3 /usr/lib/oguzdows/render-assets.py --root /
install -d /usr/share/icons/hicolor/scalable/apps
install -m 0644 /usr/share/oguzdows/assets/oguzdows.svg /usr/share/icons/hicolor/scalable/apps/oguzdows.svg
gtk-update-icon-cache -f -t /usr/share/icons/hicolor
plymouth-set-default-theme oguzdows
# Sonraki çekirdek güncellemeleri de bütün Pi modelleri için modülleri korusun.
install -d /etc/initramfs-tools/conf.d
printf 'MODULES=most\n' > /etc/initramfs-tools/conf.d/oguzdows-pi
# Standart DRM/KMS, kamera ve DSI algılama resmî pi-gen config'inden korunur.
printf '\n[all]\n# OğuzDows: üretici sınırları içinde, overclock yok.\ndisable_splash=1\ninclude oguzdows-config.txt\n' >> /boot/firmware/config.txt
printf '# Kullanıcıya ait ek Pi firmware ayarları.\n[all]\n' > /boot/firmware/oguzdows-config.txt
python3 - <<'PY'
from pathlib import Path
path = Path('/boot/firmware/cmdline.txt')
args = path.read_text().split()
for arg in ('quiet', 'splash', 'logo.nologo', 'plymouth.ignore-serial-consoles'):
    if arg not in args:
        args.append(arg)
path.write_text(' '.join(args) + '\n')
PY
# Derleme anındaki donanıma göre profil uygulanmaz; gerçek Pi açılışında seçilir.
install -d -m 0700 /var/lib/oguzdows
rm -f /var/lib/oguzdows/firstboot.done /var/lib/oguzdows/firstboot.pending.json

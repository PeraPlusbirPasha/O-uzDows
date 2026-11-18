#!/bin/sh
# Calamares shellprocess modülü bunu HEDEF sistemin chroot'u içinde çalıştırır.
# users modülünden ÖNCE çalışır; yeni kullanıcının tercihlerini değiştirmez.
set -eu
systemctl disable oguzdows-live-setup.service
rm -f /etc/systemd/system/oguzdows-live-setup.service \
      /usr/lib/oguzdows/live-setup.sh \
      /etc/sudoers.d/oguzdows-live /etc/sudoers.d/live \
      /etc/lightdm/lightdm.conf.d/99-oguzdows-live.conf \
      /etc/lightdm/lightdm.conf.d/90-live-config.conf
# Canlı oturumun otomatik girişi farklı bir LightDM dosyasına da yazılmış olabilir.
for conf in /etc/lightdm/lightdm.conf /etc/lightdm/lightdm.conf.d/*.conf; do
    [ -f "$conf" ] || continue
    sed -i -E '/^[[:space:]]*autologin-(user|user-timeout)[[:space:]]*=/d' "$conf"
done
rm -f /usr/share/applications/oguzdows-install.desktop \
      /usr/local/sbin/oguzdows-installer \
      /usr/local/bin/oguzdows-install \
      /usr/lib/oguzdows/prepare-install.py \
      /usr/share/polkit-1/actions/org.oguzdows.install.policy \
      /etc/skel/Masaüstü/oguzdows-install.desktop
# Uyumluluk seçeneğiyle kuran kullanıcı ilk disk açılışında yeniden siyah ekran görmesin.
# Yalnızca tanıdığımız sabit parametreleri taşı; canlı ortamın boot=live vb. değerlerini alma.
COMPAT_ARGS=
case " $(cat /proc/cmdline) " in
    *' nomodeset '*) COMPAT_ARGS=' nomodeset' ;;
esac
case " $(cat /proc/cmdline) " in
    *' oguzdows.profile=light '*) COMPAT_ARGS="$COMPAT_ARGS oguzdows.profile=light" ;;
esac
if [ -n "$COMPAT_ARGS" ]; then
    install -d /etc/default/grub.d
    # Değişken bu betikte değil, GRUB yapılandırması okunurken açılmalı.
    # shellcheck disable=SC2016
    printf 'GRUB_CMDLINE_LINUX_DEFAULT="${GRUB_CMDLINE_LINUX_DEFAULT}%s plymouth.enable=0"\n' "$COMPAT_ARGS" \
        > /etc/default/grub.d/60-oguzdows-compat.cfg
fi
# networkcfg, machineid ve displaymanager bundan sonra kendi ayarlarını yazar.
exit 0

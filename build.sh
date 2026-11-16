#!/usr/bin/env bash
# OğuzDows - eski bilgisayarlar için hafif, macOS görünümlü Debian tabanlı live + kurulum ISO'su
#
# Kullanım:  sudo ./build.sh amd64     (64 bit ISO)
#            sudo ./build.sh i386      (32 bit ISO)
# Gereksinim: Debian 12/13 (veya debian:trixie konteyneri), internet bağlantısı
#             sudo apt install live-build debootstrap squashfs-tools xorriso \
#                              syslinux syslinux-utils isolinux git ca-certificates
set -euo pipefail

ARCH="${1:-amd64}"

case "$ARCH" in
  amd64) SUITE="trixie";   FLAVOUR="amd64"   ;;
  # Debian 13 (trixie) 32 bit çekirdeği bıraktı; i386 için bookworm kullanılır.
  i386)  SUITE="bookworm"; FLAVOUR="686-pae" ;;
  *) echo "Kullanım: $0 [amd64|i386]"; exit 1 ;;
esac

[ "$(id -u)" -eq 0 ] || { echo "root olarak çalıştırın (sudo)."; exit 1; }
command -v lb >/dev/null || { echo "live-build kurulu değil: apt install live-build"; exit 1; }

HERE="$(pwd)"
WORK="$HERE/build-$ARCH"
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

# ---------------------------------------------------------------
# 1) Temel yapılandırma
#    Canlı ISO'da GRUB yok: syslinux/isolinux ile BIOS'tan açılır.
# ---------------------------------------------------------------
lb config \
  --distribution "$SUITE" \
  --architectures "$ARCH" \
  --linux-flavours "$FLAVOUR" \
  --archive-areas "main contrib non-free non-free-firmware" \
  --bootloaders syslinux \
  --binary-images iso-hybrid \
  --debian-installer none \
  --apt-recommends false \
  --iso-volume "OGUZDOWS" \
  --iso-application "OguzDows" \
  --iso-publisher "Oguz" \
  --memtest none \
  --bootappend-live "boot=live components quiet splash hostname=oguzdows username=oguz locales=tr_TR.UTF-8 keyboard-layouts=tr timezone=Europe/Istanbul"

# ---------------------------------------------------------------
# 2) Paket listesi
# ---------------------------------------------------------------
mkdir -p config/package-lists
cat > config/package-lists/oguzdows.list.chroot <<'EOF'
# Masaüstü
xorg
xfce4
xfce4-terminal
xfce4-settings
xfce4-session
xfce4-notifyd
xfce4-power-manager
xfce4-whiskermenu-plugin
xfce4-pulseaudio-plugin
lightdm
lightdm-gtk-greeter
dbus-x11
thunar
thunar-volman
mousepad
file-roller
ristretto
network-manager
network-manager-gnome
gvfs
gvfs-backends
pavucontrol
pulseaudio
sudo
fonts-noto-core
fonts-noto-color-emoji

# Mac görünümü için
plank
gtk2-engines-murrine
gnome-themes-extra
sassc
libglib2.0-dev-bin
libxml2-utils
imagemagick
git
curl
ca-certificates

# Güncel uygulamalar
firefox-esr
firefox-esr-l10n-tr
libreoffice-writer
libreoffice-calc
libreoffice-impress
libreoffice-gtk3
libreoffice-l10n-tr
vlc
flatpak

# Eski donanım için
zram-tools
preload

# Kurulum arayüzü (Calamares) ve disk araçları
calamares
calamares-settings-debian
grub-pc
os-prober
parted
gdisk
dosfstools
e2fsprogs
ntfs-3g
rsync
squashfs-tools

# Kablosuz ve diğer sürücüler
firmware-linux
firmware-iwlwifi
firmware-realtek
firmware-atheros
firmware-brcm80211
firmware-misc-nonfree
EOF

# ---------------------------------------------------------------
# 3) Masaüstü ayarları (macOS tarzı): üstte ince panel, altta dock,
#    pencere düğmeleri solda, WhiteSur tema/ikon/imleç
# ---------------------------------------------------------------
SKEL=config/includes.chroot/etc/skel
XF="$SKEL/.config/xfce4/xfconf/xfce-perchannel-xml"
mkdir -p "$XF" "$SKEL/.config/autostart" "$SKEL/Desktop" \
         "$SKEL/.config/plank/dock1/launchers" \
         config/includes.chroot/usr/local/bin \
         config/includes.chroot/etc/default

cat > "$XF/xsettings.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xsettings" version="1.0">
  <property name="Net" type="empty">
    <property name="ThemeName" type="string" value="WhiteSur-Light"/>
    <property name="IconThemeName" type="string" value="WhiteSur"/>
  </property>
  <property name="Gtk" type="empty">
    <property name="CursorThemeName" type="string" value="WhiteSur-cursors"/>
    <property name="FontName" type="string" value="Noto Sans 10"/>
  </property>
</channel>
EOF

cat > "$XF/xfwm4.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="WhiteSur-Light"/>
    <property name="button_layout" type="string" value="CHM|"/>
    <property name="title_alignment" type="string" value="center"/>
    <property name="use_compositing" type="bool" value="true"/>
    <property name="show_dock_shadow" type="bool" value="true"/>
    <property name="show_frame_shadow" type="bool" value="true"/>
  </property>
</channel>
EOF

cat > "$XF/xfce4-panel.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="configver" type="int" value="2"/>
  <property name="panels" type="array">
    <value type="int" value="1"/>
    <property name="panel-1" type="empty">
      <property name="position" type="string" value="p=6;x=0;y=0"/>
      <property name="length" type="uint" value="100"/>
      <property name="position-locked" type="bool" value="true"/>
      <property name="size" type="uint" value="28"/>
      <property name="plugin-ids" type="array">
        <value type="int" value="1"/>
        <value type="int" value="2"/>
        <value type="int" value="3"/>
        <value type="int" value="4"/>
        <value type="int" value="5"/>
      </property>
    </property>
  </property>
  <property name="plugins" type="empty">
    <property name="plugin-1" type="string" value="whiskermenu">
      <property name="button-title" type="string" value="OğuzDows"/>
      <property name="show-button-title" type="bool" value="true"/>
      <property name="show-button-icon" type="bool" value="false"/>
    </property>
    <property name="plugin-2" type="string" value="separator">
      <property name="expand" type="bool" value="true"/>
      <property name="style" type="uint" value="0"/>
    </property>
    <property name="plugin-3" type="string" value="systray"/>
    <property name="plugin-4" type="string" value="pulseaudio"/>
    <property name="plugin-5" type="string" value="clock">
      <property name="mode" type="uint" value="2"/>
      <property name="digital-layout" type="uint" value="3"/>
      <property name="digital-time-format" type="string" value="%a %e %b  %H:%M"/>
    </property>
  </property>
</channel>
EOF

# Dock (Plank) otomatik başlasın
cat > "$SKEL/.config/autostart/plank.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Dock
Exec=plank
X-GNOME-Autostart-enabled=true
EOF

# Dock simgeleri
mkdock() {
  printf '[PlankDockItemPreferences]\nLauncher=file:///usr/share/applications/%s.desktop\n' "$2" \
    > "$SKEL/.config/plank/dock1/launchers/$1.dockitem"
}
mkdock 01-files     thunar
mkdock 02-firefox   firefox-esr
mkdock 03-writer    libreoffice-writer
mkdock 04-vlc       vlc
mkdock 05-terminal  xfce4-terminal
mkdock 06-install   oguzdows-install

# Masaüstü duvar kağıdı ilk oturumda uygulanır
cat > config/includes.chroot/usr/local/bin/oguzdows-wallpaper <<'EOF'
#!/bin/sh
sleep 3
for p in $(xfconf-query -c xfce4-desktop -l 2>/dev/null | grep last-image); do
  xfconf-query -c xfce4-desktop -p "$p" -s /usr/share/backgrounds/oguzdows.png
done
EOF
chmod +x config/includes.chroot/usr/local/bin/oguzdows-wallpaper
cat > "$SKEL/.config/autostart/oguzdows-wallpaper.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Wallpaper
Exec=/usr/local/bin/oguzdows-wallpaper
X-GNOME-Autostart-enabled=true
EOF

# ---------------------------------------------------------------
# 4) Kurulum arayüzü (Calamares) kısayolları
# ---------------------------------------------------------------
mkdir -p config/includes.chroot/usr/share/applications
cat > config/includes.chroot/usr/share/applications/oguzdows-install.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=OğuzDows'u Kur
Comment=OğuzDows'u bilgisayarın diskine kur
Exec=sudo -E calamares
Icon=calamares
Terminal=false
Categories=System;
EOF
cp config/includes.chroot/usr/share/applications/oguzdows-install.desktop \
   "$SKEL/Desktop/OguzDows-Kur.desktop"

# ---------------------------------------------------------------
# 5) Chroot kancaları: markalama, WhiteSur teması, duvar kağıdı
# ---------------------------------------------------------------
mkdir -p config/hooks/live

cat > config/hooks/live/0100-branding.hook.chroot <<'EOF'
#!/bin/sh
set -e
# ID=debian korunur (araçlar uyumlu kalsın), görünen ad değişir
sed -i 's/^PRETTY_NAME=.*/PRETTY_NAME="OğuzDows"/; s/^NAME=.*/NAME="OğuzDows"/' /etc/os-release
echo "OğuzDows \\n \\l" > /etc/issue
echo "OğuzDows" > /etc/issue.net
chmod +x /etc/skel/Desktop/*.desktop || true
# Flathub deposunu ekle (güncel uygulamalar için)
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo || true
EOF

cat > config/hooks/live/0200-macos-theme.hook.chroot <<'EOF'
#!/bin/sh
# WhiteSur (macOS tarzı) GTK/ikon/imleç temalarını GitHub'dan kurar.
# Ağ yoksa derleme kırılmaz; varsayılan tema kalır.
set -e
T=/tmp/oguzdows-theme
mkdir -p "$T"
cd "$T"
if git clone --depth=1 https://github.com/vinceliuice/WhiteSur-gtk-theme.git gtk \
 && git clone --depth=1 https://github.com/vinceliuice/WhiteSur-icon-theme.git icons \
 && git clone --depth=1 https://github.com/vinceliuice/WhiteSur-cursors.git cursors; then
  (cd gtk    && ./install.sh -d /usr/share/themes -c Light -t default) || echo "GTK teması kurulamadı"
  (cd icons  && ./install.sh -d /usr/share/icons)                       || echo "İkon teması kurulamadı"
  (mkdir -p /usr/share/icons && cp -r cursors/dist /usr/share/icons/WhiteSur-cursors) || echo "İmleç teması kurulamadı"
else
  echo "UYARI: WhiteSur indirilemedi, varsayılan tema kullanılacak."
fi
cd /
rm -rf "$T"

# Duvar kağıdı
mkdir -p /usr/share/backgrounds
(convert -size 1920x1080 gradient:'#2b1055-#d53369' /usr/share/backgrounds/oguzdows.png \
  || magick -size 1920x1080 gradient:'#2b1055-#d53369' /usr/share/backgrounds/oguzdows.png) || true
EOF

# --- Giriş garantisi: kullanıcı oguz / şifre oguz + otomatik giriş ---
# live-config'in kullanıcı/otomatik giriş ayarına güvenmek yerine, açılışta
# (ekran yöneticisinden önce) kendi servisimiz hesabı garanti eder.
mkdir -p config/includes.chroot/etc/systemd/system config/includes.chroot/etc/sudoers.d

cat > config/includes.chroot/usr/local/bin/oguzdows-fixlogin <<'EOF'
#!/bin/sh
# Her açılışta çalışır: kullanıcıyı, şifreyi ve otomatik girişi garanti eder.
U=oguz
getent group nopasswdlogin >/dev/null || groupadd -r nopasswdlogin
if ! getent passwd "$U" >/dev/null; then
  useradd -m -s /bin/bash -c "Oguz" "$U"
fi
echo "$U:oguz" | chpasswd
for g in sudo audio video plugdev netdev cdrom dip floppy lpadmin scanner bluetooth nopasswdlogin; do
  getent group "$g" >/dev/null && usermod -aG "$g" "$U"
done
echo "$U ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/oguzdows
chmod 440 /etc/sudoers.d/oguzdows
mkdir -p /etc/lightdm/lightdm.conf.d
cat > /etc/lightdm/lightdm.conf.d/50-oguzdows.conf <<EOC
[Seat:*]
autologin-user=$U
autologin-user-timeout=0
user-session=xfce
EOC
exit 0
EOF
chmod +x config/includes.chroot/usr/local/bin/oguzdows-fixlogin

cat > config/includes.chroot/etc/systemd/system/oguzdows-fixlogin.service <<'EOF'
[Unit]
Description=OguzDows kullanici ve otomatik giris ayari
After=live-config.service
Before=display-manager.service lightdm.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/oguzdows-fixlogin
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

cat > config/hooks/live/0300-login.hook.chroot <<'EOF'
#!/bin/sh
set -e
systemctl enable oguzdows-fixlogin.service
EOF

# Klavye: Türkçe Q (giriş ekranı dahil)
cat > config/includes.chroot/etc/default/keyboard <<'EOF'
XKBMODEL="pc105"
XKBLAYOUT="tr"
XKBVARIANT=""
XKBOPTIONS=""
BACKSPACE="guess"
EOF

chmod +x config/hooks/live/*.hook.chroot

# zram: RAM'i sıkıştırarak eski makinelerde takılmayı azaltır
cat > config/includes.chroot/etc/default/zramswap <<'EOF'
ALGO=lz4
PERCENT=50
EOF

# ---------------------------------------------------------------
# 6) ISO'yu üret
# ---------------------------------------------------------------
lb build 2>&1 | tee build.log

ISO="$(ls -1 *.iso 2>/dev/null | head -n1 || true)"
if [ -n "$ISO" ]; then
  mv "$ISO" "$HERE/OguzDows-$ARCH.iso"
  (cd "$HERE" && sha256sum "OguzDows-$ARCH.iso" > "OguzDows-$ARCH.iso.sha256")
  echo "Hazır: $HERE/OguzDows-$ARCH.iso"
else
  echo "ISO üretilemedi, build.log dosyasına bakın."
  exit 1
fi

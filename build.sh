#!/usr/bin/env bash
# OğuzDows - eski bilgisayarlar için hafif, macOS görünümlü Debian tabanlı live + kurulum ISO'su
#
# Kullanım:  sudo ./build.sh amd64     (64 bit ISO)
#            sudo ./build.sh i386      (32 bit ISO)
# Gereksinim: Debian 12/13 (veya debian:trixie konteyneri), internet bağlantısı
#             apt install live-build debootstrap squashfs-tools xorriso \
#                         syslinux syslinux-utils isolinux git ca-certificates
#
# Giriş bilgileri:  kullanıcı oguz / şifre oguz  (otomatik giriş açık)
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

# Çekirdek parametreleri (ISO menüsü de aynısını kullanır)
BOOTAPPEND="boot=live components quiet splash hostname=oguzdows username=oguz locales=tr_TR.UTF-8 keyboard-layouts=tr timezone=Europe/Istanbul"

HERE="$(pwd)"
WORK="$HERE/build-$ARCH"
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

# ---------------------------------------------------------------
# 1) Temel yapılandırma
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
  --firmware-chroot true \
  --firmware-binary true \
  --iso-volume "OGUZDOWS" \
  --iso-application "OguzDows" \
  --iso-publisher "Oguz" \
  --memtest none \
  --bootappend-live "$BOOTAPPEND"

# ---------------------------------------------------------------
# 2) Paket listesi
# ---------------------------------------------------------------
mkdir -p config/package-lists
cat > config/package-lists/oguzdows.list.chroot <<'EOF'
# --- Masaüstü ---
xorg
x11-xserver-utils
xserver-xorg-input-libinput
xfce4
xfce4-terminal
xfce4-settings
xfce4-session
xfce4-notifyd
xfce4-power-manager
xfce4-power-manager-plugins
xfce4-whiskermenu-plugin
xfce4-pulseaudio-plugin
lightdm
lightdm-gtk-greeter
dbus-x11
dconf-cli
thunar
thunar-volman
mousepad
file-roller
ristretto
gvfs
gvfs-backends
sudo
procps
libpam-systemd
dbus-user-session

# --- Ağ / Wi-Fi / Bluetooth ---
network-manager
network-manager-gnome
wpasupplicant
wireless-regdb
iw
rfkill
usb-modeswitch
bluez
blueman

# --- Ses ---
alsa-utils
pulseaudio
pulseaudio-utils
pavucontrol
sox

# --- Yazı tipleri ---
fonts-inter
fonts-noto-core
fonts-noto-color-emoji

# --- Mac görünümü ---
plank
plymouth
plymouth-themes
gtk2-engines-murrine
gnome-themes-extra
qt5-gtk-platformtheme
sassc
libglib2.0-dev-bin
libxml2-utils
imagemagick
fontconfig
git
curl
ca-certificates

# --- Güncel uygulamalar ---
firefox-esr
firefox-esr-l10n-tr
libreoffice-writer
libreoffice-calc
libreoffice-impress
libreoffice-gtk3
libreoffice-l10n-tr
vlc
flatpak

# --- Eski donanım için ---
zram-tools
preload
intel-microcode

# --- Kurulum arayüzü (Calamares) ve disk araçları ---
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

# --- Sürücü yazılımları (firmware) ---
firmware-linux
firmware-misc-nonfree
firmware-iwlwifi
firmware-realtek
firmware-atheros
firmware-brcm80211
firmware-amd-graphics
firmware-intel-graphics
EOF

if [ "$SUITE" = "trixie" ]; then
  printf '%s\n' firmware-intel-sound polkitd pkexec \
    >> config/package-lists/oguzdows.list.chroot
else
  printf '%s\n' policykit-1 >> config/package-lists/oguzdows.list.chroot
fi

# ---------------------------------------------------------------
# 3) Masaüstü ayarları (macOS tarzı üst panel ve tema)
# ---------------------------------------------------------------
SKEL=config/includes.chroot/etc/skel
XF="$SKEL/.config/xfce4/xfconf/xfce-perchannel-xml"
mkdir -p "$XF" "$SKEL/.config/autostart" "$SKEL/.config/gtk-3.0" "$SKEL/Desktop" \
         "$SKEL/.config/plank/dock1/launchers" \
         config/includes.chroot/usr/local/bin \
         config/includes.chroot/etc/default \
         config/includes.chroot/etc/dconf/db/local.d \
         config/includes.chroot/etc/dconf/profile \
         config/includes.chroot/etc/lightdm \
         config/includes.chroot/etc/X11/xorg.conf.d

cat > "$XF/xsettings.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xsettings" version="1.0">
  <property name="Net" type="empty">
    <property name="ThemeName" type="string" value="WhiteSur-Light"/>
    <property name="IconThemeName" type="string" value="WhiteSur"/>
    <property name="EnableEventSounds" type="bool" value="false"/>
  </property>
  <property name="Gtk" type="empty">
    <property name="CursorThemeName" type="string" value="WhiteSur-cursors"/>
    <property name="FontName" type="string" value="Inter 10"/>
    <property name="MonospaceFontName" type="string" value="Monospace 10"/>
  </property>
  <property name="Xft" type="empty">
    <property name="Antialias" type="int" value="1"/>
    <property name="Hinting" type="int" value="1"/>
    <property name="HintStyle" type="string" value="hintslight"/>
    <property name="RGBA" type="string" value="rgb"/>
  </property>
</channel>
EOF

cat > "$XF/xfwm4.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="WhiteSur-Light"/>
    <property name="title_font" type="string" value="Inter Semi-Bold 10"/>
    <property name="button_layout" type="string" value="CHM|"/>
    <property name="title_alignment" type="string" value="center"/>
    <property name="use_compositing" type="bool" value="true"/>
    <property name="show_dock_shadow" type="bool" value="true"/>
    <property name="show_frame_shadow" type="bool" value="true"/>
    <property name="show_popup_shadow" type="bool" value="true"/>
    <property name="shadow_opacity" type="int" value="60"/>
    <property name="frame_opacity" type="int" value="100"/>
    <property name="double_click_action" type="string" value="maximize"/>
  </property>
</channel>
EOF

# Garanti üst panel yerleşimi
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
      <property name="background-style" type="uint" value="0"/>
      <property name="plugin-ids" type="array">
        <value type="int" value="1"/>
        <value type="int" value="2"/>
        <value type="int" value="6"/>
        <value type="int" value="3"/>
        <value type="int" value="4"/>
        <value type="int" value="8"/>
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
    <property name="plugin-6" type="string" value="statusnotifier"/>
    <property name="plugin-8" type="string" value="power-manager-plugin"/>
  </property>
</channel>
EOF

cat > config/includes.chroot/etc/X11/xorg.conf.d/40-touchpad.conf <<'EOF'
Section "InputClass"
    Identifier "OguzDows touchpad"
    MatchIsTouchpad "on"
    Driver "libinput"
    Option "Tapping" "on"
    Option "NaturalScrolling" "true"
    Option "DisableWhileTyping" "on"
    Option "ClickMethod" "clickfinger"
EndSection
EOF

cat > "$SKEL/.config/gtk-3.0/settings.ini" <<'EOF'
[Settings]
gtk-theme-name=WhiteSur-Light
gtk-icon-theme-name=WhiteSur
gtk-cursor-theme-name=WhiteSur-cursors
gtk-font-name=Inter 10
gtk-application-prefer-dark-theme=0
EOF

cat > "$SKEL/.config/gtk-3.0/gtk.css" <<'EOF'
.xfce4-panel.background {
  background-color: rgba(246, 246, 248, 0.85);
  color: #1d1d1f;
  border-bottom: 1px solid rgba(0, 0, 0, 0.15);
}
.xfce4-panel button, .xfce4-panel label {
  color: #1d1d1f;
  font-weight: 600;
}
EOF

cat > config/includes.chroot/etc/environment <<'EOF'
QT_QPA_PLATFORMTHEME=gtk2
EOF

cat > config/includes.chroot/etc/lightdm/lightdm-gtk-greeter.conf <<'EOF'
[greeter]
background=/usr/share/backgrounds/oguzdows.png
theme-name=WhiteSur-Light
icon-theme-name=WhiteSur
cursor-theme-name=WhiteSur-cursors
font-name=Inter 11
clock-format=%a %e %b  %H:%M
indicators=~host;~spacer;~clock;~spacer;~session;~language;~a11y;~power
user-background=false
EOF

cat > config/includes.chroot/etc/dconf/profile/user <<'EOF'
user-db:user
system-db:local
EOF
cat > config/includes.chroot/etc/dconf/db/local.d/00-oguzdows <<'EOF'
[net/launchpad/plank/docks/dock1]
dock-items=['01-files.dockitem','02-firefox.dockitem','03-writer.dockitem','04-vlc.dockitem','05-terminal.dockitem','06-install.dockitem']
icon-size=52
zoom-enabled=true
zoom-percent=150
theme='Transparent'
hide-mode='window-dodge'
position='bottom'
alignment='center'
items-alignment='center'
EOF

cat > "$SKEL/.config/autostart/plank.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Dock
Exec=plank
X-GNOME-Autostart-enabled=true
EOF

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

cat > config/includes.chroot/usr/local/bin/oguzdows-wallpaper <<'EOF'
#!/bin/sh
sleep 2
WP=/usr/share/backgrounds/oguzdows.png
for m in $(xrandr 2>/dev/null | awk '/ connected/{print $1}') 0; do
  for w in 0 1 2 3; do
    P="/backdrop/screen0/monitor$m/workspace$w"
    xfconf-query -c xfce4-desktop -p "$P/last-image" -n -t string -s "$WP" 2>/dev/null \
      || xfconf-query -c xfce4-desktop -p "$P/last-image" -s "$WP" 2>/dev/null
    xfconf-query -c xfce4-desktop -p "$P/image-style" -n -t int -s 5 2>/dev/null \
      || xfconf-query -c xfce4-desktop -p "$P/image-style" -s 5 2>/dev/null
  done
done
exit 0
EOF
chmod +x config/includes.chroot/usr/local/bin/oguzdows-wallpaper
cat > "$SKEL/.config/autostart/oguzdows-wallpaper.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Wallpaper
Exec=/usr/local/bin/oguzdows-wallpaper
X-GNOME-Autostart-enabled=true
EOF

cat > config/includes.chroot/usr/local/bin/oguzdows-chime <<'EOF'
#!/bin/sh
sleep 2
amixer -q sset Master unmute 2>/dev/null
amixer -q sset Master 70% 2>/dev/null
amixer -q sset Speaker unmute 2>/dev/null
paplay /usr/share/sounds/oguzdows/startup.wav 2>/dev/null
exit 0
EOF
chmod +x config/includes.chroot/usr/local/bin/oguzdows-chime
cat > "$SKEL/.config/autostart/oguzdows-chime.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Startup chime
Exec=/usr/local/bin/oguzdows-chime
X-GNOME-Autostart-enabled=true
EOF

# ---------------------------------------------------------------
# 4) Kurulum arayüzü (Calamares) kısayolları ve macOS Stili Markalama
# ---------------------------------------------------------------
mkdir -p config/includes.chroot/usr/share/applications
cat > config/includes.chroot/usr/share/applications/oguzdows-install.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=OğuzDows'u Kur
Comment=OğuzDows'u bilgisayarın diskine kur (macOS Stili)
Exec=sudo -E calamares
Icon=calamares
Terminal=false
Categories=System;
EOF
cp config/includes.chroot/usr/share/applications/oguzdows-install.desktop \
   "$SKEL/Desktop/OguzDows-Kur.desktop"

# ---------------------------------------------------------------
# 5) Kullanıcı yönetimi ve otomatik giriş
# ---------------------------------------------------------------
mkdir -p config/includes.chroot/etc/systemd/system config/includes.chroot/etc/sudoers.d

cat > config/includes.chroot/usr/local/bin/oguzdows-fixlogin <<'EOF'
#!/bin/sh
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

cat > config/includes.chroot/etc/default/keyboard <<'EOF'
XKBMODEL="pc105"
XKBLAYOUT="tr"
XKBVARIANT=""
XKBOPTIONS=""
BACKSPACE="guess"
EOF

cat > config/includes.chroot/etc/default/zramswap <<'EOF'
ALGO=lz4
PERCENT=50
EOF

# ---------------------------------------------------------------
# 6) Chroot Kancaları (Hooks)
# ---------------------------------------------------------------
mkdir -p config/hooks/live

# --- 0100: Markalama ve Calamares macOS dönüştürme ---
cat > config/hooks/live/0100-branding.hook.chroot <<'EOF'
#!/bin/sh
set -e
sed -i 's/^PRETTY_NAME=.*/PRETTY_NAME="OğuzDows"/; s/^NAME=.*/NAME="OğuzDows"/' /etc/os-release
echo "OğuzDows \\n \\l" > /etc/issue
echo "OğuzDows" > /etc/issue.net
chmod +x /etc/skel/Desktop/*.desktop || true

# Calamares yükleyicisini tamamen OğuzDows macOS stiline uyarla
for f in /etc/calamares/branding/*/branding.desc /usr/share/calamares/branding/*/branding.desc; do
  [ -f "$f" ] || continue
  sed -i -E 's/^([[:space:]]*(productName|shortProductName):[[:space:]]*).*/\1OğuzDows/' "$f" || true
  sed -i -E 's/^([[:space:]]*bootloaderEntryName:[[:space:]]*).*/\1OguzDows/' "$f" || true
  sed -i -E 's/^([[:space:]]*windowExpanding:[[:space:]]*).*/\1normal/' "$f" || true
done

flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo || true
EOF

# --- 0200: WhiteSur Teması ve Şık Duvar Kağıdı ---
cat > config/hooks/live/0200-macos-theme.hook.chroot <<'EOF'
#!/bin/sh
set -e
T=/tmp/oguzdows-theme
mkdir -p "$T"
cd "$T"
if git clone --depth=1 https://github.com/vinceliuice/WhiteSur-gtk-theme.git gtk \
 && git clone --depth=1 https://github.com/vinceliuice/WhiteSur-icon-theme.git icons \
 && git clone --depth=1 https://github.com/vinceliuice/WhiteSur-cursors.git cursors; then
  (cd gtk    && ./install.sh -d /usr/share/themes -c Light -t default) || echo "GTK teması kurulamadı"
  (cd icons  && ./install.sh -d /usr/share/icons)                       || echo "İkon teması kurulamadı"
  (mkdir -p /usr/share/icons && cp -r cursors/dist /usr/share/icons/WhiteSur-cursors) || echo "İmleç kurulamadı"
else
  echo "UYARI: WhiteSur indirilemedi, varsayılan kullanılacak."
fi
cd /
rm -rf "$T"

mkdir -p /usr/share/backgrounds
IM=convert; command -v convert >/dev/null 2>&1 || IM=magick
$IM -size 1920x1080 gradient:'#1b1464-#0e0b2e' \
  \( -size 1920x1080 radial-gradient:'rgba(255,94,162,0.65)-rgba(255,94,162,0)' \) \
  -compose screen -composite /usr/share/backgrounds/oguzdows.png \
  || $IM -size 1920x1080 gradient:'#1b1464-#0e0b2e' /usr/share/backgrounds/oguzdows.png || true

dconf update || true
EOF

# --- 0250: Sürücüler (Broadcom & Donanım) ---
cat > config/hooks/live/0250-drivers.hook.chroot <<EOF
#!/bin/sh
export DEBIAN_FRONTEND=noninteractive
apt-get update || true
apt-get install -y --no-install-recommends dkms linux-headers-$FLAVOUR broadcom-sta-dkms \\
  || echo "UYARI: Broadcom surucusu kurulamadi"
if dkms status 2>/dev/null | grep -q broadcom; then
  cat > /etc/modprobe.d/broadcom-wl.conf <<'EOC'
blacklist b43
blacklist b43legacy
blacklist ssb
blacklist bcm43xx
blacklist brcm80211
blacklist brcmfmac
blacklist brcmsmac
blacklist bcma
EOC
fi
exit 0
EOF

# --- 0300: Giriş Servisi ---
cat > config/hooks/live/0300-login.hook.chroot <<'EOF'
#!/bin/sh
set -e
systemctl enable oguzdows-fixlogin.service
EOF

# --- 0400: macOS Tarzı Animasyonlu Yükleme ve Ses Efekti ---
cat > config/hooks/live/0400-boot-experience.hook.chroot <<'EOF'
#!/bin/sh
set -e

# Plymouth: Zarif, animasyonlu macOS tarzı yükleme ekranı
D=/usr/share/plymouth/themes/oguzdows
mkdir -p "$D"
IM=convert; command -v convert >/dev/null 2>&1 || IM=magick
FONT="$(fc-match -f '%{file}' 'Inter:bold' 2>/dev/null || true)"
[ -n "$FONT" ] || FONT="$(fc-match -f '%{file}' 'sans:bold' 2>/dev/null || true)"
if [ -n "$FONT" ]; then
  $IM -background none -fill white -font "$FONT" -pointsize 76 label:'OğuzDows' "png32:$D/logo.png"
else
  $IM -background none -fill white -pointsize 76 label:'OğuzDows' "png32:$D/logo.png"
fi

# Modern macOS tarzı ince, yuvarlatılmış kapsül yükleme çubuğu parçaları
$IM -size 220x6 xc:'rgba(255,255,255,0.2)' "png32:$D/track.png"
$IM -size 220x6 xc:'#ffffff' "png32:$D/fill.png"

cat > "$D/oguzdows.plymouth" <<'EOP'
[Plymouth Theme]
Name=OguzDows
Description=OguzDows Animasyonlu macOS Tarzi Acilis Ekrani
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/oguzdows
ScriptFile=/usr/share/plymouth/themes/oguzdows/oguzdows.script
EOP

cat > "$D/oguzdows.script" <<'EOP'
Window.SetBackgroundTopColor(0.05, 0.05, 0.08);
Window.SetBackgroundBottomColor(0.0, 0.0, 0.02);

logo.image = Image("logo.png");
logo.sprite = Sprite(logo.image);
logo.sprite.SetX(Window.GetWidth() / 2 - logo.image.GetWidth() / 2);
logo.sprite.SetY(Window.GetHeight() / 2 - logo.image.GetHeight() / 2 - 50);

bar.x = Window.GetWidth() / 2 - 110;
bar.y = Window.GetHeight() / 2 + 65;

track.image = Image("track.png");
track.sprite = Sprite(track.image);
track.sprite.SetX(bar.x);
track.sprite.SetY(bar.y);

fill.image = Image("fill.png");
fill.sprite = Sprite();
fill.sprite.SetX(bar.x);
fill.sprite.SetY(bar.y);
fill.sprite.SetZ(10);

progress = 0;
fun refresh_callback() {
  progress = progress + 1.5;
  if (progress > 220) progress = 20;
  w = Math.Int(progress);
  if (w < 4) w = 4;
  fill.sprite.SetImage(fill.image.Scale(w, 6));
}
Plymouth.SetRefreshFunction(refresh_callback);
EOP

plymouth-set-default-theme oguzdows

# Yumuşak başlangıç akor sesi (SoX ile)
mkdir -p /usr/share/sounds/oguzdows
TMP=/tmp/oguzdows-chime
mkdir -p "$TMP"
i=0
for f in 130.81 196.00 329.63 392.00 587.33 783.99; do
  d=$(awk "BEGIN{printf \"%.2f\", $i*0.1}")
  sox -n -r 44100 -b 16 "$TMP/n$i.wav" synth 5 sine "$f" fade q 0.03 5 4.2 pad "$d" 0 gain -16 channels 2
  i=$((i+1))
done
sox -m "$TMP"/n0.wav "$TMP"/n1.wav "$TMP"/n2.wav "$TMP"/n3.wav "$TMP"/n4.wav "$TMP"/n5.wav \
  /usr/share/sounds/oguzdows/startup.wav gain -n -3 reverb 30
rm -rf "$TMP"

update-initramfs -u -k all
EOF

chmod +x config/hooks/live/*.hook.chroot

# ---------------------------------------------------------------
# 7) ISO'yu üret
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

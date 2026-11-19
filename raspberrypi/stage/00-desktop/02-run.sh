#!/bin/bash -e
# QEMU yalnızca kullanıcı alanı smoke testi içindir; Pi boot/GPU testi değildir.
if [ "${ARCH}" = armhf ]; then
    emulator=/usr/bin/qemu-arm-static
    cpu=arm1176
else
    emulator=/usr/bin/qemu-aarch64-static
    cpu=cortex-a53
fi
if [ ! -x "$emulator" ]; then
    echo "Pi minimum CPU kontrolü için $emulator gerekli." >&2
    exit 1
fi
install -m 0755 "$emulator" "${ROOTFS_DIR}/tmp/oguzdows-qemu-static"
trap 'rm -f "${ROOTFS_DIR}/tmp/oguzdows-qemu-static"' EXIT
# pi-gen on_chroot bir bash oturumu açar; ELF dosyası argüman olarak verilmez.
on_chroot <<EOF
/tmp/oguzdows-qemu-static -cpu "$cpu" /bin/true
/tmp/oguzdows-qemu-static -cpu "$cpu" /usr/bin/python3 -c \\
    'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk; import sys; sys.path.insert(0,"/usr/lib/oguzdows"); import hardware, pi_support; print("OğuzDows minimum ARM CPU / Python / GTK: başarılı")'
/tmp/oguzdows-qemu-static -cpu "$cpu" /usr/bin/xfce4-session --version
EOF

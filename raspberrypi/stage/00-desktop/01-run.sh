#!/bin/bash -e
# Sisteme yalnızca mimariden bağımsız ortak görünüm + Pi katmanı kopyalanır.
cp -a files/overlay/. "${ROOTFS_DIR}/"
# Üretim görselinde derleme hesabı, ortak parola ve parolasız sudo bulunmaz.
on_chroot < files/configure-system.sh

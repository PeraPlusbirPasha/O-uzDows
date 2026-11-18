#!/bin/bash -e
# set-partuuid'den sonra, sıkıştırma/sağlama toplamından önce çalışır.
# Initramfs dosyaları bir sonraki resmî finalise aşamasında üretilir.
on_chroot <<EOF
/usr/bin/python3 /usr/lib/oguzdows/verify-pi.py --root / --arch "${ARCH}" --pre-export
EOF

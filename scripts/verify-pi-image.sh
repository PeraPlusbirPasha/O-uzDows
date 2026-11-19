#!/bin/bash
# Salt okunur yapısal kontrol; imajdan program çalıştırmaz.
set -euo pipefail
if [ "$#" -ne 2 ] || [[ ! "$2" =~ ^(armhf|arm64)$ ]]; then
    echo "Kullanım: sudo scripts/verify-pi-image.sh imaj.img armhf|arm64" >&2
    exit 2
fi
[ "$(id -u)" -eq 0 ] || { echo 'Salt okunur loop bağlamak için root gerekli.' >&2; exit 1; }
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
IMAGE=$(realpath -- "$1")
ARCH=$2
[ -f "$IMAGE" ] || { echo 'Ham .img bulunamadı.' >&2; exit 1; }
DIRECTORY=$(mktemp -d -t oguzdows-pi-check.XXXXXXXX)
LOOP=''
cleanup() {
    local status=$?
    if mountpoint -q "$DIRECTORY/root/boot/firmware"; then
        umount "$DIRECTORY/root/boot/firmware" || return 1
    fi
    if mountpoint -q "$DIRECTORY/root"; then
        umount "$DIRECTORY/root" || return 1
    fi
    if [ -n "$LOOP" ]; then losetup -d "$LOOP" || return 1; fi
    rm -f "$DIRECTORY/partitions.json"
    if [ -d "$DIRECTORY/root" ]; then rmdir "$DIRECTORY/root"; fi
    rmdir "$DIRECTORY"
    return "$status"
}
trap cleanup EXIT
sfdisk --json "$IMAGE" > "$DIRECTORY/partitions.json"
python3 - "$DIRECTORY/partitions.json" <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    table = json.load(stream)['partitiontable']
parts = table['partitions']
if table['label'] != 'dos' or len(parts) != 2:
    raise ValueError('Pi imajı MBR / iki bölüm olmalı')
if parts[0]['type'].lower() not in ('b', 'c', '0b', '0c') or parts[1]['type'] != '83':
    raise ValueError('FAT boot / Linux kök bölümü eksik')
if not all(part['start'] % 16384 == 0 for part in parts):
    raise ValueError('8 MiB hizalama eksik')
PY
rm "$DIRECTORY/partitions.json"
LOOP=$(losetup --find --show --partscan --read-only "$IMAGE")
udevadm settle
mkdir "$DIRECTORY/root"
mount -o ro,noload,nodev,nosuid,noexec "${LOOP}p2" "$DIRECTORY/root"
mount -o ro,nodev,nosuid,noexec "${LOOP}p1" "$DIRECTORY/root/boot/firmware"
python3 "$SCRIPT_DIR/verify-pi.py" --root "$DIRECTORY/root" --arch "$ARCH"

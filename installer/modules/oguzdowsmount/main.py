"""Chroot bağlantılarını kopyalamadan ve GRUB yazımından önce salt-okunur denetler."""
from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

import libcalamares

REQUIRED = frozenset(('/dev', '/dev/pts', '/proc', '/sys', '/run', '/run/udev'))


class MountError(ValueError):
    pass


def mount_table(text=None):
    if text is None:
        text = Path('/proc/self/mountinfo').read_text()
    table = {}
    for line in text.splitlines():
        before, separator, after = line.partition(' - ')
        head, tail = before.split(), after.split()
        if not separator or len(head) < 6 or len(tail) < 3:
            raise MountError('Çalışan sistemin bağlama tablosu okunamadı.')
        point = re.sub(r'\\([0-7]{3})', lambda match: chr(int(match[1], 8)), head[4])
        table[point] = {'device_id': head[2], 'fs': tail[0]}
    return table


def selected_partition(partitions, point):
    matches = [p for p in partitions if p.get('mountPoint') == point]
    if len(matches) != 1:
        raise MountError('Hedef bölüm tekil değil veya seçilmemiş: ' + point)
    return matches[0]


def device_path(partition):
    mapper = partition.get('luksMapperName')
    if mapper:
        if not isinstance(mapper, str) or not re.fullmatch(r'[A-Za-z0-9_.+-]+', mapper) or mapper in ('.', '..'):
            raise MountError('Şifreli hedefin aygıt adı geçersiz.')
        return '/dev/mapper/' + mapper
    return partition.get('device')


def block_info(device):
    if not isinstance(device, str) or not device.startswith('/dev/'):
        raise MountError('Hedef bölümün blok aygıtı bulunamadı.')
    info = os.stat(device)
    if not stat.S_ISBLK(info.st_mode):
        raise MountError('Hedef bölüm gerçek bir blok aygıtı değil: ' + device)
    return info


def target_root(root):
    root = Path(root)
    if not root.is_absolute() or not root.is_dir() or root.resolve() == Path('/'):
        raise MountError('Güvenli kurulum kökü yok; çalışan sistem değiştirilmedi.')
    return root.resolve()


def verify_mounts(root, partitions, extra_mounts, table=None):
    root = target_root(root)
    if not isinstance(extra_mounts, list) or not REQUIRED <= {
            item.get('mountPoint') for item in extra_mounts if isinstance(item, dict)}:
        raise MountError('mount.conf / extraMounts eksik. /dev, /dev/pts, /proc, /sys, /run ve /run/udev '
                         'hem bağlanmalı hem kopyalama dışında tutulmalı; dosya aktarımı başlatılmadı.')
    if table is None:
        table = mount_table()
    points = ['/'] + (['/boot'] if any(p.get('mountPoint') == '/boot' for p in partitions) else [])
    devices = []
    for point in points:
        selected = selected_partition(partitions, point)
        device = device_path(selected)
        info = block_info(device)
        location = root if point == '/' else root / point.lstrip('/')
        record = table.get(str(location), {})
        expected = f'{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}'
        if record.get('device_id') != expected:
            raise MountError('Seçilen bölüm hedefe bağlı değil: ' + str(point) + ' ← ' + str(device)
                             + '. Bağlama hatası göz ardı edilmedi; hedef otomatik değiştirilmedi.')
        devices.append(device)
    for point in REQUIRED:
        location = root / point.lstrip('/')
        if str(location) not in table or location.resolve() != location:
            raise MountError('Hedef sistem bağlantısı yok veya güvenli değil: ' + point
                             + '. mount.conf ve kurulum günlüğünü inceleyin; GRUB yazımına geçilmedi.')
    for point, filesystem in (('/proc', 'proc'), ('/sys', 'sysfs'), ('/run', 'tmpfs'), ('/dev/pts', 'devpts')):
        if table[str(root / point.lstrip('/'))]['fs'] != filesystem:
            raise MountError('Hedef sistem bağlantısının türü yanlış: ' + point)
    for point in ('/dev', '/dev/pts', '/run/udev'):
        if not os.path.samefile(point, root / point.lstrip('/')):
            raise MountError('Canlı aygıt bağlantısı hedefte görünmüyor: ' + point)
    for device in devices:
        # by-id / mapper bağlantısının hedefteki mutlak symlink'i host kökünde
        # çözülmesin: önce hosttaki gerçek /dev düğümünü belirle.
        canonical = Path(device).resolve(strict=True)
        if not canonical.is_relative_to('/dev'):
            raise MountError('Aygıt yolu /dev dışına çıkıyor: ' + device)
        target_device = root / canonical.relative_to('/')
        target_info = target_device.stat()
        if block_info(str(canonical)).st_rdev != target_info.st_rdev or not stat.S_ISBLK(target_info.st_mode):
            raise MountError('Hedef /dev içinde seçilen bölüm görünmüyor: ' + device)
    return root


def probe_boot(root, partitions, output):
    root = target_root(root)
    selected = selected_partition(partitions, '/boot' if any(p.get('mountPoint') == '/boot' for p in partitions) else '/')
    path = '/boot/grub' if (root / 'boot/grub').is_dir() else '/boot'
    try:
        result = output(['grub-probe', '--target=device', path], '', 30)
    except subprocess.CalledProcessError as error:
        detail = str(error.output or error.stderr or error)[-1500:]
        raise MountError('GRUB hedef /boot aygıtını göremiyor. /dev, /proc ve /sys bağlantılarını '
                         'kontrol edin; hiçbir diske GRUB yazılmadı.\n' + detail) from error
    devices = result.split()
    expected = block_info(device_path(selected)).st_rdev
    if len(devices) != 1 or block_info(devices[0]).st_rdev != expected:
        raise MountError('GRUB tarafından görülen /boot aygıtı seçilen hedefle eşleşmiyor; '
                         'hiçbir diske GRUB yazılmadı: ' + result.strip())
    return devices[0]


def pretty_name():
    return 'OğuzDows hedef sistem bağlantıları denetleniyor'


def run():
    gs = libcalamares.globalstorage
    try:
        phase = libcalamares.job.configuration.get('phase')
        if phase not in ('mounted', 'grub-probe'):
            raise MountError('Bilinmeyen hedef bağlantı denetim aşaması.')
        partitions = gs.value('partitions') or []
        root = verify_mounts(gs.value('rootMountPoint') or '', partitions, gs.value('extraMounts'))
        if phase == 'grub-probe':
            device = probe_boot(root, partitions, libcalamares.utils.check_target_env_output)
            libcalamares.utils.debug('OğuzDows: hedef chroot grub-probe /boot aygıtı doğrulandı: ' + device)
        else:
            libcalamares.utils.debug('OğuzDows: hedef /dev, /dev/pts, /proc, /sys, /run ve /run/udev bağlantıları doğrulandı.')
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        return ('Hedef sistem bağlantıları hazırlanamadı', str(error))
    return None

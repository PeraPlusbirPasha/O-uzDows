"""Kurulu hedefin canlı oturumdan ayrıldığını ve gerçek açılış dosyalarını denetler.

Disk seçmez, bölümlemez veya paket kaldırmaz. Calamares'in zorunlu temizliği ve
initramfs işi öncesi/sonrası salt-okunur doğrulama için kullanılır.
"""
from __future__ import annotations

import re
import shlex
import stat
import subprocess
from pathlib import Path

LIVE_PACKAGES = frozenset(('live-boot', 'live-boot-initramfs-tools', 'live-config',
                           'live-config-systemd', 'live-tools', 'calamares'))
VERSION = re.compile(r'[A-Za-z0-9][A-Za-z0-9.+_~:-]*\Z')


class TargetError(ValueError):
    pass


def target_root(root):
    root = Path(root)
    if not root.is_absolute() or not root.is_dir() or root.resolve() == Path('/'):
        raise TargetError('Güvenli kurulum hedefi yok; çalışan sistem denetlenmedi veya değiştirilmedi.')
    return root.resolve()


def inside(root, relative):
    root = target_root(root)
    path = root / relative
    if Path(relative).is_absolute() or not path.resolve().is_relative_to(root):
        raise TargetError('Hedef dışına çıkan dosya yolu reddedildi: ' + str(relative))
    return path


def nonempty(root, relative):
    path = inside(root, relative)
    if not path.is_file() or not path.stat().st_size:
        raise TargetError('Hedefte eksik / boş dosya: ' + str(relative))
    return path


def package_states(text):
    states = {}
    for paragraph in text.split('\n\n'):
        fields = dict(line.split(': ', 1) for line in paragraph.splitlines()
                      if ': ' in line and not line.startswith((' ', '\t')))
        if fields.get('Package'):
            states[fields['Package']] = fields.get('Status', '')
    return states


def require_clean_target(root):
    states = package_states(nonempty(root, 'var/lib/dpkg/status').read_text())
    remaining = sorted(p for p in LIVE_PACKAGES if p in states
                       and states[p].split()[1:] != ['ok', 'not-installed'])
    if remaining:
        raise TargetError('Canlı paket temizliği tamamlanmadı: ' + ', '.join(remaining)
                          + '. initramfs ve disk açılışı henüz doğrulanamaz; APT günlüğünü inceleyin.')
    diversions = inside(root, 'var/lib/dpkg/diversions')
    if diversions.exists():
        lines = diversions.read_text().splitlines()
        if len(lines) % 3:
            raise TargetError('Hedef dpkg diversion kaydı bozuk; initramfs denetimi durdu.')
        for original in lines[::3]:
            if original in ('/usr/sbin/update-initramfs', '/sbin/update-initramfs'):
                raise TargetError('update-initramfs hâlâ yönlendirilmiş. Canlı sarmalayıcı sessizce iş atlayabilir; temizliği düzeltin.')
    updater = nonempty(root, 'usr/sbin/update-initramfs')
    if not updater.stat().st_mode & 0o111:
        raise TargetError('Hedef update-initramfs çalıştırılabilir değil.')


def fingerprint(path):
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise TargetError('Geçersiz açılış dosyası: ' + str(path))
    # QVariant dönüşümünde nanosaniye / inode hassasiyeti kaybolmasın.
    return {key: str(value) for key, value in
            (('device', info.st_dev), ('inode', info.st_ino),
             ('mtime_ns', info.st_mtime_ns), ('size', info.st_size))}


def kernel_snapshot(root):
    root = target_root(root)
    boot = inside(root, 'boot')
    kernels = {}
    for image in sorted(boot.glob('vmlinuz-*')):
        version = image.name.removeprefix('vmlinuz-')
        if not VERSION.fullmatch(version):
            raise TargetError('Beklenmeyen çekirdek dosya adı: ' + image.name)
        nonempty(root, 'boot/' + image.name)
        modules = inside(root, 'usr/lib/modules/' + version)
        if not modules.is_dir():
            modules = inside(root, 'lib/modules/' + version)
        if not modules.is_dir():
            raise TargetError('Çekirdekle eşleşen modüller yok: ' + version)
        initrd = inside(root, 'boot/initrd.img-' + version)
        kernels[version] = fingerprint(initrd) if initrd.exists() else None
    if not kernels:
        raise TargetError('Hedef /boot altında kurulu çekirdek bulunamadı.')
    return kernels


def initrd_contents(path):
    result = subprocess.run(['lsinitramfs', str(path)], check=True, capture_output=True,
                            text=True, errors='replace', timeout=300)
    return {line.strip().removeprefix('./') for line in result.stdout.splitlines()}


def verify_initramfs(root, before, contents=None):
    if contents is None:
        contents = initrd_contents
    require_clean_target(root)
    after = kernel_snapshot(root)
    if not isinstance(before, dict) or set(before) != set(after):
        raise TargetError('initramfs öncesi / sonrası çekirdek kaydı eşleşmiyor; başarı bildirilmedi.')
    for version, current in after.items():
        if current is None:
            raise TargetError('Çekirdeğin initramfs dosyası oluşmadı: ' + version)
        if current == before[version]:
            raise TargetError('initramfs yenilenmedi: ' + version
                              + '. Sıfır çıkış kodu tek başına yeterli değil; canlı sarmalayıcıyı / günlüğü inceleyin.')
        names = contents(inside(root, 'boot/initrd.img-' + version))
        if 'init' not in names or 'scripts/local' not in names:
            raise TargetError('initramfs normal disk açılış betiklerini içermiyor: ' + version)
        prefixes = ('lib/modules/' + version + '/', 'usr/lib/modules/' + version + '/')
        if not any(name.startswith(prefixes) for name in names):
            raise TargetError('initramfs içinde eşleşen çekirdek modülleri yok: ' + version)
    return after


def verify_grub_menu(root, expected_root=None):
    """Mevcut çekirdek + initrd çifti ve geçici olmayan disk kökü gerekir.

    expected_root, izole ISO testinde UUID'nin hedefle eşleşmesini de zorunlu
    tutar. /dev/mapper gibi meşru şifreli kurulum kökleri varsayılanda korunur.
    """
    versions = kernel_snapshot(root)
    text = nonempty(root, 'boot/grub/grub.cfg').read_text(errors='replace')
    kernel = None
    for line in text.splitlines():
        try:
            words = shlex.split(line, comments=True)
        except ValueError:
            continue
        if not words:
            continue
        if words[0] in ('linux', 'linuxefi'):
            kernel = None
            roots = [w.removeprefix('root=') for w in words[2:] if w.startswith('root=')]
            if len(words) < 3 or 'boot=live' in words or len(roots) != 1 or not roots[0]:
                continue
            if roots[0].startswith(('/dev/loop', '/dev/sr', '/run/live/', '/lib/live/')):
                continue  # Canlı/CI oturumuna ait aygıt, diskten açılışta yoktur.
            if expected_root is not None and roots[0] != expected_root:
                continue
            for version in versions:
                if words[1] in ('/boot/vmlinuz-' + version, '/vmlinuz-' + version):
                    kernel = version
        elif words[0] in ('initrd', 'initrdefi') and kernel:
            if any(name in words[1:] for name in ('/boot/initrd.img-' + kernel, '/initrd.img-' + kernel)):
                nonempty(root, 'boot/initrd.img-' + kernel)
                return kernel
        elif words[0] == '}':
            kernel = None
    raise TargetError('GRUB menüsünde mevcut çekirdek, initramfs ve disk kökü birlikte doğrulanamadı.')

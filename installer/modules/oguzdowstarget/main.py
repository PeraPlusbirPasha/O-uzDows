"""Canlı paket temizliği → gerçek initramfs üretimi → disk çekirdek menüsü."""
import json
import subprocess
import sys
from pathlib import Path

import libcalamares

sys.path.insert(0, '/usr/lib/oguzdows')


def pretty_name():
    return 'OğuzDows hedef sistem açılış dosyaları doğrulanıyor'


def run():
    import target_system
    from install_status import atomic_json
    try:
        gs = libcalamares.globalstorage
        root = target_system.target_root(Path(gs.value('rootMountPoint') or ''))
        phase = libcalamares.job.configuration.get('phase')
        if phase == 'prepare':
            target_system.require_clean_target(root)
            gs.insert('oguzdowsInitramfsBefore', target_system.kernel_snapshot(root))
        elif phase == 'verify':
            after = target_system.verify_initramfs(root, gs.value('oguzdowsInitramfsBefore'))
            gs.insert('oguzdowsInitramfsVerified', after)
        elif phase == 'boot-menu':
            after = gs.value('oguzdowsInitramfsVerified')
            if not isinstance(after, dict) or not after:
                raise target_system.TargetError('initramfs doğrulama kanıtı yok; kurulum tamamlandı sayılmadı.')
            if after != target_system.kernel_snapshot(root):
                raise target_system.TargetError('Doğrulanan initramfs sonradan değişti; kurulum tamamlandı sayılmadı.')
            version = target_system.verify_grub_menu(root)
            report = {'version': 1, 'kernel': version, 'initramfs': after,
                      'stage': 'boot-menu-verified', 'physical_boot_verified': False}
            build = target_system.inside(root, 'usr/share/oguzdows/build-info.json')
            if build.is_file():
                report['build'] = json.loads(build.read_text())
            atomic_json(target_system.inside(root, 'var/log/oguzdows/target-system.json'), report)
        else:
            raise target_system.TargetError('Bilinmeyen hedef sistem denetim aşaması.')
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        return ('Hedef sistem açılışı hazırlanamadı', str(error))
    return None

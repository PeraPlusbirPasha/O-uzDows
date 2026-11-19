"""Canlı donanım denetimi ile hedef paket kurulumunu birbirinden ayırır.

Ek Wi-Fi paketi, temel sistemi / önyükleyiciyi durduramaz. Her atlama ya da
başarısız paket işlemi sonuç ekranına ve hedef günlüğüne açıkça taşınır.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

from hardware import supported_broadcom, supported_intel_legacy
from offline import PACKAGES

PLAN = 'run/oguzdows-driver-transfer.json'
WORKER = '/usr/lib/oguzdows/install-target-driver.py'


def compatible(action):
    return supported_broadcom() if action == 'broadcom' else supported_intel_legacy()


def save_plan(path, action, devices):
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise OSError('Hedef çalışma dizini sembolik bağlantı olamaz.')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump({'version': 1, 'action': action, 'devices': devices, 'approved': True}, stream)
        stream.flush()
        os.fsync(stream.fileno())


def read_plan(path=Path('/') / PLAN):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'r', encoding='utf-8') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
            raise ValueError('Sürücü aktarım onayı güvenli değil.')
        data = json.loads(stream.read(8193))
    if not isinstance(data, dict) or data.get('version') != 1 or data.get('approved') is not True or data.get('action') not in PACKAGES:
        raise ValueError('Geçersiz sürücü aktarım onayı.')
    devices = data.get('devices')
    vendor = '14e4:' if data['action'] == 'broadcom' else '8086:'
    if not isinstance(devices, list) or not devices or not all(isinstance(d, str) and len(d) == 9 and d.startswith(vendor) and all(c in '0123456789abcdef' for c in d[5:]) for d in devices):
        raise ValueError('Canlı ortamda eşleşen aygıt kanıtı yok.')
    return data


def transfer(root, actions, approved, invoke, detect=compatible):
    """invoke yalnızca sabit argv ile HEDEF ortamında çalıştırılır; shell yoktur."""
    root = Path(root)
    if not root.is_absolute() or root.resolve() == Path('/') or not root.is_dir() or root.is_symlink():
        raise ValueError('Güvenli kurulum hedefi bulunamadı; çalışan sisteme paket kurulmadı.')
    results = []
    for action in dict.fromkeys(a for a in actions if isinstance(a, str) and a in PACKAGES):
        item = {'action': action, 'status': 'skipped', 'message': ''}
        if action not in approved:
            item['message'] = 'Canlı oturumdaki açık lisans / sürücü onayı yok. Paket kurulmadı.'
        else:
            try:
                devices = detect(action)
                if not devices:
                    item['message'] = 'Canlı ortamda bu ek sürücüyle eşleşen aygıt yok. Yerleşik sürücüler korundu; temel kuruluma devam edildi.'
                else:
                    plan = root / PLAN
                    save_plan(plan, action, devices)
                    try:
                        code = invoke(['/usr/bin/python3', '-I', WORKER, action])
                        item.update(status='installed' if code == 0 else 'failed',
                                    message='Onaylanan ek paket hedefe kuruldu.' if code == 0 else 'Ek paket kurulamadı. Temel kuruluma devam edildi; ayrıntılar /var/log/oguzdows/drivers-target.log dosyasında.')
                    finally:
                        plan.unlink(missing_ok=True)
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                item.update(status='failed', message='Ek sürücü aktarımı tamamlanamadı. Yerleşik sürücüler korundu. ' + type(error).__name__)
        results.append(item)
    return results


def save_results(root, results):
    path = Path(root) / 'var/log/oguzdows/driver-transfer.json'
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(results, stream, ensure_ascii=False, indent=2)
        stream.write('\n')

#!/usr/bin/python3 -I
"""Sadece Calamares'in onaylı hedef aktarımı; canlı sürücüyü yüklemez / sökmez."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from driver_transfer import read_plan
from offline import headers_available, install_command, payload

ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C.UTF-8', 'DEBIAN_FRONTEND': 'noninteractive'}


def install(action, log, modules=Path('/lib/modules'), boot=Path('/boot')):
    archive = payload(action)
    if archive is None:
        raise ValueError('Gömülü paket bütünlüğü doğrulanamadı.')
    if action == 'broadcom':
        kernels = [p.name for p in sorted(modules.iterdir()) if (p / 'modules.dep').is_file() and (boot / ('vmlinuz-' + p.name)).is_file()]
        if not kernels or not all(headers_available(kernel, modules) for kernel in kernels):
            raise ValueError('Hedef çekirdeklerinin eşleşen başlıkları eksik. Canlı çekirdeğin sürümü kullanılmadı.')
    if action == 'intel-legacy-accept-license':
        subprocess.run(['/usr/bin/debconf-set-selections'], input='firmware-ipw2x00 firmware-ipw2x00/license/accepted boolean true\n',
                       text=True, stdout=log, stderr=subprocess.STDOUT, env=ENV, check=True, timeout=30)
    subprocess.run(install_command(archive), stdout=log, stderr=subprocess.STDOUT, env=ENV, check=True, timeout=780)
    # Ana Calamares initramfs işi SONRA çalışır; burada live tespit / modprobe yok.
    return 0


def main(args=None):
    args = sys.argv[1:] if args is None else args
    if os.geteuid() != 0 or len(args) != 1:
        return 2
    try:
        plan = read_plan()
        if args[0] != plan['action']:
            raise ValueError('Aktarım eylemi onayla eşleşmiyor.')
        directory = Path('/var/log/oguzdows')
        directory.mkdir(mode=0o755, parents=True, exist_ok=True)
        fd = os.open(directory / 'drivers-target.log', os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'a', encoding='utf-8') as log:
            print('Onaylı hedef işlemi: ' + plan['action'], file=log, flush=True)
            try:
                return install(plan['action'], log)
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                print('Ek paket kurulamadı: ' + str(error), file=log, flush=True)
                return 1
    except (OSError, ValueError):
        print('Güvenli sürücü aktarım onayı yok; hiçbir paket kurulmadı.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

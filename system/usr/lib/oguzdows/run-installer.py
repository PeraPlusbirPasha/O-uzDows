#!/usr/bin/env python3
"""Yetkili başlatıcının sabit kurucu işlemini izler; GUI kapanışını başarı saymaz."""
from __future__ import annotations

import argparse
from collections import deque
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import install_status as status


def supervise(prepare, command, log, directory=status.RUN):
    state = status.begin(directory)
    session = state['session']
    environment = {**os.environ, 'OGUZDOWS_INSTALL_SESSION': session}
    try:
        if subprocess.run(prepare, stdout=log, stderr=subprocess.STDOUT, env=environment, check=False).returncode:
            result = status.finish(session, 1, directory)
        else:
            status.stage(session, 'ready', directory)
            code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=environment, check=False).returncode
            result = status.finish(session, code, directory)
    except OSError as error:
        print('Kurucu işlemi başlatılamadı: ' + str(error), file=log, flush=True)
        result = status.finish(session, 1, directory)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0 or 'boot=live' not in Path('/proc/cmdline').read_text().split():
        parser.error('Yalnızca yetkili canlı ortam başlatıcısı kullanabilir.')
    if args.log.parent != Path('/var/log/oguzdows') or not args.log.name.startswith('installer.') or args.log.is_symlink():
        parser.error('Geçersiz günlük hedefi.')
    fd = os.open(args.log, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'a', encoding='utf-8') as log:
        try:
            build = json.loads(Path('/usr/share/oguzdows/build-info.json').read_text())
        except (OSError, ValueError):
            build = {'source_revision': 'unknown'}
        print('OğuzDows kurucu kaynak kimliği: ' + json.dumps(build, ensure_ascii=False), file=log, flush=True)
        print('Canlı çekirdek: ' + os.uname().release, file=log, flush=True)
        result = supervise(['/usr/bin/python3', '-I', '/usr/lib/oguzdows/prepare-install.py'],
                           ['/usr/bin/calamares', '-D', '6'], log)
    print(status.PREFIX + json.dumps(result, ensure_ascii=False), flush=True)
    if result['outcome'] != 'success':
        print('Kurulum tamamlanmadı. Günlük: /var/log/oguzdows/installer.log', file=sys.stderr)
        with args.log.open(errors='replace') as log:
            for line in deque(log, maxlen=20):
                print(line, file=sys.stderr, end='')
    return {'success': 0, 'cancelled': 10, 'incomplete': 11}.get(result['outcome'], 1)


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Gerçek Calamares mount → özel loop hedefi → chroot grub-probe regresyonu.

Yalnızca tek kullanımlık, ayrıcalıklı CI'de kendi dosyasına yazar. Fiziksel
aygıt/ISO parametresi kabul etmez. GRUB kurulumu / tam Calamares kurulumu yapmaz.
Etiketsiz CI'de SELinux chcon adımı atlanır; mount ve grub-probe gerçektir.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

from support import load
from test_calamares_mount import packaged_module

configure = load('native_mount_smoke_configure', 'scripts/configure.py')
firmware = load('native_mount_smoke_loop', 'tests/smoke-installed-boot.py')


def run(*args, **kwargs):
    print('+', *map(str, args), flush=True)
    return subprocess.run(list(map(str, args)), timeout=60, check=True, **kwargs)


def copy_probe(root):
    program = Path(shutil.which('grub-probe') or '/nonexistent/grub-probe')
    dependencies = subprocess.check_output(['ldd', str(program)], text=True)
    files = [program] + [Path(value) for value in re.findall(r'(/[^\s()]+)', dependencies)]
    for source in files:
        if not source.is_file():
            raise RuntimeError('grub-probe / kütüphanesi eksik: ' + str(source))
        destination = root / source.relative_to('/')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source.resolve(), destination)
    (root / 'boot/grub').mkdir(parents=True, exist_ok=True)
    return '/' + str(program.relative_to('/'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('test-results/calamares-mount'))
    args = parser.parse_args()
    if os.geteuid() != 0 or os.environ.get('CI') != 'true':
        parser.error('Yalnızca ayrıcalıklı, tek kullanımlık CI konteynerinde çalışır.')
    native = packaged_module('mount')
    unpack = packaged_module('unpackfs')
    if not native or not unpack:
        parser.error('Gerçek Calamares mount ve unpackfs paket işleri kurulu olmalı.')
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    arch = {'bookworm': 'i386', 'trixie': 'amd64'}.get(release.get('VERSION_CODENAME', '').strip('"'))
    if not arch:
        parser.error('Yalnızca bookworm ve trixie tabanları sınanır.')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='oguzdows-native-mount-')).resolve()
    image = work / 'private-test-only.img'
    loop = None
    mounts = []
    report = {'arch': arch, 'module': str(native), 'gui_installation_tested': False,
              'physical_boot_verified': False, 'grub_disk_write_tested': False}
    def mount_real(device, destination, filesystem, options):
        location = Path(destination)
        allowed = {root_device, '/dev', '/dev/pts', 'proc', 'sys', 'tmpfs', '/run/udev'}
        if not location.is_relative_to(work) or device not in allowed:
            raise RuntimeError('Özel test alanı / izinli kaynak dışında mount reddedildi.')
        command = ['mount']
        if filesystem:
            command += ['-t', filesystem]
        if options:
            command += ['-o', options]
        run(*command, '--', device, location)
        mounts.append(location)
        return 0
    def mount_native(configuration, destination):
        state = {'partitions': [{'device': root_device, 'mountPoint': '/', 'fs': 'ext4'}], 'firmwareType': 'bios'}
        fake = SimpleNamespace(job=SimpleNamespace(configuration=copy.deepcopy(configuration)),
                               globalstorage=SimpleNamespace(value=state.get, insert=state.__setitem__),
                               utils=SimpleNamespace(mount=mount_real, warning=print, error=print, debug=print,
                                                     gettext_path=lambda: '/nonexistent/oguzdows-locales',
                                                     gettext_languages=lambda: ['tr']))
        with patch.dict('sys.modules', {'libcalamares': fake}), patch('sys.dont_write_bytecode', True):
            module = load('real_native_mount_smoke', native)
            with patch.object(module.tempfile, 'mkdtemp', return_value=str(destination)), \
                    patch.object(module.subprocess, 'call', return_value=0):
                result = module.run()
            if result is not None:
                raise RuntimeError('Yerleşik mount işi başarısız: ' + repr(result))
            guard = load('real_native_mount_guard', 'installer/modules/oguzdowsmount/main.py')
            unpack_module = load('real_native_unpack_exclusions', unpack)
            exclusions = unpack_module.global_excludes()
        return state, guard, exclusions
    def unmount_all():
        while mounts:
            run('umount', mounts[-1])
            mounts.pop()
    try:
        # Daemonu olmayan CI'de yalnızca boş udev çalışma dizini gerekir;
        # aygıt düğümleri aşağıda kendi loop'umuz için doğrulanır / oluşturulur.
        Path('/run/udev').mkdir(parents=True, exist_ok=True)
        configure.configure(arch, work / 'configuration')
        settings_path = work / 'configuration/includes.chroot/etc/calamares/modules/mount.conf'
        configuration = yaml.safe_load(settings_path.read_text())
        report['configuration'] = configuration
        with image.open('wb') as stream:
            stream.truncate(192 * 1024**2)
        run('parted', '--script', image, 'mklabel', 'msdos', 'mkpart', 'primary', 'ext4', '1MiB', '100%')
        allocated = subprocess.check_output(['losetup', '--find', '--show', '--partscan', str(image)], text=True).strip()
        if not re.fullmatch(r'/dev/loop[0-9]+', allocated):
            raise RuntimeError('Özel loop dışında hedef reddedildi.')
        backing = Path('/sys/class/block') / Path(allocated).name / 'loop/backing_file'
        if Path(backing.read_text().strip()).resolve() != image:
            raise RuntimeError('Loop bu testin özel dosyasına ait değil.')
        loop = allocated
        root_device = firmware.partition_device(loop, 1)
        run('mkfs.ext4', '-q', '-F', root_device)
        before = work / 'without-configuration'
        state, guard, _ = mount_native({}, before)
        program = copy_probe(before)
        missing = subprocess.run(['chroot', str(before), program, '--target=device', '/boot/grub'],
                                 capture_output=True, text=True, timeout=30, env={**os.environ, 'LC_ALL': 'C'})
        message = missing.stdout + missing.stderr
        (output / 'without-configuration.log').write_text(message)
        report['without_configuration'] = {'returncode': missing.returncode, 'output': message[-2000:]}
        if missing.returncode == 0 or 'cannot find a device for /boot/grub' not in message:
            raise RuntimeError('Eksik mount yapılandırması beklenen GRUB hatasını üretmedi:\n' + message)
        try:
            guard.verify_mounts(before, state['partitions'], state['extraMounts'])
        except guard.MountError:
            pass
        else:
            raise RuntimeError('Eksik bağlantılar yeni güvenlik denetiminden geçti.')
        report['missing_configuration_reproduced'] = True
        unmount_all()
        after = work / 'with-configuration'
        state, guard, exclusions = mount_native(configuration, after)
        guard.verify_mounts(after, state['partitions'], state['extraMounts'])
        if not {point + '/' for point in guard.REQUIRED} <= set(exclusions):
            raise RuntimeError('Yerleşik unpackfs /dev vb. bağlantıları kopyalamadan dışlamıyor.')
        def probe(command, unused_input, timeout):
            if command[0] != 'grub-probe':
                raise RuntimeError('Salt-okunur grub-probe dışında komut reddedildi.')
            return subprocess.check_output(['chroot', str(after), program, *command[1:]],
                                           text=True, stderr=subprocess.STDOUT, timeout=timeout,
                                           env={**os.environ, 'LC_ALL': 'C'})
        device = guard.probe_boot(after, state['partitions'], probe)
        report['with_configuration'] = {'probe_device': device, 'expected_device': root_device,
                                        'unpack_exclusions': exclusions, 'mounts_verified': True}
        print('::notice title=Gerçek Calamares mount regresyonu::' + json.dumps(report, ensure_ascii=False), flush=True)
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        (output / 'native-mount-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        safe = True
        for location in reversed(mounts):
            if subprocess.run(['umount', str(location)], check=False).returncode:
                safe = False
        # Kaydedilmemiş bir alt bağlantı bile kalmışsa rmtree yapılmaz.
        try:
            for line in Path('/proc/self/mountinfo').read_text().splitlines():
                point = re.sub(r'\\([0-7]{3})', lambda match: chr(int(match[1], 8)), line.split()[4])
                if Path(point).is_relative_to(work):
                    safe = False
        except (OSError, IndexError):
            safe = False
        if loop and safe:
            safe = subprocess.run(['losetup', '--detach', loop], check=False).returncode == 0
        if safe:
            shutil.rmtree(work)
        else:
            print('Bağlı test alanı korunuyor; otomatik silinmedi: ' + str(work), file=sys.stderr)


if __name__ == '__main__':
    main()

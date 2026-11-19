"""Canlı paket / initramfs sessiz atlama regresyonu; gerçek diske yazmaz."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import yaml

from support import ROOT, load

core = load('target_system_checks', 'system/usr/lib/oguzdows/target_system.py')
config = load('target_source_identity', 'scripts/configure.py')
with patch.dict('sys.modules', {'libcalamares': SimpleNamespace()}):
    job = load('target_system_job', 'installer/modules/oguzdowstarget/main.py')
VERSION = '6.12.0-test-amd64'


def put(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def fixture(root):
    put(root, 'var/lib/dpkg/status', 'Package: initramfs-tools\nStatus: install ok installed\n\n')
    put(root, 'usr/sbin/update-initramfs', '#!/bin/sh\nexit 0\n').chmod(0o755)
    put(root, 'boot/vmlinuz-' + VERSION, 'kernel fixture, not bootable')
    (root / 'usr/lib/modules' / VERSION).mkdir(parents=True)
    put(root, 'boot/initrd.img-' + VERSION, 'old live initrd fixture')
    put(root, 'boot/grub/grub.cfg', "menuentry 'OğuzDows' {\n linux /boot/vmlinuz-" + VERSION + " root=UUID=abc ro quiet\n initrd /boot/initrd.img-" + VERSION + '\n}\n')
    return root / ('boot/initrd.img-' + VERSION)


def archive(_path):
    return {'init', 'scripts/local', 'usr/lib/modules/' + VERSION + '/kernel/fs/ext4/ext4.ko'}


class TargetSystemTests(unittest.TestCase):
    def test_zero_exit_without_regenerating_the_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = fixture(root)
            core.require_clean_target(root)
            before = core.kernel_snapshot(root)
            # Eski canlı sarmalayıcı exit 0 döner ama bu dosyayı değiştirmez.
            with self.assertRaisesRegex(core.TargetError, 'yenilenmedi'):
                core.verify_initramfs(root, before, archive)
            image.write_text('new regenerated target initrd with local disk scripts')
            after = core.verify_initramfs(root, before, archive)
            self.assertNotEqual(after, before)
            self.assertEqual(core.verify_grub_menu(root), VERSION)

    def test_all_live_package_states_including_leftover_config_are_fatal(self):
        for package in core.LIVE_PACKAGES:
            for state in ('install ok installed', 'deinstall ok config-files', 'install ok unpacked', ''):
                with self.subTest(package=package, state=state), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    fixture(root)
                    put(root, 'var/lib/dpkg/status', f'Package: {package}\nStatus: {state}\n\n')
                    with self.assertRaisesRegex(core.TargetError, 'temizliği'):
                        core.require_clean_target(root)

    def test_update_initramfs_diversion_is_detected_without_executing_the_wrapper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            for original in ('/usr/sbin/update-initramfs', '/sbin/update-initramfs'):
                put(root, 'var/lib/dpkg/diversions', original + '\n' + original + '.orig.initramfs-tools\nlive-tools\n')
                with self.assertRaisesRegex(core.TargetError, 'yönlendirilmiş'):
                    core.require_clean_target(root)
            put(root, 'var/lib/dpkg/diversions', '/one\n/two\n')
            with self.assertRaisesRegex(core.TargetError, 'bozuk'):
                core.require_clean_target(root)

    def test_missing_empty_wrong_kernel_and_invalid_archive_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = fixture(root)
            before = core.kernel_snapshot(root)
            image.unlink()
            with self.assertRaisesRegex(core.TargetError, 'oluşmadı'):
                core.verify_initramfs(root, before, archive)
            image.write_text('new target image')
            for names in (set(), {'init'}, {'init', 'scripts/local', 'usr/lib/modules/wrong/kernel/ext4.ko'}):
                with self.assertRaises(core.TargetError):
                    core.verify_initramfs(root, before, lambda _: names)
            for before_value in (None, {}, {'another-kernel': None}):
                with self.assertRaisesRegex(core.TargetError, 'eşleşmiyor'):
                    core.verify_initramfs(root, before_value, archive)
            image.write_text('')
            with self.assertRaises(core.TargetError):
                core.kernel_snapshot(root)

    def test_a_kernel_menu_without_the_matching_initrd_or_with_live_boot_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            for text in ("menuentry 'x' {\n linux /boot/vmlinuz-" + VERSION + ' root=UUID=abc\n}\n',
                         'linux /boot/vmlinuz-' + VERSION + ' root=UUID=abc boot=live\ninitrd /boot/initrd.img-' + VERSION,
                         'linux /boot/vmlinuz-' + VERSION + '\ninitrd /boot/initrd.img-' + VERSION,
                         'linux /boot/vmlinuz-' + VERSION + ' root=UUID=abc\ninitrd /boot/initrd.img-missing'):
                put(root, 'boot/grub/grub.cfg', text)
                with self.assertRaisesRegex(core.TargetError, 'birlikte'):
                    core.verify_grub_menu(root)
            put(root, 'boot/grub/grub.cfg', 'linux /vmlinuz-' + VERSION + ' root=/dev/mapper/root ro\ninitrd /intel-ucode.img /initrd.img-' + VERSION)
            self.assertEqual(core.verify_grub_menu(root), VERSION)

    def test_temporary_live_root_multiple_roots_and_wrong_expected_uuid_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            self.assertEqual(core.verify_grub_menu(root, expected_root='UUID=abc'), VERSION)
            with self.assertRaises(core.TargetError):
                core.verify_grub_menu(root, expected_root='UUID=another-target')
            for argument in ('/dev/loop1p3', '/dev/sr0', '/run/live/rootfs/target', '/lib/live/mount/rootfs', 'UUID=abc root=/dev/loop1p1'):
                put(root, 'boot/grub/grub.cfg', 'linux /boot/vmlinuz-' + VERSION + ' root=' + argument + '\ninitrd /boot/initrd.img-' + VERSION)
                with self.subTest(root=argument), self.assertRaisesRegex(core.TargetError, 'birlikte'):
                    core.verify_grub_menu(root)

    def test_live_root_relative_root_and_escape_symlinks_are_rejected(self):
        for root in (Path('/'), Path('.')):
            with self.assertRaises(core.TargetError):
                core.target_root(root)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'boot').symlink_to('/tmp')
            with self.assertRaises(core.TargetError):
                core.kernel_snapshot(root)
            with self.assertRaises(core.TargetError):
                core.inside(root, '../outside')

    def test_calamares_gates_initramfs_and_records_no_physical_boot_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = fixture(root)
            gs = {'rootMountPoint': str(root)}
            storage = SimpleNamespace(value=gs.get, insert=gs.__setitem__)
            phase = {'phase': 'prepare'}
            with patch.object(job.libcalamares, 'globalstorage', storage, create=True), patch.object(job.libcalamares, 'job', SimpleNamespace(configuration=phase), create=True), patch.dict('sys.modules', {'target_system': core}):
                self.assertIsNone(job.run())
                phase['phase'] = 'verify'
                self.assertIn('yenilenmedi', job.run()[1])
                image.write_text('new target initrd')
                with patch.object(core, 'initrd_contents', side_effect=archive):
                    self.assertIsNone(job.run())
                phase['phase'] = 'boot-menu'
                self.assertIsNone(job.run())
                proof = json.loads((root / 'var/log/oguzdows/target-system.json').read_text())
                self.assertFalse(proof['physical_boot_verified'])
                self.assertEqual(proof['kernel'], VERSION)
                self.assertNotIn('complete', proof)
                image.write_text('changed after verification')
                self.assertIn('sonradan değişti', job.run()[1])
                gs.pop('oguzdowsInitramfsVerified')
                self.assertIn('kanıtı yok', job.run()[1])

    def test_critical_purge_is_mandatory_but_optional_drivers_remain_separate(self):
        packages = yaml.safe_load((ROOT / 'installer/modules/packages.conf').read_text())
        self.assertEqual(set(packages['operations'][0]['remove']), core.LIVE_PACKAGES)
        self.assertNotIn('try_remove', str(packages['operations']))
        settings = yaml.safe_load((ROOT / 'installer/settings.conf').read_text())
        sequence = settings['sequence'][1]['exec']
        self.assertLess(sequence.index('packages'), sequence.index('oguzdowstarget@target-prepare'))
        self.assertEqual(sequence[sequence.index('initramfs') - 1:sequence.index('initramfs') + 2],
                         ['oguzdowstarget@target-prepare', 'initramfs', 'oguzdowstarget@target-verify'])
        self.assertLess(sequence.index('bootloader'), sequence.index('oguzdowstarget@target-menu'))
        self.assertLess(sequence.index('oguzdowstarget@target-menu'), sequence.index('umount'))
        self.assertEqual(sequence[-1], 'oguzdowsresult@result-complete')

    def test_source_identity_never_invents_a_revision_if_git_is_missing(self):
        with patch.object(config.subprocess, 'run', side_effect=FileNotFoundError()), patch.dict(os.environ, {'GITHUB_SHA': 'not-a-revision'}):
            self.assertEqual(config.source_identity(), {'source_revision': 'unknown', 'source_dirty': None})
        with patch.object(config.subprocess, 'run', side_effect=FileNotFoundError()), patch.dict(os.environ, {'GITHUB_SHA': 'a' * 40}):
            self.assertEqual(config.source_identity()['source_revision'], 'a' * 40)
        with patch.object(config.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0, 'b' * 40 + '\n'), subprocess.CompletedProcess([], 0, ' M source.py\n')]):
            self.assertTrue(config.source_identity()['source_dirty'])

    def test_target_modules_and_fingerprints_are_staged_on_both_pc_architectures(self):
        settings = yaml.safe_load((ROOT / 'installer/settings.conf').read_text())
        for identifier, phase in (('target-prepare', 'prepare'), ('target-verify', 'verify'), ('target-menu', 'boot-menu')):
            instance = next(i for i in settings['instances'] if i['id'] == identifier)
            self.assertEqual(instance['module'], 'oguzdowstarget')
            self.assertEqual(yaml.safe_load((ROOT / 'installer/modules' / instance['config']).read_text()), {'phase': phase})
        for arch in ('amd64', 'i386'):
            with tempfile.TemporaryDirectory() as directory, patch.object(config, 'source_identity', return_value={'source_revision': 'd' * 40, 'source_dirty': False}):
                config.configure(arch, Path(directory))
                overlay = Path(directory) / 'includes.chroot'
                for path in ('usr/lib/oguzdows/target_system.py', 'etc/calamares/modules/oguzdowstarget/main.py', 'etc/calamares/modules/oguzdowstarget/module.desc'):
                    self.assertTrue((overlay / path).is_file(), path)
                build = json.loads((overlay / 'usr/share/oguzdows/build-info.json').read_text())
                self.assertEqual(len(build['source_revision']), 40)
                self.assertIsInstance(build['source_dirty'], bool)

    def test_lsinitramfs_uses_only_a_fixed_read_only_command(self):
        with patch.object(core.subprocess, 'run', return_value=Mock(stdout='init\nscripts/local\n')) as child:
            self.assertEqual(core.initrd_contents(Path('/tmp/private-initrd')), {'init', 'scripts/local'})
        self.assertEqual(child.call_args.args[0], ['lsinitramfs', '/tmp/private-initrd'])
        self.assertNotIn('shell', child.call_args.kwargs)


if __name__ == '__main__':
    unittest.main()

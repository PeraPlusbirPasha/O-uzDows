"""Gerçek Calamares mount işi; tüm mount/chcon çağrıları sahtedir."""
import copy
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

configure = load('calamares_mount_configure', 'scripts/configure.py')


def packaged_module(name):
    try:
        package = subprocess.run(['dpkg-query', '-L', 'calamares'], check=False,
                                 capture_output=True, text=True, timeout=10)
        return next((Path(line) for line in package.stdout.splitlines()
                     if line.endswith('/' + name + '/main.py') and Path(line).is_file()), None)
    except (OSError, subprocess.SubprocessError):
        return None


def effective_configuration(overlay, name):
    # Module::moduleConfigurationCandidates sırası (uygulama veri dizini
    # geçersiz kılınmamış normal ISO çalıştırması); dokümandaki örnekler okunmaz.
    candidates = [overlay / 'etc/calamares/modules' / (name + '.conf'),
                  Path('/etc/calamares/modules') / (name + '.conf'),
                  Path('/usr/share/calamares/modules') / (name + '.conf')]
    selected = next((path for path in candidates if path.is_file()), None)
    return (yaml.safe_load(selected.read_text()) or {}) if selected else {}, selected


def exercise_native_mount(path, configuration, root, firmware='bios', mount_result=0):
    state = {'partitions': [{'device': '/dev/oguzdows-test-only1', 'mountPoint': '/', 'fs': 'ext4'}],
             'firmwareType': firmware, 'efiSystemPartition': '/boot/efi'}
    mounts = Mock(return_value=mount_result)
    warnings = Mock()
    fake = SimpleNamespace(job=SimpleNamespace(configuration=copy.deepcopy(configuration)),
                           globalstorage=SimpleNamespace(value=state.get, insert=state.__setitem__),
                           utils=SimpleNamespace(mount=mounts, warning=warnings, error=Mock(),
                                                 gettext_path=lambda: '/nonexistent/oguzdows-locales',
                                                 gettext_languages=lambda: ['tr']))
    with patch.dict('sys.modules', {'libcalamares': fake}), patch('sys.dont_write_bytecode', True):
        module = load('native_calamares_mount_contract', path)
        with patch.object(module.tempfile, 'mkdtemp', return_value=str(root)), \
                patch.object(module.subprocess, 'call', return_value=0):
            result = module.run()
    return result, state, mounts, warnings


class CalamaresMountContractTests(unittest.TestCase):
    def native(self):
        if os.environ.get('OGUZDOWS_TEST_TARGET') == 'raspberrypi':
            self.skipTest('Pi Calamares kullanmaz; gerçek PC işi bookworm/trixie CI içinde zorunludur.')
        native = packaged_module('mount')
        if not native:
            if os.environ.get('GITHUB_ACTIONS') == 'true':
                self.fail('CI gerçek Calamares mount işini kurmalı.')
            self.skipTest('Yerelde Calamares yok; iki tabanlı CI gerçek mount işini sınar.')
        return native

    def test_native_pc_requirement_fails_in_ci_and_skips_only_in_explicit_pi_scope(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'OGUZDOWS_TEST_TARGET': 'pc'}), \
                patch(__name__ + '.packaged_module', return_value=None):
            with self.assertRaisesRegex(AssertionError, 'CI gerçek Calamares'):
                self.native()
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'OGUZDOWS_TEST_TARGET': 'raspberrypi'}), \
                patch(__name__ + '.packaged_module') as package:
            with self.assertRaisesRegex(unittest.SkipTest, 'Pi Calamares kullanmaz'):
                self.native()
            package.assert_not_called()

    def arch(self):
        release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines()
                       if '=' in line and not line.startswith('#'))
        suite = release.get('VERSION_CODENAME', '').strip('"')
        arch = {'bookworm': 'i386', 'trixie': 'amd64'}.get(suite)
        if not arch:
            self.fail('Calamares mount sözleşmesi için bilinmeyen taban: ' + suite)
        return arch

    def test_both_architectures_stage_version_correct_explicit_mount_configuration(self):
        for arch in ('amd64', 'i386'):
            with self.subTest(arch=arch), tempfile.TemporaryDirectory() as directory:
                configure.configure(arch, Path(directory))
                overlay = Path(directory) / 'includes.chroot'
                configuration, selected = effective_configuration(overlay, 'mount')
                self.assertEqual(selected, overlay / 'etc/calamares/modules/mount.conf')
                points = {item['mountPoint']: item for item in configuration['extraMounts']}
                self.assertTrue({'/dev', '/dev/pts', '/proc', '/sys', '/run', '/run/udev'} <= set(points))
                for point in ('/dev', '/dev/pts', '/run/udev'):
                    self.assertEqual(points[point]['device'], point)
                    self.assertEqual(points[point]['options'], ['bind'] if arch == 'amd64' else 'bind')
                if arch == 'amd64':
                    self.assertTrue(points['/sys/firmware/efi/efivars']['efi'])
                    self.assertNotIn('extraMountsEfi', configuration)
                else:
                    self.assertNotIn('/sys/firmware/efi/efivars', points)
                    self.assertEqual(configuration['extraMountsEfi'][0]['mountPoint'], '/sys/firmware/efi/efivars')
                self.assertTrue((overlay / 'etc/calamares/modules/oguzdowsmount/main.py').is_file())
        settings = yaml.safe_load((ROOT / 'installer/settings.conf').read_text())
        sequence = settings['sequence'][1]['exec']
        self.assertEqual(sequence[sequence.index('mount') + 1], 'oguzdowsmount@mount-verify')
        self.assertLess(sequence.index('oguzdowsmount@mount-verify'), sequence.index('unpackfs'))
        self.assertEqual(sequence[sequence.index('bootloader') - 1], 'oguzdowsmount@mount-probe')
        for identifier, phase in (('mount-verify', 'mounted'), ('mount-probe', 'grub-probe')):
            instance = next(item for item in settings['instances'] if item['id'] == identifier)
            self.assertEqual(instance['module'], 'oguzdowsmount')
            self.assertEqual(yaml.safe_load((ROOT / 'installer/modules' / instance['config']).read_text()), {'phase': phase})

    def test_actual_package_and_effective_configuration_provide_chroot_mounts(self):
        native = self.native()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            configure.configure(self.arch(), base / 'overlay')
            overlay = base / 'overlay/includes.chroot'
            configuration, selected = effective_configuration(overlay, 'mount')
            print('::notice title=Calamares etkin mount yapılandırması::' + json.dumps(
                {'module': str(native), 'configuration_file': str(selected) if selected else None,
                 'configuration': configuration}, ensure_ascii=False), flush=True)
            for firmware in ('bios', 'efi'):
                with self.subTest(firmware=firmware):
                    result, state, mounts, _ = exercise_native_mount(native, configuration, base / firmware, firmware)
                    self.assertIsNone(result)
                    points = {str(Path(call.args[1]).relative_to(base / firmware)): call.args
                              for call in mounts.call_args_list}
                    for relative in ('dev', 'dev/pts', 'proc', 'sys', 'run', 'run/udev'):
                        self.assertIn(relative, points, 'Etkin mount yapılandırmasında zorunlu bağlantı yok: ' + relative)
                    self.assertEqual(points['dev'][0], '/dev')
                    self.assertIn('bind', points['dev'][3])
                    self.assertEqual(points['proc'][2], 'proc')
                    self.assertEqual(points['sys'][2], 'sysfs')
                    self.assertEqual(state['rootMountPoint'], str(base / firmware))
                    extra_points = {item['mountPoint'] for item in state['extraMounts']}
                    self.assertTrue({'/dev', '/dev/pts', '/proc', '/sys', '/run', '/run/udev'} <= extra_points)
                    self.assertEqual('/sys/firmware/efi/efivars' in extra_points, firmware == 'efi')

    def test_privileged_mount_regression_gates_both_suites_without_cancelling_jobs(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/main.yml').read_text())
        job = workflow['jobs']['installed-boot']
        self.assertEqual(job['container']['options'], '--privileged')
        self.assertEqual(job['strategy']['matrix']['suite'], ['bookworm', 'trixie'])
        step = next(step for step in job['steps'] if 'tests/smoke-calamares-mount.py' in step.get('run', ''))
        self.assertNotIn('continue-on-error', step)
        self.assertIn('calamares', str(job['steps']))
        evidence = next(step for step in job['steps'] if step.get('with', {}).get('name') == 'OguzDows-Calamares-mount-${{ matrix.suite }}')
        self.assertEqual(evidence['if'], 'always()')
        self.assertFalse(workflow['concurrency']['cancel-in-progress'])
        self.assertIn('installed-boot', workflow['jobs']['build']['needs'])
        self.assertEqual((ROOT / 'build.yml').read_text(), (ROOT / '.github/workflows/main.yml').read_text())

    def test_actual_native_mount_does_not_create_implicit_bindings_without_configuration(self):
        native = self.native()
        with tempfile.TemporaryDirectory() as directory:
            result, state, mounts, warnings = exercise_native_mount(native, {}, Path(directory))
            self.assertIsNone(result)  # Yerleşik iş yalnızca uyarır; hata döndürmez.
            self.assertEqual(len(mounts.call_args_list), 1)
            self.assertEqual(state['extraMounts'], [])
            self.assertTrue(any('No extra mounts' in str(entry) for entry in warnings.call_args_list))

    def test_actual_native_unpack_excludes_all_bound_interfaces(self):
        self.native()
        native = packaged_module('unpackfs')
        self.assertIsNotNone(native)
        with tempfile.TemporaryDirectory() as directory:
            configure.configure(self.arch(), Path(directory) / 'overlay')
            configuration, _ = effective_configuration(Path(directory) / 'overlay/includes.chroot', 'mount')
            _, state, _, _ = exercise_native_mount(packaged_module('mount'), configuration, Path(directory) / 'target')
            fake = SimpleNamespace(globalstorage=SimpleNamespace(value=state.get), utils=SimpleNamespace(
                gettext_path=lambda: '/nonexistent/oguzdows-locales', gettext_languages=lambda: ['tr']))
            with patch.dict('sys.modules', {'libcalamares': fake}), patch('sys.dont_write_bytecode', True):
                module = load('native_calamares_unpack_mount_excludes', native)
                excludes = module.global_excludes()
            for relative in ('/dev/', '/dev/pts/', '/proc/', '/sys/', '/run/', '/run/udev/'):
                self.assertIn(relative, excludes)
            self.assertNotIn('/boot/', excludes)

    def test_actual_native_mount_failure_only_warns_so_our_guard_is_required(self):
        native = self.native()
        with tempfile.TemporaryDirectory() as directory:
            configuration = {'extraMounts': [{'device': 'proc', 'fs': 'proc', 'mountPoint': '/proc'}]}
            result, _, _, warnings = exercise_native_mount(native, configuration, Path(directory), mount_result=32)
            self.assertIsNone(result)
            self.assertTrue(any('Cannot mount' in str(entry) for entry in warnings.call_args_list))


if __name__ == '__main__':
    unittest.main()

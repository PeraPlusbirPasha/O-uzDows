"""ISO hedef OS testinin sınırları; bu birim testler VM / disk açmaz."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import yaml

from support import ROOT, load

smoke = load('iso_target_smoke_contract', 'tests/smoke-iso-target.py')


class IsoTargetSmokeContractTests(unittest.TestCase):
    def test_guard_rejects_non_ci_and_non_regular_iso_before_mount_or_mkdtemp(self):
        arguments = ['smoke-iso-target', '--iso', '/dev/null', '--arch', 'amd64', '--expected-revision', 'a' * 40]
        for ci, uid in (('false', 0), ('true', 1000), ('true', 0)):
            with self.subTest(ci=ci, uid=uid), patch('sys.argv', arguments), patch.dict(os.environ, {'CI': ci}), patch.object(smoke.os, 'geteuid', return_value=uid), patch.object(smoke.tempfile, 'mkdtemp') as temp, patch.object(smoke.subprocess, 'run') as child, patch('sys.stderr'):
                with self.assertRaises(SystemExit) as error:
                    smoke.main()
                self.assertEqual(error.exception.code, 2)
                temp.assert_not_called()
                child.assert_not_called()

    def test_vm_boot_requires_uuid_specific_os_proof_not_the_old_grub_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            serial = root / 'target-os-bios.serial.log'
            serial.write_text('OGUZDOWS-INSTALLED-BIOS-OK\n')
            process = Mock()
            process.poll.return_value = 0
            with patch.object(smoke.subprocess, 'Popen', return_value=process), self.assertRaisesRegex(RuntimeError, 'erken kapandı'):
                smoke.boot_os(root / 'private.img', 'bios', root, root, 'abc')
            process.poll.return_value = None
            serial.write_text('OGUZDOWS-TARGET-OS-OK:abc\n')
            with patch.object(smoke.subprocess, 'Popen', return_value=process) as child, patch('builtins.print'):
                smoke.boot_os(root / 'private.img', 'bios', root, root, 'abc')
            command = child.call_args.args[0]
            for bypass in ('-kernel', '-initrd', '-cdrom'):
                self.assertNotIn(bypass, command)
            self.assertIn('none', command)
            self.assertTrue(any('snapshot=on' in arg for arg in command))
            self.assertNotIn('OGUZDOWS-TARGET-OS-OK', str(command))
            process.terminate.assert_called_once()

    def test_unknown_checkout_cleanliness_is_not_called_clean_or_confused_with_known_dirty(self):
        build = {'source_revision': 'a' * 40, 'arch': 'i386', 'source_dirty': False}
        smoke.validate_source(build, 'a' * 40, 'i386')
        build['source_dirty'] = None
        with patch('builtins.print') as notice:
            smoke.validate_source(build, 'a' * 40, 'i386')
        self.assertIn('belirlenemedi (null)', notice.call_args.args[0])
        self.assertIsNone(build['source_dirty'])
        for change in ({'source_dirty': True}, {'source_dirty': 0}, {'source_dirty': 'false'},
                       {'source_revision': 'unknown'}, {'source_revision': 'b' * 40}, {'arch': 'amd64'}):
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                smoke.validate_source({**build, **change}, 'a' * 40, 'i386')
        build.pop('source_dirty')
        with self.assertRaises(RuntimeError):
            smoke.validate_source(build, 'a' * 40, 'i386')

    def test_ci_uuid_link_only_names_its_own_loop_and_never_overwrites_existing_devices(self):
        uuid = '12345678-1234-1234-1234-123456789abc'
        device = '/dev/loop12345p1'
        with tempfile.TemporaryDirectory() as directory, patch.object(Path, 'is_block_device', return_value=True):
            base = Path(directory) / 'uuid'
            owned = smoke.expose_loop_uuid(device, uuid, base)
            self.assertEqual(os.readlink(owned[0]), device)
            self.assertIsNone(smoke.expose_loop_uuid(device, uuid, base))
            smoke.remove_owned_uuid_links([owned])
            self.assertFalse(owned[0].is_symlink())
            owned = smoke.expose_loop_uuid(device, uuid, base)
            owned[0].unlink()
            owned[0].symlink_to('/dev/loop12346p1')
            with self.assertRaisesRegex(RuntimeError, 'başka bir aygıta'):
                smoke.expose_loop_uuid(device, uuid, base)
            smoke.remove_owned_uuid_links([owned])
            self.assertEqual(os.readlink(owned[0]), '/dev/loop12346p1')
        for device_value, uuid_value in (('/dev/sda1', uuid), ('/dev/loop1', uuid), (device, '../escape')):
            with tempfile.TemporaryDirectory() as directory:
                base = Path(directory) / 'must-not-exist'
                with self.assertRaises(RuntimeError):
                    smoke.expose_loop_uuid(device_value, uuid_value, base)
                self.assertFalse(base.exists())
        with tempfile.TemporaryDirectory() as directory, patch.object(Path, 'is_block_device', return_value=False):
            base = Path(directory) / 'must-not-exist'
            with self.assertRaises(RuntimeError):
                smoke.expose_loop_uuid(device, uuid, base)
            self.assertFalse(base.exists())

    def test_real_iso_package_and_diversion_evidence_is_recorded_read_only(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as result:
            root, output = Path(directory), Path(result)
            (root / 'var/lib/dpkg').mkdir(parents=True)
            (root / 'usr/sbin').mkdir(parents=True)
            status = root / 'var/lib/dpkg/status'
            status.write_text('Package: live-tools\nVersion: 1:fixture\nStatus: install ok installed\n\nPackage: unrelated\nVersion: 2\n')
            diversion = root / 'var/lib/dpkg/diversions'
            diversion.write_text('/usr/sbin/update-initramfs\n/usr/sbin/update-initramfs.orig\nlive-tools\n')
            (root / 'usr/sbin/update-initramfs').write_text('# fixture wrapper\n')
            with patch('builtins.print'):
                smoke.record_live_state(root, output, 'before')
            report = json.loads((output / 'target-live-before.json').read_text())
            self.assertEqual(report['packages'], [{'Package': 'live-tools', 'Version': '1:fixture', 'Status': 'install ok installed'}])
            self.assertIn('live-tools', report['diversions'])
            self.assertEqual((output / 'before-update-initramfs.txt').read_text(), '# fixture wrapper\n')
            self.assertEqual(status.read_text().count('Package:'), 2)
            self.assertTrue(diversion.exists())

    def test_iso_artifact_is_gated_by_new_real_os_check_and_failure_evidence_is_kept(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/main.yml').read_text())
        build = workflow['jobs']['build']
        steps = build['steps']
        build_index = next(i for i, s in enumerate(steps) if 'bash build.sh' in s.get('run', ''))
        os_index = next(i for i, s in enumerate(steps) if 'tests/smoke-iso-target.py' in s.get('run', ''))
        upload_index = next(i for i, s in enumerate(steps) if s.get('with', {}).get('name') == 'OguzDows-${{ matrix.arch }}')
        self.assertLess(build_index, os_index)
        self.assertLess(os_index, upload_index)
        self.assertNotIn('continue-on-error', steps[os_index])
        self.assertNotIn('if', steps[upload_index])  # Varsayılan success() zorunlu.
        self.assertIn('--expected-revision "$GITHUB_SHA"', steps[os_index]['run'])
        evidence = next(s for s in steps if s.get('with', {}).get('name') == 'OguzDows-ISO-hedef-test-${{ matrix.arch }}')
        self.assertEqual(evidence['if'], 'always()')
        self.assertEqual(build['container']['options'], '--privileged')
        for name in ('verify', 'installed-boot', 'build'):
            self.assertIn("target != 'pc-diagnostics'", workflow['jobs'][name]['if'])
        diagnostics = workflow['jobs']['diagnostics']
        self.assertIn("target == 'pc-diagnostics'", diagnostics['if'])
        self.assertEqual(diagnostics['permissions']['actions'], 'read')
        self.assertNotIn('bash build.sh', str(diagnostics))
        self.assertTrue(any(s.get('uses', '').startswith('actions/download-artifact@') for s in diagnostics['steps']))
        checkout_index = next(i for i, s in enumerate(steps) if s.get('uses', '').startswith('actions/checkout@'))
        self.assertIn('git ca-certificates', steps[checkout_index - 1]['run'])
        self.assertEqual((ROOT / 'build.yml').read_text(), (ROOT / '.github/workflows/main.yml').read_text())


if __name__ == '__main__':
    unittest.main()

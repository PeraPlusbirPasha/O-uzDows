"""Fotoğraftaki optional Broadcom hatasını diske / APT'ye yazmadan yeniden üretir."""
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from support import ROOT, load

transfer = load('driver_transfer_tests', 'system/usr/lib/oguzdows/driver_transfer.py')
worker = load('target_driver_worker_tests', 'system/usr/lib/oguzdows/install-target-driver.py')
status = load('target_status_tests', 'system/usr/lib/oguzdows/install_status.py')


class TransferTests(unittest.TestCase):
    def test_selected_broadcom_without_matching_device_does_not_stop_base_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(transfer, 'save_plan') as plan, patch('subprocess.run') as process:
                results = transfer.transfer(root, ['broadcom'], ['broadcom'], process, detect=lambda _: [])
            self.assertEqual(results[0]['status'], 'skipped')
            self.assertIn('devam edildi', results[0]['message'])
            process.assert_not_called()
            plan.assert_not_called()

    def test_host_hardware_is_used_even_when_target_sysfs_is_empty(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'sys/bus/pci/devices').mkdir(parents=True)
            calls = []
            def invoke(command):
                calls.append(command)
                data = json.loads((root / transfer.PLAN).read_text())
                self.assertEqual(data['devices'], ['14e4:4353'])
                self.assertTrue(data['approved'])
                self.assertEqual((root / transfer.PLAN).stat().st_mode & 0o777, 0o600)
                return 0
            results = transfer.transfer(root, ['broadcom'], ['broadcom'], invoke, detect=lambda _: ['14e4:4353'])
            self.assertEqual(results[0]['status'], 'installed')
            self.assertEqual(calls, [['/usr/bin/python3', '-I', transfer.WORKER, 'broadcom']])
            self.assertFalse((root / transfer.PLAN).exists())

    def test_failed_optional_package_becomes_explicit_warning_not_fake_driver_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for failure in (17, subprocess.CalledProcessError(3, 'fake')):
                def invoke(_):
                    if isinstance(failure, Exception):
                        raise failure
                    return failure
                results = transfer.transfer(root, ['broadcom'], ['broadcom'], invoke, detect=lambda _: ['14e4:4353'])
                self.assertEqual(results[0]['status'], 'failed')
                self.assertFalse((root / transfer.PLAN).exists())
                session = status.begin(root / 'state')['session']
                status.driver_results(session, results, root / 'state')
                status.stage(session, 'complete', root / 'state')
                data = status.finish(session, 0, root / 'state')
                self.assertEqual(data['outcome'], 'success')
                title, detail = status.description(data)
                self.assertIn('uyarısı', title)
                self.assertIn('Broadcom', detail)
                self.assertIn('failed', json.dumps(data))

    def test_no_live_approval_means_no_package_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch('subprocess.run') as process:
                results = transfer.transfer(Path(temporary), ['broadcom', 'arbitrary;command'], [], process)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['status'], 'skipped')
            self.assertIn('onayı yok', results[0]['message'])
            process.assert_not_called()

    def test_live_root_relative_root_and_symlink_roots_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            link = Path(temporary) / 'target'
            link.symlink_to(Path(temporary), target_is_directory=True)
            for root in (Path('/'), Path('relative'), link):
                with self.assertRaises(ValueError):
                    transfer.transfer(root, [], [], lambda _: 0)

    def test_transfer_plan_never_follows_an_existing_file_or_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / 'untouched'
            outside.write_text('before')
            plan = root / transfer.PLAN
            plan.parent.mkdir()
            plan.symlink_to(outside)
            result = transfer.transfer(root, ['broadcom'], ['broadcom'], lambda _: self.fail('Unsafe plan executed'), detect=lambda _: ['14e4:4353'])
            self.assertEqual(result[0]['status'], 'failed')
            self.assertEqual(outside.read_text(), 'before')

    def test_target_worker_requires_bundled_integrity_and_target_kernel_headers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            modules, boot = root / 'modules', root / 'boot'
            (modules / 'target-kernel/build').mkdir(parents=True)
            boot.mkdir()
            (modules / 'target-kernel/modules.dep').touch()
            (boot / 'vmlinuz-target-kernel').touch()
            with patch.object(worker, 'payload', return_value=Path('/trusted/broadcom.deb')), patch.object(worker.subprocess, 'run') as process:
                with self.assertRaises(ValueError):
                    worker.install('broadcom', io.StringIO(), modules, boot)
                process.assert_not_called()
                (modules / 'target-kernel/build/Makefile').touch()
                self.assertEqual(worker.install('broadcom', io.StringIO(), modules, boot), 0)
                self.assertEqual(process.call_count, 1)
                command = process.call_args.args[0]
                self.assertIn('--no-download', command)
                self.assertIn('--no-remove', command)
                self.assertNotIn('modprobe', ' '.join(command))
                self.assertNotIn('linux-headers-' + worker.os.uname().release, command)
            with patch.object(worker, 'payload', return_value=None), patch.object(worker.subprocess, 'run') as process:
                with self.assertRaises(ValueError):
                    worker.install('broadcom', io.StringIO(), modules, boot)
                process.assert_not_called()

    def test_target_worker_cannot_load_or_unload_live_driver_or_remember_new_consent(self):
        source = (ROOT / 'system/usr/lib/oguzdows/install-target-driver.py').read_text()
        self.assertNotIn('from hardware import', source)
        self.assertNotIn('activate(', source)
        self.assertNotIn('remember(', source)
        self.assertNotIn('is_live(', source)
        with patch.object(worker.os, 'geteuid', return_value=1000), patch.object(worker, 'read_plan') as plan:
            self.assertEqual(worker.main(['broadcom']), 2)
            plan.assert_not_called()


if __name__ == '__main__':
    unittest.main()

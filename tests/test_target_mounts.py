"""Hedef /dev ve GRUB aygıt denetimi; gerçek mount/disk/chroot çalıştırılmaz."""
import copy
import os
import stat
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from support import load

fake = SimpleNamespace(utils=SimpleNamespace(debug=Mock()))
with patch.dict('sys.modules', {'libcalamares': fake}):
    guard = load('oguzdows_mount_guard', 'installer/modules/oguzdowsmount/main.py')


def fixture(root):
    root = root.resolve()
    for point in guard.REQUIRED | {'/boot/grub'}:
        (root / point.lstrip('/')).mkdir(parents=True, exist_ok=True)
    for name in ('null', 'zero'):
        (root / 'dev' / name).write_text('device placeholder, not a real node')
    partitions = [{'mountPoint': '/', 'device': '/dev/null', 'fs': 'ext4'}]
    extras = [{'mountPoint': point} for point in guard.REQUIRED]
    table = {str(root): {'device_id': '8:1', 'fs': 'ext4'}}
    types = {'/proc': 'proc', '/sys': 'sysfs', '/dev/pts': 'devpts', '/run': 'tmpfs'}
    for point in guard.REQUIRED:
        table[str(root / point.lstrip('/'))] = {'device_id': '0:1', 'fs': types.get(point, 'tmpfs')}
    return partitions, extras, table


def block(device):
    return SimpleNamespace(st_mode=stat.S_IFBLK | 0o600,
                           st_rdev=os.makedev(8, 2 if str(device).endswith('zero') else 1))


def fake_devices(stack, root):
    original = os.stat
    def info(path, *args, **kwargs):
        if str(path) in {str(root / 'dev/null'), str(root / 'dev/zero')}:
            return block(path)
        return original(path, *args, **kwargs)
    stack.enter_context(patch.object(guard, 'block_info', side_effect=block))
    stack.enter_context(patch.object(guard.os, 'stat', side_effect=info))
    stack.enter_context(patch.object(guard.os.path, 'samefile', return_value=True))


class TargetMountTests(unittest.TestCase):
    def test_mountinfo_parses_escaped_points_without_shell_or_subprocess(self):
        text = '42 30 8:1 / /tmp/target\\040space rw,relatime - ext4 /dev/test1 rw\n'
        self.assertEqual(guard.mount_table(text), {'/tmp/target space': {'device_id': '8:1', 'fs': 'ext4'}})
        for bad in ('garbage', '1 2 3 4 5 - ext4 /dev/a rw', '1 2 3 4 5 6 - ext4'):
            with self.assertRaises(guard.MountError):
                guard.mount_table(bad)

    def test_real_char_devices_and_non_dev_paths_cannot_be_target_blocks(self):
        for path in ('/dev/null', '/tmp/not-a-device', 'sdb1', None):
            with self.assertRaises(guard.MountError):
                guard.block_info(path)
        self.assertEqual(guard.device_path({'device': '/dev/test1', 'luksMapperName': 'luks-test'}), '/dev/mapper/luks-test')
        for name in ('../escape', '..', '.', 'name/other', True):
            with self.assertRaises(guard.MountError):
                guard.device_path({'luksMapperName': name})

    def test_selected_root_and_all_bindings_are_checked_without_commands_or_writes(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            partitions, extras, table = fixture(root)
            before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            fake_devices(stack, root)
            child = stack.enter_context(patch.object(guard.subprocess, 'run'))
            self.assertEqual(guard.verify_mounts(root, partitions, extras, table), root)
            child.assert_not_called()
            self.assertEqual(before, {name: Path(name).read_bytes() for name in before})

    def test_missing_extra_exclusions_or_mounts_and_wrong_root_device_are_fatal(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            partitions, extras, table = fixture(root)
            fake_devices(stack, root)
            for bad in (None, [], extras[:-1]):
                with self.subTest(extras=bad), self.assertRaisesRegex(guard.MountError, 'extraMounts'):
                    guard.verify_mounts(root, partitions, bad, table)
            for point in guard.REQUIRED | {'/'}:
                bad = copy.deepcopy(table)
                del bad[str(root if point == '/' else root / point.lstrip('/'))]
                with self.subTest(missing=point), self.assertRaises(guard.MountError):
                    guard.verify_mounts(root, partitions, extras, bad)
            table[str(root)]['device_id'] = '8:9'
            with self.assertRaisesRegex(guard.MountError, 'Seçilen bölüm'):
                guard.verify_mounts(root, partitions, extras, table)

    def test_wrong_pseudo_filesystem_or_unbound_device_directory_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            partitions, extras, table = fixture(root)
            fake_devices(stack, root)
            for point in ('/proc', '/sys', '/run', '/dev/pts'):
                bad = copy.deepcopy(table)
                bad[str(root / point.lstrip('/'))]['fs'] = 'ext4'
                with self.subTest(point=point), self.assertRaisesRegex(guard.MountError, 'türü yanlış'):
                    guard.verify_mounts(root, partitions, extras, bad)
            with patch.object(guard.os.path, 'samefile', return_value=False), self.assertRaisesRegex(guard.MountError, 'görünmüyor'):
                guard.verify_mounts(root, partitions, extras, table)
            (root / 'run/udev').rmdir()
            (root / 'run/udev').symlink_to('/tmp')
            with self.assertRaisesRegex(guard.MountError, 'güvenli değil'):
                guard.verify_mounts(root, partitions, extras, table)

    def test_missing_or_wrong_target_dev_node_is_not_substituted_with_host_visibility(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            partitions, extras, table = fixture(root)
            fake_devices(stack, root)
            old_stat = guard.os.stat.side_effect
            def wrong_node(path, *args, **kwargs):
                if str(path) == str(root / 'dev/null'):
                    return block('/dev/zero')
                return old_stat(path, *args, **kwargs)
            guard.os.stat.side_effect = wrong_node
            with self.assertRaisesRegex(guard.MountError, 'seçilen bölüm görünmüyor'):
                guard.verify_mounts(root, partitions, extras, table)

    def test_separate_boot_is_used_instead_of_root_and_must_be_unique(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            partitions, extras, table = fixture(root)
            fake_devices(stack, root)
            partitions.append({'mountPoint': '/boot', 'device': '/dev/zero', 'fs': 'ext4'})
            table[str(root / 'boot')] = {'device_id': '8:2', 'fs': 'ext4'}
            self.assertEqual(guard.verify_mounts(root, partitions, extras, table), root)
            output = Mock(return_value='/dev/zero\n')
            self.assertEqual(guard.probe_boot(root, partitions, output), '/dev/zero')
            output.assert_called_once_with(['grub-probe', '--target=device', '/boot/grub'], '', 30)
            partitions.append(dict(partitions[1]))
            with self.assertRaisesRegex(guard.MountError, 'tekil değil'):
                guard.verify_mounts(root, partitions, extras, table)

    def test_probe_failure_or_another_device_prevents_grub_write_and_keeps_original_error(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(guard, 'block_info', side_effect=block):
            root = Path(directory)
            partitions, _, _ = fixture(root)
            message = 'cannot find a device for /boot/grub (is /dev mounted?)'
            with self.assertRaisesRegex(guard.MountError, 'cannot find a device'):
                guard.probe_boot(root, partitions, Mock(side_effect=subprocess.CalledProcessError(1, ['grub-probe'], output=message)))
            for answer in ('', '/dev/zero\n', '/dev/null\n/dev/zero\n'):
                with self.subTest(answer=answer), self.assertRaisesRegex(guard.MountError, 'eşleşmiyor'):
                    guard.probe_boot(root, partitions, Mock(return_value=answer))
            (root / 'boot/grub').rmdir()
            output = Mock(return_value='/dev/null\n')
            guard.probe_boot(root, partitions, output)
            output.assert_called_once_with(['grub-probe', '--target=device', '/boot'], '', 30)

    def test_job_reports_visible_failure_before_copy_or_probe_and_never_pretends_success(self):
        state = {'rootMountPoint': '/tmp/test-only', 'partitions': []}
        job = SimpleNamespace(configuration={'phase': 'mounted'})
        utils = SimpleNamespace(check_target_env_output=Mock(), debug=Mock())
        with patch.object(guard.libcalamares, 'globalstorage', SimpleNamespace(value=state.get), create=True), \
                patch.object(guard.libcalamares, 'job', job, create=True), patch.object(guard.libcalamares, 'utils', utils), \
                patch.object(guard, 'verify_mounts', side_effect=guard.MountError('target /dev missing')):
            result = guard.run()
            self.assertIn('bağlantıları', result[0])
            self.assertIn('/dev missing', result[1])
            utils.check_target_env_output.assert_not_called()
        with patch.object(guard.libcalamares, 'globalstorage', SimpleNamespace(value=state.get), create=True), \
                patch.object(guard.libcalamares, 'job', job, create=True), patch.object(guard.libcalamares, 'utils', utils), \
                patch.object(guard, 'verify_mounts', return_value=Path('/tmp/test-only')), \
                patch.object(guard, 'probe_boot', return_value='/dev/test-only1') as probe:
            self.assertIsNone(guard.run())
            probe.assert_not_called()
            job.configuration['phase'] = 'grub-probe'
            self.assertIsNone(guard.run())
            probe.assert_called_once()
            job.configuration['phase'] = 'invalid'
            self.assertIn('aşaması', guard.run()[1])

    def test_privileged_smoke_rejects_non_ci_and_physical_device_arguments_before_any_work(self):
        smoke = load('native_mount_smoke_contract', 'tests/smoke-calamares-mount.py')
        for ci, uid, extra in (('false', 0, []), ('true', 1000, []), ('true', 0, ['--device', '/dev/sda'])):
            with self.subTest(ci=ci, uid=uid, extra=extra), \
                    patch('sys.argv', ['smoke-calamares-mount', *extra]), patch.dict(os.environ, {'CI': ci}), \
                    patch.object(smoke.os, 'geteuid', return_value=uid), patch('sys.stderr'), \
                    patch.object(smoke.tempfile, 'mkdtemp') as temp, patch.object(smoke.subprocess, 'run') as child:
                with self.assertRaises(SystemExit) as result:
                    smoke.main()
                self.assertEqual(result.exception.code, 2)
                temp.assert_not_called()
                child.assert_not_called()

    def test_live_root_and_relative_or_missing_targets_are_rejected(self):
        for root in ('/', '.', '/nonexistent-oguzdows-test'):
            with self.assertRaises(guard.MountError):
                guard.target_root(root)


if __name__ == '__main__':
    unittest.main()

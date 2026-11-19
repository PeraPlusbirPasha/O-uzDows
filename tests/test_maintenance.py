"""Bakım güvenlik sözleşmesi; gerçek APT kurulumu veya sistem dosyası yazımı yok."""
import base64
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from support import ROOT, load

core = load('maintenance_test', 'system/usr/lib/oguzdows/maintenance.py')
helper = load('maintenance_helper_test', 'system/usr/local/sbin/oguzdows-maintenance')
helper.core = core
PC = {'arch': 'amd64', 'suite': 'trixie'}
OLD = {'arch': 'i386', 'suite': 'bookworm'}
PLAN = 'Reading package lists...\nInst firmware-realtek [1] (2 Debian:13/trixie [all])\nConf firmware-realtek (2 Debian:13/trixie [all])\n'
KEY = ROOT / 'system/usr/share/keyrings/oguzdows-pardus.asc'
PREF = ROOT / 'system/etc/apt/preferences.d/oguzdows-pardus'


def cache_for(name='firmware-realtek', version='2', origin='Debian', suite='trixie', trusted=True, arch='all'):
    return {name: NS(candidate=NS(version=version, architecture=arch, origins=[NS(origin=origin, codename=suite, trusted=trusted)]))}


def release(stamp=None):
    stamp = stamp or datetime.now(timezone.utc)
    return ('Origin: Pardus\nSuite: yirmibes\nCodename: yirmibes\nArchitectures: amd64 arm64 i386\nDate: '
            + stamp.strftime('%a, %d %b %Y %H:%M:%S +0000') + '\n')


class MaintenanceTests(unittest.TestCase):
    def test_build_identity_fails_closed_and_requires_known_arch_suite_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'build.json'
            for value in ('bad json', '[]', '{}', '{"arch":"arm64","suite":"bookworm"}',
                          '{"arch":"amd64","suite":"bookworm"}', '{"arch":"amd64","suite":"trixie","platform":"raspberrypi"}'):
                path.write_text(value)
                with self.subTest(value=value), self.assertRaises(core.MaintenanceError):
                    core.build_info(path)
            for data in (PC, OLD):
                path.write_text(json.dumps(data))
                self.assertEqual(core.build_info(path), data)

    def test_fixed_requests_never_accept_commands_packages_or_distribution_upgrade(self):
        for request in ('', 'dist-upgrade', 'full-upgrade', 'install bash', 'pardus:libc6', 'desktop:kde;id',
                        'driver:--allow-unauthenticated', 'upgrade\nrm -rf /'):
            with self.subTest(request=request), self.assertRaises(core.MaintenanceError):
                core.apt_command(request, PC, suggestions=[])
        for request in ('desktop:kde', 'desktop:gnome', 'pardus:pardus-pen'):
            with self.assertRaises(core.MaintenanceError):
                core.apt_command(request, OLD)
        with self.assertRaises(core.MaintenanceError):
            core.apt_command('driver:realtek', PC, suggestions=[])
        command = core.apt_command('driver:realtek', PC, suggestions=[{'id': 'realtek', 'packages': ['firmware-realtek']}])
        self.assertEqual(command[-2:], ['install', 'firmware-realtek'])

    def test_all_apt_actions_keep_verification_no_removal_and_fixed_environment(self):
        for request in ('upgrade', 'desktop:kde', 'desktop:gnome', 'pardus:pardus-pen'):
            for simulate in (False, True):
                command = core.apt_command(request, PC, simulate)
                self.assertIn('--no-remove', command)
                self.assertIn('--simulate' if simulate else '--assume-yes', command)
                self.assertNotIn('--allow-downgrades', command)
                self.assertIn('APT::Get::AllowUnauthenticated=false', command)
                self.assertIn('Acquire::AllowInsecureRepositories=false', command)
        self.assertNotIn('APT_CONFIG', core.ENV)
        self.assertNotIn('PYTHONPATH', core.ENV)
        self.assertIn('gnome-session-xsession', core.DESKTOPS['gnome'])
        self.assertIn('kwin-x11', core.DESKTOPS['kde'])
        self.assertNotIn('task-kde-desktop', core.DESKTOPS['kde'])
        self.assertNotIn('gdm3', core.DESKTOPS['gnome'])

    def test_plan_parsing_is_strict_about_removal_and_version_format(self):
        self.assertEqual(core.parse_plan(PLAN)[0]['version'], '2')
        self.assertEqual(core.parse_plan('0 upgraded, 0 newly installed.\n'), [])
        for suffix in (' []', ' [other:amd64 ]', ' [libfoo:amd64 ] [libbar:amd64 ]'):
            parsed = core.parse_plan(PLAN.splitlines()[1] + suffix + '\n')
            self.assertEqual((parsed[0]['package'], parsed[0]['version']), ('firmware-realtek', '2'))
        for text in (PLAN + 'Remv important [1]\n', 'Inst -o (1 repo [all])', 'Inst broken output', 'Inst bad/name (1 repo [all])',
                     'Inst valid (1 repo [all]) arbitrary trailing text'):
            with self.subTest(text=text), self.assertRaises(core.MaintenanceError):
                core.parse_plan(text)

    def test_every_changed_package_requires_exact_version_trusted_origin_and_base(self):
        changes = core.parse_plan(PLAN)
        core.verify_origins(changes, cache_for(), 'upgrade', PC)
        for fields in ({'origin': 'Ubuntu'}, {'origin': 'Kali'}, {'origin': 'Pardus'}, {'suite': 'forky'},
                       {'trusted': False}, {'version': '3'}, {'arch': 'arm64'}):
            with self.subTest(fields=fields), self.assertRaises(core.MaintenanceError):
                core.verify_origins(changes, cache_for(**fields), 'upgrade', PC)
        for suite in ('trixie-security', 'trixie-updates'):
            core.verify_origins(changes, cache_for(suite=suite), 'upgrade', PC)

    def test_pardus_is_not_a_dependency_or_core_package_backdoor(self):
        changes = [{'package': 'pardus-pen', 'version': '2'}]
        cache = cache_for(name='pardus-pen', origin='Pardus', suite='yirmibes')
        core.verify_origins(changes, cache, 'pardus:pardus-pen', PC)
        core.verify_origins(changes, cache, 'upgrade', PC)
        for request, info in (('desktop:kde', PC), ('upgrade', OLD)):
            with self.assertRaises(core.MaintenanceError):
                core.verify_origins(changes, cache, request, info)
        with self.assertRaises(core.MaintenanceError):
            core.verify_origins([{'package': 'libc6', 'version': '2'}], cache_for(name='libc6', origin='Pardus', suite='yirmibes'), 'pardus:pardus-pen', PC)

    def test_preview_does_not_install_and_apply_reconfirms_exact_plan(self):
        execute = Mock(return_value=PLAN)
        plan = core.make_plan('upgrade', PC, execute, cache_for())
        self.assertRegex(plan['token'], r'^[0-9a-f]{64}$')
        self.assertEqual(execute.call_count, 1)
        self.assertIn('--simulate', execute.call_args.args[0])
        execute.reset_mock()
        result = core.apply_plan('upgrade', plan['token'], PC, execute, cache_for())
        self.assertEqual(result['changed'], 1)
        self.assertEqual(execute.call_count, 2)
        self.assertIn('--simulate', execute.call_args_list[0].args[0])
        self.assertIn('--assume-yes', execute.call_args_list[1].args[0])
        execute.reset_mock()
        execute.return_value = PLAN + 'The following packages have been kept back: example\n'
        with self.assertRaisesRegex(core.MaintenanceError, 'değişti'):
            core.apply_plan('upgrade', plan['token'], PC, execute, cache_for())
        self.assertEqual(execute.call_count, 1)
        execute.reset_mock()
        with self.assertRaises(core.MaintenanceError):
            core.apply_plan('upgrade', 'not-a-token', PC, execute, cache_for())
        execute.assert_not_called()

    def test_empty_plan_does_not_run_a_mutation(self):
        execute = Mock(return_value='Nothing to do\n')
        plan = core.make_plan('upgrade', PC, execute, {})
        execute.reset_mock()
        self.assertEqual(core.apply_plan('upgrade', plan['token'], PC, execute, {})['changed'], 0)
        self.assertEqual(execute.call_count, 1)

    def test_firmware_detection_is_hardware_gated_and_suite_aware(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, vendor, kind in (('gpu', '0x8086', '0x030000'), ('wifi', '0x10ec', '0x028000'), ('disk', '0x8086', '0x010100')):
                path = root / 'pci/devices' / name
                path.mkdir(parents=True)
                (path / 'vendor').write_text(vendor)
                (path / 'class').write_text(kind)
            (root / 'pci/devices/wifi/driver').symlink_to('/sys/fixture/driver')
            suggestions = {row['id']: row for row in core.driver_suggestions(root)}
            self.assertEqual(set(suggestions), {'intel-graphics', 'realtek'})
            self.assertFalse(suggestions['realtek']['unbound'])
            self.assertTrue(suggestions['intel-graphics']['unbound'])
            old = {row['id']: row for row in core.driver_suggestions(root, 'bookworm')}
            self.assertEqual(old['intel-graphics']['packages'], ['firmware-misc-nonfree'])


class PardusTests(unittest.TestCase):
    def test_bundled_key_is_pinned_to_one_official_production_fingerprint(self):
        self.assertEqual(hashlib.sha256(KEY.read_bytes()).hexdigest(), core.PARDUS_KEY_SHA256)
        block = ''.join(line for line in KEY.read_text().splitlines() if line and not line.startswith(('-----', '=')))
        packet = base64.b64decode(block)
        self.assertEqual(packet[0], 0x99)
        length = int.from_bytes(packet[1:3], 'big')
        fingerprint = hashlib.sha1(packet[:3+length]).hexdigest().upper()
        self.assertEqual(fingerprint, core.PARDUS_FINGERPRINT)
        self.assertEqual(PREF.read_text(), core.pardus_preferences())
        source = (ROOT / 'system/etc/apt/sources.list.d/oguzdows-pardus.sources').read_text()
        self.assertEqual(source, core.pardus_source(False))
        self.assertIn('Enabled: no', source)
        for bad in ('trusted=yes', 'AllowInsecure: yes', 'yirmibes-deb', 'http://'):
            self.assertNotIn(bad, source)
        self.assertIn('Pin-Priority: -1', PREF.read_text())

    def test_channel_cannot_enable_without_key_pins_base_and_current_signature(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            channel = root / 'sources/channel.sources'
            verifier = Mock(return_value=release())
            for info, key, pref in ((OLD, KEY, PREF), (PC, root / 'missing', PREF), (PC, KEY, root / 'missing')):
                with self.assertRaises(core.MaintenanceError):
                    core.atomic_channel(True, info, channel, key, pref, verifier)
                self.assertFalse(channel.exists())
            verifier.assert_not_called()
            with self.assertRaises(core.MaintenanceError):
                core.atomic_channel(True, PC, channel, KEY, PREF)
            verifier.side_effect = core.MaintenanceError('İmza geçersiz')
            with self.assertRaises(core.MaintenanceError):
                core.atomic_channel(True, PC, channel, KEY, PREF, verifier)
            self.assertFalse(channel.exists())
            verifier.side_effect = None
            core.atomic_channel(True, PC, channel, KEY, PREF, verifier)
            self.assertIn('Enabled: yes', channel.read_text())
            self.assertFalse(channel.with_suffix('.sources.new').exists())
            core.atomic_channel(False, OLD, channel, root / 'missing', root / 'missing')
            self.assertIn('Enabled: no', channel.read_text())

    def test_changed_preferences_and_symlink_targets_never_get_enabled(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key, pref, channel = root / 'key', root / 'pref', root / 'channel'
            key.write_bytes(KEY.read_bytes())
            pref.write_text(core.pardus_preferences().replace('-1', '500'))
            with self.assertRaises(core.MaintenanceError):
                core.atomic_channel(True, PC, channel, key, pref, release)
            pref.write_text(core.pardus_preferences())
            key.write_bytes(KEY.read_bytes() + b'\n')
            with self.assertRaises(core.MaintenanceError):
                core.atomic_channel(True, PC, channel, key, pref, release)
            original = root / 'original'
            original.write_text('do not overwrite')
            channel.symlink_to(original)
            with self.assertRaises(core.MaintenanceError):
                core.atomic_channel(False, PC, channel)
            self.assertEqual(original.read_text(), 'do not overwrite')

    def test_release_identity_and_freshness_are_not_inferred_from_url(self):
        now = datetime(2026, 11, 17, tzinfo=timezone.utc)
        valid = release(now)
        core.validate_pardus_release(valid, now)
        for text in (valid.replace('Origin: Pardus', 'Origin: Something'), valid.replace('yirmibes', 'yirmiuc'),
                     valid.replace('amd64 ', ''), release(datetime(2025, 11, 17, tzinfo=timezone.utc)),
                     release(datetime(2027, 11, 17, tzinfo=timezone.utc)), valid.replace('Date:', 'No-Date:')):
            with self.subTest(text=text), self.assertRaises(core.MaintenanceError):
                core.validate_pardus_release(text, now)

    def test_https_downgrade_is_rejected(self):
        with self.assertRaises(core.MaintenanceError):
            helper.HTTPSRedirects().redirect_request(None, None, 302, '', {}, 'http://mirror.invalid/file')

    @unittest.skipUnless(shutil.which('gpgv'), 'gpgv yok')
    def test_real_gpgv_rejects_unsigned_release_before_it_can_enable_anything(self):
        response = Mock()
        response.url = core.PARDUS_INRELEASE
        response.read.return_value = release().encode()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = response
        def execute(command):
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode:
                raise core.MaintenanceError('invalid signature')
            return result.stdout
        with patch.object(core, 'PARDUS_KEY', KEY), patch.object(helper.urllib.request, 'build_opener', return_value=opener), self.assertRaises(core.MaintenanceError):
            helper.verify_pardus(execute)


class HelperTests(unittest.TestCase):
    def test_no_privileges_or_invalid_actions_stop_before_locks_apt_and_network(self):
        for uid, args in ((1000, ['refresh']), (0, ['exec', '/bin/sh']), (0, []), (0, ['refresh', 'extra']), (0, ['flatpak-system-update'])):
            with patch.object(helper.os, 'geteuid', return_value=uid), patch('sys.argv', ['helper', *args]), patch.object(core, 'build_info') as build, contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(helper.main(), 2)
                self.assertIn('error', json.loads(output.getvalue()))
                build.assert_not_called()

    def test_real_posix_list_lock_contention_stops_before_apt_without_deleting_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            listing, own = root / 'apt-lists-lock', root / 'our-lock'
            listing.touch()
            child_code = ('import fcntl,sys; stream=open(sys.argv[1], "r+"); '
                          'fcntl.lockf(stream, fcntl.LOCK_EX | fcntl.LOCK_NB); '
                          'print("locked", flush=True); sys.stdin.read(1)')
            with subprocess.Popen([sys.executable, '-c', child_code, str(listing)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as holder:
                try:
                    self.assertEqual(holder.stdout.readline().strip(), 'locked')
                    real_open = os.open
                    def remap(path, flags, mode=0o777):
                        mapped = {'/run/lock/oguzdows-maintenance.lock': own, '/var/lib/apt/lists/lock': listing}
                        self.assertIn(str(path), mapped, 'Kilit reddinden sonra log / paket dosyası açılmamalı.')
                        return real_open(mapped[str(path)], flags, mode)
                    with patch.object(helper.os, 'geteuid', return_value=0), patch('sys.argv', ['helper', 'plan', 'upgrade']), patch.object(core, 'build_info', return_value=PC), patch.object(helper.subprocess, 'check_output', return_value='amd64'), patch.object(helper.os, 'open', side_effect=remap), patch.object(core, 'make_plan') as plan, contextlib.redirect_stdout(io.StringIO()) as output:
                        self.assertEqual(helper.main(), 1)
                        plan.assert_not_called()
                        self.assertIn('Kilit dosyasını silmeyin', json.loads(output.getvalue())['error'])
                    self.assertTrue(listing.exists())
                    self.assertIsNone(holder.poll())
                finally:
                    holder.communicate('x', timeout=5)
            # finally'de hem helper kilidi hem de lists dosya tanıtıcısı kapanır.
            descriptor = os.open(own, os.O_RDWR)
            try:
                helper.fcntl.flock(descriptor, helper.fcntl.LOCK_EX | helper.fcntl.LOCK_NB)
            finally:
                os.close(descriptor)

    def test_live_mutation_and_actual_architecture_mismatch_stop_before_lock(self):
        for live, arch in ((True, 'amd64'), (False, 'i386')):
            with patch.object(helper.os, 'geteuid', return_value=0), patch('sys.argv', ['helper', 'apply', 'upgrade', 'a' * 64]), patch.object(core, 'build_info', return_value=PC), patch.object(helper.subprocess, 'check_output', return_value=arch), patch.object(helper, 'is_live', return_value=live), patch.object(helper.os, 'open') as opened, contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(helper.main(), 1)
                opened.assert_not_called()
                self.assertIn('error', json.loads(output.getvalue()))


if __name__ == '__main__':
    unittest.main()

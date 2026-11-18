"""Sonuç protokolü ve Rıfkı; gerçek disk, kurucu veya ses aygıtı kullanılmaz."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from support import ROOT, load

state = load('oguzdows_install_status_test', 'system/usr/lib/oguzdows/install_status.py')
runner = load('oguzdows_runner_test', 'system/usr/lib/oguzdows/run-installer.py')
model = load('oguzdows_rifki_model_test', 'system/usr/lib/oguzdows/rifki_model.py')
boot_report = load('oguzdows_boot_report_test', 'system/usr/lib/oguzdows/boot_report.py')


class InstallationResults(unittest.TestCase):
    def test_zero_exit_without_completion_proof_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = state.begin(root)['session']
            result = state.finish(session, 0, root)
            self.assertEqual(result['outcome'], 'cancelled')
            self.assertFalse(result['complete'])
        self.assertEqual(state.from_output(0, '')['outcome'], 'unknown')

    def test_started_but_missing_last_job_is_incomplete_even_with_zero_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = state.begin(root)['session']
            state.stage(session, 'partition', root)
            self.assertEqual(state.finish(session, 0, root)['outcome'], 'incomplete')

    def test_old_success_never_confirms_a_new_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = state.begin(root)['session']
            state.stage(first, 'complete', root)
            second = state.begin(root)['session']
            self.assertNotEqual(first, second)
            with self.assertRaises(ValueError):
                state.stage(first, 'complete', root)
            self.assertNotEqual(state.finish(second, 0, root)['outcome'], 'success')

    def test_success_requires_matching_final_marker_and_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = state.begin(root)['session']
            state.stage(session, 'partition', root, firmware='bios', target='/dev/test')
            state.stage(session, 'complete', root)
            state.stage(session, 'copying', root)
            result = state.finish(session, 0, root)
            self.assertEqual(result['outcome'], 'success')
            self.assertTrue(result['complete'])
            self.assertEqual(result['stage'], 'complete')
            self.assertEqual(state.from_output(0, state.PREFIX + json.dumps(result)), result)
            title, detail = state.description(result)
            self.assertIn('başarıyla', title)
            self.assertIn('ayrıca', detail)
            self.assertIn('/dev/test', detail)

    def test_a_marker_without_a_published_final_state_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current = state.begin(root)
            state.atomic_json(root / ('complete-' + current['session'] + '.json'), {'session': current['session'], 'complete': True})
            self.assertNotEqual(state.finish(current['session'], 0, root)['outcome'], 'success')

    def test_forged_public_success_without_marker_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current = state.begin(root)
            current.update(outcome='success', complete=True)
            state.atomic_json(root / 'status.json', current)
            self.assertNotEqual(state.finish(current['session'], 0, root)['outcome'], 'success')
        self.assertNotEqual(state.from_output(0, state.PREFIX + '{bad json}')['outcome'], 'success')
        self.assertNotEqual(state.from_output(0, state.PREFIX + json.dumps({'outcome': 'success'}))['outcome'], 'success')

    def test_unsafe_directory_and_stale_or_invalid_session_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                state.stage('../../unsafe', 'complete', root)
            root.chmod(0o777)
            with self.assertRaises(OSError):
                state.begin(root)
            root.chmod(0o700)

    def test_failure_and_auth_cancellation_have_unambiguous_text(self):
        for code, expected in ((1, 'failed'), (126, 'cancelled'), (127, 'cancelled'), (10, 'cancelled')):
            data = state.from_output(code, '')
            self.assertEqual(data['outcome'], expected)
            self.assertNotIn('başarıyla', state.description(data)[0])

    def test_preparation_failure_never_launches_the_installer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (root / 'log').open('w') as log:
                with patch.object(runner.subprocess, 'run', return_value=subprocess.CompletedProcess([], 4)) as process:
                    result = runner.supervise(['fake-prepare'], ['fake-installer'], log, root / 'state')
            self.assertEqual(process.call_count, 1)
            self.assertEqual(result['outcome'], 'failed')

    def test_real_child_process_propagates_only_its_own_session_and_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = "import os,sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); import install_status; install_status.stage(os.environ['OGUZDOWS_INSTALL_SESSION'],'complete',Path(sys.argv[2]))"
            with (root / 'log').open('w') as log:
                result = runner.supervise([sys.executable, '-c', 'pass'], [sys.executable, '-c', child, str(ROOT / 'system/usr/lib/oguzdows'), str(root / 'state')], log, root / 'state')
            self.assertEqual(result['outcome'], 'success')

    def test_success_job_is_after_umount_and_installer_no_longer_auto_closes(self):
        config = yaml.safe_load((ROOT / 'installer/settings.conf').read_text())
        sequence = config['sequence'][1]['exec']
        self.assertEqual(sequence[-2:], ['umount', 'oguzdowsresult@result-complete'])
        self.assertEqual(sequence[0], 'oguzdowsresult@result-start')
        self.assertFalse(config['quit-at-end'])
        self.assertEqual(yaml.safe_load((ROOT / 'installer/modules/result-complete.conf').read_text()), {'stage': 'complete'})


class RifkiTests(unittest.TestCase):
    def test_turkish_questions_and_all_actions_are_bounded(self):
        expected = [('DİSK BÖLÜMÜ', 'disk'), ('Wi-Fi internet', None), ('SÜRÜCÜLER', None), ('Duvar kâğıdı', None), ('Rıfkı merhaba', 'help')]
        for question, clip in expected:
            answer = model.reply(question)
            self.assertTrue(answer['text'])
            self.assertEqual(answer['clip'], clip)
            self.assertIn(answer['action'], (None, 'boot-report', 'network', 'drivers', 'wallpapers', 'install'))
        self.assertEqual(model.reply('sudo grub-install /dev/test')['action'], 'boot-report')
        self.assertEqual(model.reply('Reboot and Select proper Boot device')['action'], 'boot-report')

    def test_no_fake_success_or_general_ai_claim(self):
        self.assertEqual(model.reply('sonuç', {'outcome': 'unknown'})['clip'], 'failure')
        self.assertIn('doğrulanamadı', model.reply('bitti mi')['text'])
        self.assertIn('Genel amaçlı', model.reply('bana bir roman yaz')['text'])
        self.assertEqual(model.reply('bitti', {'outcome': 'success', 'complete': True})['clip'], 'success')

    def test_boot_report_only_invokes_read_only_commands(self):
        with patch.object(boot_report, 'command_output', return_value='test disk list') as command:
            text = boot_report.report()
        self.assertIn('test disk list', text)
        self.assertIn('tek başına kanıtlamaz', text)
        self.assertTrue(all(call.args[0][0] == '/usr/bin/lsblk' for call in command.call_args_list))
        self.assertFalse(any('sudo' in part for call in command.call_args_list for part in call.args[0]))

    def test_installed_cat_frames_audio_and_envelopes_are_local_and_consistent(self):
        import wave
        from PIL import Image
        base = ROOT / 'system/usr/share/oguzdows/rifki'
        for frame in ('idle', 'blink', 'talk', 'talk-blink'):
            with Image.open(base / (frame + '.png')) as image:
                self.assertEqual(image.size, (384, 384))
        envelope = json.loads((base / 'envelopes.json').read_text())
        for clip in ('hello', 'disk', 'working', 'success', 'failure', 'help'):
            with wave.open(str(base / (clip + '.wav'))) as audio:
                self.assertEqual(audio.getnchannels(), 1)
                self.assertEqual(audio.getsampwidth(), 2)
                self.assertAlmostEqual(audio.getnframes() / audio.getframerate(), envelope[clip]['duration'])
                self.assertLess(abs(len(envelope[clip]['levels']) - envelope[clip]['duration'] * 20), 1.1)


if __name__ == '__main__':
    unittest.main()

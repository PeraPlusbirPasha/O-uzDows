import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from support import ROOT, load

release = load('pc_release_assets_test', 'scripts/release-assets.py')
REVISION = 'a' * 40
REPOSITORY = 'owner/project'
BRANCH = 'arena/test'


class ReleaseAssetsTests(unittest.TestCase):
    def fixture(self, root):
        inputs = root / 'input'
        for arch in release.ARCHES:
            directory = inputs / arch
            directory.mkdir(parents=True)
            name = f'OguzDows-{arch}.iso'
            image = b'unchanged ISO bytes ' + arch.encode()
            (directory / name).write_bytes(image)
            (directory / (name + '.sha256')).write_text(hashlib.sha256(image).hexdigest() + '  ' + name + '\n')
            proof = inputs / 'evidence' / ('OguzDows-ISO-hedef-test-' + arch)
            proof.mkdir(parents=True)
            result = {'arch': arch, 'source_revision': REVISION, 'build': {'source_dirty': None},
                      'modes': ['bios', 'efi'] if arch == 'amd64' else ['bios']}
            (proof / 'target-os-result.json').write_text(json.dumps(result))
            sample = {'used_bytes': 450_000_000, 'graphical_xfce': True,
                      'desktop_processes': sorted(release.DESKTOP), 'known_foreground_or_package_work': []}
            memory = {'build': {'source_revision': REVISION, 'arch': arch}, 'valid_idle_measurement': True,
                      'target_met': True, 'invalid_reasons': [], 'settled_seconds': 120,
                      'sample_interval_seconds': 5, 'sample_count': 6, 'max_used_bytes': 450_000_000,
                      'samples': [sample] * 6}
            (proof / 'desktop-idle.json').write_text(json.dumps(memory))
        return inputs

    def prepare(self, root):
        return release.prepare(root / 'input', root / 'output', repository=REPOSITORY, run_id=123,
                               release_id=456, revision=REVISION, publisher_revision='b' * 40, tag='v1.0.0')

    def test_same_bytes_checksums_and_raw_memory_are_preserved_with_source_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = self.fixture(root)
            files = self.prepare(root)
            self.assertEqual(len(files), 8)
            for arch in release.ARCHES:
                name = f'OguzDows-{arch}.iso'
                self.assertEqual((root / 'output' / name).read_bytes(), (inputs / arch / name).read_bytes())
                self.assertEqual(files[name]['sha256'], release.sha256(inputs / arch / name))
                self.assertEqual((root / 'output' / f'desktop-idle-{arch}.json').read_bytes(),
                                 (inputs / 'evidence' / ('OguzDows-ISO-hedef-test-' + arch) / 'desktop-idle.json').read_bytes())
            manifest = json.loads((root / 'output/release-manifest.json').read_text())
            self.assertFalse(manifest['iso_rebuilt'])
            self.assertEqual(manifest['source_revision'], REVISION)
            self.assertEqual(manifest['publisher_revision'], 'b' * 40)
            self.assertEqual(manifest['release_id'], 456)
            self.assertIsNone(manifest['target_os']['amd64']['build']['source_dirty'])
            self.assertNotIn('release-manifest.json', manifest['files'])  # Kendi hash'ini döngüsel hesaplamaz.
            checksums = (root / 'output/SHA256SUMS').read_text().splitlines()
            self.assertEqual(len(checksums), 2)
            self.assertTrue(all(len(line.split()[0]) == 64 for line in checksums))

    def test_mismatch_malformed_or_path_traversing_checksum_is_rejected(self):
        for text in ('0' * 64 + '  OguzDows-amd64.iso\n', 'broken', 'a' * 64 + '  ../OguzDows-amd64.iso\n'):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                inputs = self.fixture(root)
                (inputs / 'amd64/OguzDows-amd64.iso.sha256').write_text(text)
                with self.assertRaisesRegex(ValueError, 'SHA-256'):
                    self.prepare(root)

    def test_failed_wrong_source_or_incomplete_firmware_evidence_is_rejected(self):
        for change in ({'source_revision': 'b' * 40}, {'arch': 'i386'}, {'error': 'boot failed'},
                       {'modes': ['bios']}, {'build': {'source_dirty': True}}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                inputs = self.fixture(root)
                path = inputs / 'evidence/OguzDows-ISO-hedef-test-amd64/target-os-result.json'
                path.write_text(json.dumps({**json.loads(path.read_text()), **change}))
                with self.assertRaisesRegex(ValueError, 'açılış kanıtı'):
                    self.prepare(root)

    def test_idle_evidence_must_be_actual_full_desktop_settled_and_under_target(self):
        cases = ({'valid_idle_measurement': False}, {'target_met': False}, {'settled_seconds': 10},
                 {'sample_count': 5}, {'sample_interval_seconds': 1}, {'max_used_bytes': 1},
                 {'build': {'source_revision': 'b' * 40, 'arch': 'amd64'}}, {'samples': []})
        for change in cases:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                inputs = self.fixture(root)
                path = inputs / 'evidence/OguzDows-ISO-hedef-test-amd64/desktop-idle.json'
                data = json.loads(path.read_text())
                data.update(change)
                path.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError, 'RAM kanıtı'):
                    self.prepare(root)
        for field, value in (('graphical_xfce', False), ('desktop_processes', []),
                             ('known_foreground_or_package_work', ['gnome-software']), ('used_bytes', 650_000_000)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                inputs = self.fixture(root)
                path = inputs / 'evidence/OguzDows-ISO-hedef-test-amd64/desktop-idle.json'
                data = json.loads(path.read_text())
                for sample in data['samples']:
                    sample[field] = value
                data['max_used_bytes'] = max(sample['used_bytes'] for sample in data['samples'])
                path.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError, 'RAM kanıtı'):
                    self.prepare(root)

    def test_symlink_large_file_and_existing_output_are_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = self.fixture(root)
            image = inputs / 'amd64/OguzDows-amd64.iso'
            image.unlink()
            image.symlink_to(inputs / 'i386/OguzDows-i386.iso')
            with self.assertRaisesRegex(ValueError, 'Normal'):
                self.prepare(root)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = self.fixture(root)
            with (inputs / 'amd64/OguzDows-amd64.iso').open('r+b') as stream:
                stream.truncate(2 * 1024**3)  # Seyrek test dosyası; büyük veri yazmaz/hash'lemez.
            with self.assertRaisesRegex(ValueError, 'boyutunu'):
                self.prepare(root)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / 'output').mkdir()
            sentinel = root / 'output/keep'
            sentinel.write_text('keep')
            with self.assertRaises(FileExistsError):
                self.prepare(root)
            self.assertEqual(sentinel.read_text(), 'keep')

    def test_only_successful_same_repo_branch_and_workflow_run_is_accepted(self):
        run = {'id': 123, 'status': 'completed', 'conclusion': 'success', 'repository': {'full_name': REPOSITORY},
               'head_repository': {'full_name': REPOSITORY}, 'head_branch': BRANCH,
               'path': '.github/workflows/main.yml', 'head_sha': REVISION}
        self.assertEqual(release.validate_run(run, 123, REPOSITORY, BRANCH), REVISION)
        for change in ({'id': 124}, {'conclusion': 'failure'}, {'status': 'in_progress'},
                       {'head_repository': {'full_name': 'fork/project'}}, {'head_branch': 'main'},
                       {'path': '.github/workflows/other.yml'}, {'head_sha': 'not-a-commit'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                release.validate_run({**run, **change}, 123, REPOSITORY, BRANCH)

    def test_upload_only_targets_the_expected_existing_draft_and_unchanged_runtime(self):
        draft = {'id': 456, 'draft': True, 'tag_name': 'v1.0.0', 'target_commitish': REVISION, 'body': 'notes\n'}
        release.validate_draft(draft, 456, 'v1.0.0', REVISION, 'notes')
        for change in ({'id': 457}, {'draft': False}, {'tag_name': 'v2.0.0'},
                       {'target_commitish': 'main'}, {'body': 'other notes'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                release.validate_draft({**draft, **change}, 456, 'v1.0.0', REVISION, 'notes')
        release.validate_changes(['docs/releases/v1.0.0.md', 'tests/test_release_assets.py',
                                  '.github/workflows/main.yml', 'scripts/release-assets.py', 'README.md', 'build.yml'])
        for path in ('system/etc/lsb-release', 'packages/pc.list', 'build.sh', 'hooks/0270-maintenance.hook.chroot',
                     'scripts/configure.py'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'yeni ISO'):
                release.validate_changes([path])

    def test_remote_upload_verification_never_clobbers_unknown_or_mismatched_assets(self):
        expected = {'iso': {'size': 123, 'sha256': 'a' * 64}, 'sums': {'size': 10, 'sha256': 'b' * 64}}
        uploaded = {'name': 'iso', 'size': 123, 'state': 'uploaded', 'digest': 'sha256:' + 'a' * 64}
        self.assertEqual(release.check_remote({'assets': [uploaded]}, expected, complete=False), {'sums'})
        with self.assertRaises(ValueError):
            release.check_remote({'assets': [uploaded]}, expected, complete=True)
        for change in ({'name': 'unrelated'}, {'size': 124}, {'state': 'starter'}, {'digest': None},
                       {'digest': 'sha256:' + 'c' * 64}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                release.check_remote({'assets': [{**uploaded, **change}]}, expected, complete=False)
        with self.assertRaises(ValueError):
            release.check_remote({'assets': [uploaded, copy.deepcopy(uploaded)]}, expected, complete=False)

    def test_release_job_has_separate_write_permission_never_builds_or_publishes_automatically(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/main.yml').read_text())
        job = workflow['jobs']['release']
        self.assertIn("target == 'pc-release'", job['if'])
        self.assertEqual(job['permissions'], {'contents': 'write', 'actions': 'read'})
        self.assertEqual(workflow['permissions']['contents'], 'read')
        self.assertFalse(job['concurrency']['cancel-in-progress'])
        self.assertFalse(workflow['concurrency']['cancel-in-progress'])
        for name in ('verify', 'installed-boot', 'build'):
            self.assertIn("target != 'pc-release'", workflow['jobs'][name]['if'])
        self.assertNotIn('bash build.sh', str(job))
        self.assertNotIn('container', job)
        source = (ROOT / 'scripts/release-assets.py').read_text()
        self.assertNotIn("command('gh', 'release', 'edit'", source)
        self.assertNotIn("command('gh', 'release', 'create'", source)
        self.assertNotIn("command('gh', 'run', 'cancel'", source)
        self.assertNotIn("'--clobber'", source)
        self.assertEqual((ROOT / 'build.yml').read_text(), (ROOT / '.github/workflows/main.yml').read_text())


if __name__ == '__main__':
    unittest.main()

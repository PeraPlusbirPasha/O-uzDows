#!/usr/bin/env python3
"""Başarılı PC artefaktlarını doğrula ve mevcut release TASLAĞINA aktar.

ISO derlemez/değiştirmez; işi iptal etmez, etiket oluşturmaz, yayını herkese
AÇMAZ. Son yayımlama, doğrulama sonrası ayrıca gh release edit ile yapılır.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ARCHES = ('amd64', 'i386')
DESKTOP = {'xfce4-session', 'xfwm4', 'xfce4-panel', 'xfdesktop'}
# İlk v1.0.0 yayını korunur; sonraki ana yayınlar v2.0, v3.0 biçimindedir.
TAG = re.compile(r'v[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:-[a-z0-9]+(?:[.-][a-z0-9]+)*)?')


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def regular(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise ValueError('Normal, dolu yayın dosyası gerekli: ' + str(path))
    return path


def validate_run(run, run_id, repository, branch):
    if (run.get('id') != run_id or run.get('status') != 'completed' or run.get('conclusion') != 'success'
            or run.get('repository', {}).get('full_name') != repository
            or run.get('head_repository', {}).get('full_name') != repository
            or run.get('head_branch') != branch or run.get('path') != '.github/workflows/main.yml'
            or not re.fullmatch(r'[0-9a-f]{40}', run.get('head_sha', ''))):
        raise ValueError('Kaynak, aynı depo/dalın başarıyla tamamlanmış PC çalışması olmalı.')
    return run['head_sha']


def validate_draft(release, release_id, tag, revision, notes):
    if (release.get('id') != release_id or release.get('draft') is not True
            or release.get('tag_name') != tag or release.get('target_commitish') != revision
            or release.get('body', '').strip() != notes.strip()):
        raise ValueError('Release kimliği, taslak durumu, kaynak commit veya sürüm notları eşleşmiyor.')


def validate_changes(paths):
    # Eski artefaktları yeni sistem kodu gibi sunma. Sonraki farklar yalnızca
    # belge, test, CI veya bu aktarma aracı olabilir; ISO içeriği aynı kalmalı.
    for path in paths:
        if not (path.startswith(('.github/', 'docs/', 'tests/'))
                or path in ('README.md', 'build.yml', 'scripts/release-assets.py')):
            raise ValueError('ISO sonrasında ürün/derleme içeriği değişmiş; yeni ISO gerekir: ' + path)


def inventory(directory):
    result = {}
    for path in sorted(directory.iterdir()):
        regular(path)
        result[path.name] = {'size': path.stat().st_size, 'sha256': sha256(path)}
    return result


def prepare(inputs, output, *, repository, run_id, release_id, revision, publisher_revision, tag):
    output.mkdir(parents=True, exist_ok=False)
    reports, checksums = {}, []
    for arch in ARCHES:
        name = f'OguzDows-{arch}.iso'
        image = regular(inputs / arch / name)
        checksum = regular(inputs / arch / (name + '.sha256'))
        if image.stat().st_size >= 2 * 1024**3 or checksum.stat().st_size > 256:
            raise ValueError('ISO, GitHub dosya sınırını veya checksum beklenen boyutunu aştı.')
        match = re.fullmatch(r'([0-9a-f]{64})  ' + re.escape(name) + r'\n?', checksum.read_text())
        digest = sha256(image)
        if match is None or match[1] != digest:
            raise ValueError('ISO SHA-256 doğrulaması başarısız: ' + name)
        proof = inputs / 'evidence' / ('OguzDows-ISO-hedef-test-' + arch)
        results = list(proof.rglob('target-os-result.json'))
        measurements = list(proof.rglob('desktop-idle.json'))
        if len(results) != 1 or len(measurements) != 1:
            raise ValueError('Her mimari için tek hedef OS ve RAM raporu gerekli.')
        result = json.loads(regular(results[0]).read_text())
        measurement = json.loads(regular(measurements[0]).read_text())
        modes = ['bios', 'efi'] if arch == 'amd64' else ['bios']
        if (result.get('arch') != arch or result.get('source_revision') != revision or result.get('error')
                or result.get('modes') != modes or result.get('build', {}).get('source_dirty') is True):
            raise ValueError('ISO hedef açılış kanıtı kaynak/mimariyle eşleşmiyor: ' + arch)
        build, samples = measurement.get('build', {}), measurement.get('samples', [])
        if (build.get('source_revision') != revision or build.get('arch') != arch
                or measurement.get('valid_idle_measurement') is not True
                or measurement.get('target_met') is not True or measurement.get('invalid_reasons')
                or measurement.get('settled_seconds', 0) < 120 or measurement.get('sample_interval_seconds', 0) < 5
                or len(samples) < 6 or measurement.get('sample_count') != len(samples)
                or not all(item.get('graphical_xfce') is True and DESKTOP <= set(item.get('desktop_processes', []))
                           and not item.get('known_foreground_or_package_work') for item in samples)
                or max(item['used_bytes'] for item in samples) != measurement.get('max_used_bytes')
                or measurement.get('max_used_bytes', 600_000_001) > 600_000_000):
            raise ValueError('Gerçek, kaynakla eşleşen ve hedefi geçen tam Xfce RAM kanıtı gerekli: ' + arch)
        os.link(image, output / name)  # Yalnızca aynı baytlar; ISO yeniden paketlenmez.
        shutil.copyfile(checksum, output / checksum.name)
        shutil.copyfile(measurements[0], output / f'desktop-idle-{arch}.json')
        checksums.append(digest + '  ' + name + '\n')
        reports[arch] = result
    (output / 'SHA256SUMS').write_text(''.join(checksums))
    manifest = {'format': 1, 'repository': repository, 'release_id': release_id, 'tag': tag,
                'source_run_id': run_id, 'source_run_url': f'https://github.com/{repository}/actions/runs/{run_id}',
                'source_revision': revision, 'publisher_revision': publisher_revision,
                'iso_rebuilt': False, 'target_os': reports, 'files': inventory(output)}
    (output / 'release-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return inventory(output)


def check_remote(release, expected, *, complete):
    assets = release.get('assets', [])
    actual = {item['name']: item for item in assets}
    if len(actual) != len(assets) or set(actual) - set(expected) or complete and set(actual) != set(expected):
        raise ValueError('Release dosya listesi beklenen listeyle eşleşmiyor; hiçbir dosya silinmedi/ezilmedi.')
    for name, item in actual.items():
        known = expected[name]
        if (item.get('state') != 'uploaded' or item.get('size') != known['size']
                or item.get('digest') != 'sha256:' + known['sha256']):
            raise ValueError('Sunucudaki dosyanın durumu/boyutu/SHA-256 değeri eşleşmiyor: ' + name)
    return set(expected) - set(actual)


def command(*args):
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True).stdout
    except subprocess.CalledProcessError as error:
        # Asıl ağ/yetki hatası yalnızca genel çıkış kodunun arkasında kalmasın.
        print((error.stderr or '')[-2000:], file=sys.stderr, flush=True)
        raise


def api(path):
    return json.loads(command('gh', 'api', path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=int, required=True)
    parser.add_argument('--release-id', type=int, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--work', type=Path, default=Path('.cache/release'))
    args = parser.parse_args()
    repository, branch = os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_REF_NAME']
    if (args.run <= 0 or args.release_id <= 0 or not TAG.fullmatch(args.tag)
            or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository)):
        parser.error('Yayın etiketi / çalışma / release kimliği geçersiz.')
    notes = (Path('docs/releases') / (args.tag + '.md')).read_text()
    revision = validate_run(api(f'repos/{repository}/actions/runs/{args.run}'), args.run, repository, branch)
    if revision not in notes or f'actions/runs/{args.run}' not in notes:
        raise ValueError('Sürüm notlarında doğru kaynak commit ve başarılı çalışma bağlantısı gerekli.')
    command('git', 'merge-base', '--is-ancestor', revision, 'HEAD')
    validate_changes(command('git', 'diff', '--name-only', revision, 'HEAD').splitlines())
    endpoint = f'repos/{repository}/releases/{args.release_id}'
    release = api(endpoint)
    validate_draft(release, args.release_id, args.tag, revision, notes)
    args.work.mkdir(parents=True, exist_ok=False)
    inputs, output = args.work / 'input', args.work / 'upload'
    for arch in ARCHES:
        print('Başarılı çalışmadan ISO alınıyor: ' + arch, flush=True)
        command('gh', 'run', 'download', str(args.run), '--repo', repository,
                '--name', 'OguzDows-' + arch, '--dir', str(inputs / arch))
    command('gh', 'run', 'download', str(args.run), '--repo', repository,
            '--pattern', 'OguzDows-ISO-hedef-test-*', '--dir', str(inputs / 'evidence'))
    expected = prepare(inputs, output, repository=repository, run_id=args.run, release_id=args.release_id,
                       revision=revision, publisher_revision=command('git', 'rev-parse', 'HEAD').strip(), tag=args.tag)
    # Kesilen aktarmada yalnızca aynı hash/boyuta sahip tamamlanmış dosyalar
    # korunur. --clobber, dosya silme, yeni release veya otomatik yayın yoktur.
    release = api(endpoint)
    validate_draft(release, args.release_id, args.tag, revision, notes)
    missing = check_remote(release, expected, complete=False)
    for name in sorted(missing):
        print('Release taslağına yükleniyor: ' + name, flush=True)
        command('gh', 'release', 'upload', args.tag, str(output / name), '--repo', repository)
    release = api(endpoint)
    validate_draft(release, args.release_id, args.tag, revision, notes)
    check_remote(release, expected, complete=True)
    summary = {'release_id': args.release_id, 'tag': args.tag, 'draft': True,
               'source_revision': revision, 'files': expected}
    print('::notice title=Doğrulanmış release taslağı::' + json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

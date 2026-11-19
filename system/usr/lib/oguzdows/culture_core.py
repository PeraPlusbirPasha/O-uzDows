"""Çevrimdışı Türkçe yardımcıları. Kullanıcı seçmeden dosya okunmaz/gönderilmez."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tarfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

PRIVATE = frozenset(('.ssh', '.gnupg', '.cache', '.git', '.mozilla', '.env', 'keyrings'))
LIMIT = 2 * 1024**3


def turkish_upper(text):
    return text.translate(str.maketrans({'i': 'İ', 'ı': 'I'})).upper()


def turkish_lower(text):
    return text.translate(str.maketrans({'I': 'ı', 'İ': 'i'})).lower()


def safe_source(path, home=None):
    home = (Path.home() if home is None else home).resolve()
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Sembolik bağlantılar paylaşılmaz / yedeklenmez.')
    resolved = path.resolve(strict=True)
    if (not resolved.is_relative_to(home) or PRIVATE.intersection(resolved.relative_to(home).parts)
            or any(part.startswith('.') for part in resolved.relative_to(home).parts)):
        raise ValueError('Yalnızca kendi ev dizininizdeki görünür konumları seçin; gizli / bilinen anahtar dizinleri dışlanır.')
    return resolved


def open_regular(path, home=None):
    # Her bileşeni dir_fd + NOFOLLOW ile aç: tarama ile okuma arasında bir
    # bağlantı değiştirilirse gizli / dış dosya takip edilmez. Root gerektirmez.
    home = (Path.home() if home is None else Path(home)).resolve()
    relative = Path(path).relative_to(home)
    directory = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    descriptor = None
    try:
        for part in relative.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Dosya türü işlem sırasında değişti; normal dosya değil.')
        stream = os.fdopen(descriptor, 'rb')
        descriptor = None
        return stream, info
    finally:
        os.close(directory)
        if descriptor is not None:
            os.close(descriptor)


def archive_name(path):
    # ZIP'i başka işletim sistemine taşıyınca ters eğik çizgi / ADS / satır
    # sonu dosya adı kaçışına dönüşmesin. Arşiv otomatik açılmaz.
    if any(any(ord(char) < 32 or char in '\\:' for char in part) or part in ('.', '..') for part in Path(path).parts):
        raise ValueError('Taşınabilir arşiv için dosya adlarında kontrol karakteri, ters eğik çizgi veya iki nokta kullanmayın.')
    return Path(path).as_posix()


def collect(source, home=None):
    source = safe_source(source, home)
    if not source.is_dir():
        raise ValueError('Yedeklemek için bir klasör seçin.')
    files = []
    total = 0
    for parent, directories, names in os.walk(source, followlinks=False):
        directories[:] = sorted(name for name in directories if not name.startswith('.') and name not in PRIVATE
                                and not (Path(parent) / name).is_symlink() and not os.path.ismount(Path(parent) / name))
        for name in sorted(names):
            path = Path(parent) / name
            if name.startswith('.') or name in PRIVATE or path.is_symlink():
                continue
            info = path.stat()
            if not stat.S_ISREG(info.st_mode):
                continue
            total += info.st_size
            if total > LIMIT or len(files) >= 100000:
                raise ValueError('Tek işlem sınırı 2 GiB / 100.000 dosyadır; daha küçük klasörler seçin.')
            files.append(path)
    if not files:
        raise ValueError('Yedeklenecek görünür normal dosya yok. Gizli / anahtar dosyaları dışlanır.')
    return source, files, total


def new_archive(destination, prefix, suffix):
    destination = Path(destination).resolve(strict=True)
    if not destination.is_dir():
        raise ValueError('Geçerli bir hedef klasör seçin.')
    path = destination / (prefix + '-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8] + suffix)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    return path, fd


def checksum(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    sidecar = path.with_name(path.name + '.sha256')
    fd = os.open(sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(digest.hexdigest() + '  ' + path.name + '\n')
    return sidecar


def heybe(source, destination, home=None):
    source, files, total = collect(source, home)
    target = Path(destination).resolve(strict=True)
    if target.is_relative_to(source):
        raise ValueError('Yedek hedefi kaynak klasörün dışında olmalı; aynı diskteki kopya disk arızasına karşı korumaz.')
    if shutil.disk_usage(target).free < total + 32 * 1024**2:
        raise ValueError('Hedefte güvenli yedek için yeterli boş alan yok.')
    path, descriptor = new_archive(target, 'OguzDows-Heybe', '.tar.gz')
    try:
        with os.fdopen(descriptor, 'wb') as stream, tarfile.open(fileobj=stream, mode='w:gz', compresslevel=1) as archive:
            current_total = 0
            for file in files:
                original, info = open_regular(file, home)
                with original:
                    current_total += info.st_size
                    if current_total > LIMIT:
                        raise ValueError('Kaynaklar işlem sırasında büyüdü; yedek sınırı aşıldı.')
                    member = tarfile.TarInfo(archive_name(Path(source.name) / file.relative_to(source)))
                    member.size, member.mode, member.mtime = info.st_size, 0o600, int(info.st_mtime)
                    archive.addfile(member, original)
        checksum(path)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def imece(files, destination, home=None):
    if not files or len(files) > 100:
        raise ValueError('1–100 dosya seçin.')
    sources = [safe_source(path, home) for path in files]
    if any(not path.is_file() for path in sources):
        raise ValueError('Yalnızca normal dosyalar paketlenebilir.')
    if sum(path.stat().st_size for path in sources) > LIMIT:
        raise ValueError('Paylaşım paketi sınırı 2 GiB.')
    if len({path.name for path in sources}) != len(sources):
        raise ValueError('Aynı adlı dosyaları yeniden adlandırın; dosyalar birbirinin üstüne yazılmadı.')
    path, descriptor = new_archive(destination, 'OguzDows-Imece', '.zip')
    manifest = []
    try:
        with os.fdopen(descriptor, 'wb') as stream, zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
            total = 0
            for source in sources:
                original, _info = open_regular(source, home)
                with original:
                    digest = hashlib.sha256()
                    entry = zipfile.ZipInfo(archive_name(Path('Dosyalar') / source.name))
                    entry.external_attr = 0o100644 << 16
                    with archive.open(entry, 'w', force_zip64=True) as target:
                        for chunk in iter(lambda: original.read(1024 * 1024), b''):
                            total += len(chunk)
                            if total > LIMIT:
                                raise ValueError('Dosyalar işlem sırasında büyüdü; paket sınırı aşıldı.')
                            digest.update(chunk)
                            target.write(chunk)
                    manifest.append({'name': source.name, 'sha256': digest.hexdigest()})
            archive.writestr('BASLANGIC.txt', 'İmece · Birlikte üretelim.\nBu paket cihazda oluşturuldu; kendiliğinden hiçbir yere gönderilmedi.\nDosyaları açmadan önce içeriğini ve göndereni kontrol edin.\n')
            archive.writestr('Dogrulama.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        checksum(path)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path

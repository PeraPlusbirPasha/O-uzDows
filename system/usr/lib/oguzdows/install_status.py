"""Kurulum sonucu protokolü. Çıkış kodu sıfır olması tek başına başarı değildir."""
from __future__ import annotations

import json
import os
import re
import stat
import tempfile
import time
import uuid
from pathlib import Path

RUN = Path('/run/oguzdows-installer')
PREFIX = 'OGUZDOWS_RESULT_JSON='
OUTCOMES = {'preparing', 'ready', 'running', 'success', 'failed', 'incomplete', 'cancelled', 'unknown'}
STAGES = {'preparing', 'ready', 'partition', 'copying', 'bootloader', 'complete'}


def valid_session(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{32}', value) is not None


def read_status(directory=RUN):
    try:
        path = directory / 'status.json'
        with path.open('r', encoding='utf-8') as stream:
            text = stream.read(16385)
        if len(text) > 16384:
            return {}
        data = json.loads(text)
        if not isinstance(data, dict) or data.get('version') != 1 or not valid_session(data.get('session')) or data.get('outcome') not in OUTCOMES:
            return {}
        return data
    except (OSError, ValueError, TypeError):
        return {}


def atomic_json(path, data):
    directory = path.parent
    directory.mkdir(mode=0o755, parents=True, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise OSError('Kurulum durum dizini güvenli değil.')
    os.chmod(directory, 0o755)
    fd, temporary = tempfile.mkstemp(prefix='.status-', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fchmod(stream.fileno(), 0o644)
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def begin(directory=RUN):
    data = {'version': 1, 'session': uuid.uuid4().hex, 'outcome': 'preparing',
            'stage': 'preparing', 'started': False, 'complete': False, 'updated': time.time()}
    atomic_json(directory / 'status.json', data)
    return data


def stage(session, name, directory=RUN, firmware='', target=''):
    if name not in STAGES or not valid_session(session):
        raise ValueError('Kurulum aşaması veya oturum kimliği geçersiz.')
    data = read_status(directory)
    if data.get('session') != session:
        raise ValueError('Kurulum oturumu artık güncel değil.')
    if data.get('complete'):
        return data
    data.update(stage=name, updated=time.time())
    if name not in ('preparing', 'ready'):
        data.update(started=True, outcome='running')
    else:
        data['outcome'] = name
    if firmware in ('efi', 'bios'):
        data['firmware'] = firmware
    if isinstance(target, str) and re.fullmatch(r'/dev/[A-Za-z0-9_./:+-]+', target):
        data['target'] = target[:256]
    if name == 'complete':
        data.update(complete=True, outcome='success')
        # Bu dosyayı yalnızca umount'tan SONRA çalışan son Calamares işi üretir.
        atomic_json(directory / ('complete-' + session + '.json'), {'session': session, 'complete': True})
    atomic_json(directory / 'status.json', data)
    return data


def finish(session, code, directory=RUN):
    data = read_status(directory)
    if data.get('session') != session:
        raise ValueError('Kurulum sonucu başka bir oturuma ait.')
    try:
        proof = json.loads((directory / ('complete-' + session + '.json')).read_text())
    except (OSError, ValueError):
        proof = {}
    complete = (proof == {'session': session, 'complete': True}
                and data.get('complete') is True and data.get('stage') == 'complete')
    outcome = 'success' if complete else ('failed' if code else ('incomplete' if data['started'] else 'cancelled'))
    data.update(outcome=outcome, complete=complete, exit_code=code, updated=time.time())
    atomic_json(directory / 'status.json', data)
    return data


def from_output(code, output):
    """pkexec çıktısındaki yeni oturuma ait kanıtlı sonucu oku; eski duruma bakma."""
    for line in output.splitlines():
        if line.startswith(PREFIX) and len(line) <= 16384:
            try:
                data = json.loads(line[len(PREFIX):])
                if isinstance(data, dict) and data.get('version') == 1 and valid_session(data.get('session')) and data.get('outcome') in OUTCOMES:
                    if data['outcome'] != 'success' or data.get('complete') is True:
                        return data
            except (ValueError, TypeError):
                pass
    return {'outcome': 'cancelled' if code in (10, 126, 127) else ('failed' if code else 'unknown'), 'complete': False}


def description(data):
    outcome = data.get('outcome')
    if outcome == 'success' and data.get('complete') is True:
        title = 'OğuzDows başarıyla kuruldu.'
        detail = 'Kurulum işleri, önyükleyici denetimi ve bölüm ayırma tamamlandı. Hâlâ canlı USB oturumundasın. Diskten ilk açılış ayrıca kontrol edilmelidir.'
        if data.get('firmware'):
            detail += '\nAçılış türü: ' + ('UEFI' if data['firmware'] == 'efi' else 'BIOS')
        if data.get('target'):
            detail += '\nÖnyükleyici hedefi: ' + data['target']
        return title, detail
    if outcome == 'cancelled':
        return 'Kurulum başlatılmadı / iptal edildi.', 'Başarılı disk kurulumu kaydı oluşmadı. Yetkilendirme veya kurucu kapatılmış olabilir. Canlı USB oturumundasın.'
    if outcome == 'unknown':
        return 'Kurulumun tamamlandığı doğrulanamadı.', 'Kurucunun kapanması başarı kanıtı değildir. Başarı kaydı bulunamadı; yeniden başlatmadan önce günlüğü incele.'
    return 'Kurulum tamamlanamadı.', 'İşlem hata ile kapandı veya yarım kaldı. Bazı dosyalar diske kopyalanmış olabilir. Ayrıntıları incele; diski yeniden biçimlendirmek gerektiğini varsayma.'

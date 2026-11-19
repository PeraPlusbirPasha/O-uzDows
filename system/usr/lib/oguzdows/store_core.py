"""Sabit ve imzalı Flathub kullanıcı kaynağı sözleşmesi; içe aktarma ağ işlemi yapmaz."""
import subprocess

FLATHUB_DESCRIPTOR = 'https://dl.flathub.org/repo/flathub.flatpakrepo'
FLATHUB_URL = 'https://dl.flathub.org/repo/'


def run(command):
    result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, errors='replace', timeout=180, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr[-2500:] or 'Mağaza işlemi tamamlanamadı.')
    return result.stdout.strip()


def official_remote(listing):
    for line in listing.splitlines():
        columns = line.split('\t')
        if columns[0] == 'flathub':
            if len(columns) < 3 or columns[1].rstrip('/') != FLATHUB_URL.rstrip('/') or 'no-gpg-verify' in columns[2]:
                raise ValueError('Flathub adıyla farklı / imzasız bir kaynak bulunuyor. Otomatik değiştirilmedi; Yazılım Depoları bölümünü kontrol edin.')
            return True
    return False


def setup_flathub(execute=run):
    if execute(['/usr/bin/flatpak', '--default-arch']) != 'x86_64':
        raise ValueError('Bu mimaride Flathub kapsamı doğrulanmadı. Sistem (APT) uygulamaları mağazada kullanılabilir.')
    command = ['/usr/bin/flatpak', '--user', 'remotes', '--columns=name,url,options']
    if not official_remote(execute(command)):
        execute(['/usr/bin/flatpak', '--user', 'remote-add', '--if-not-exists', '--from', 'flathub', FLATHUB_DESCRIPTOR])
        if not official_remote(execute(command)):
            raise ValueError('Flathub kaynağı doğrulanamadı; imza denetimi kapatılmadı.')

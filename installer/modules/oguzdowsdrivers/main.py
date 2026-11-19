"""İsteğe bağlı Wi-Fi aktarımı canlı /sys'de denetlenir, hedefte sadece paket kurulur."""
import os
import sys
from pathlib import Path

import libcalamares

sys.path.insert(0, '/usr/lib/oguzdows')


def pretty_name():
    return 'Onaylanan ek sürücüler aktarılıyor'


def run():
    import driver_transfer
    import install_status
    import offline
    root = Path(libcalamares.globalstorage.value('rootMountPoint') or '/')
    try:
        actions = libcalamares.job.configuration.get('actions', [])
        if not isinstance(actions, list):
            raise ValueError('Sürücü seçim listesi geçersiz.')
        results = driver_transfer.transfer(root, actions, offline.selected(), libcalamares.utils.target_env_call)
        driver_transfer.save_results(root, results)
        install_status.driver_results(os.environ.get('OGUZDOWS_INSTALL_SESSION', ''), results)
        for item in results:
            libcalamares.utils.debug('OğuzDows ek sürücü: ' + item['action'] + ': ' + item['status'] + ' — ' + item['message'])
    except (OSError, ValueError) as error:
        # Durum / hedef güvenliği doğrulanamıyorsa yazmaya devam etme.
        return ('Ek sürücü aktarım bilgisi kaydedilemedi', str(error))
    return None

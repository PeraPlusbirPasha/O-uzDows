"""Canlı oturumdaki rehbere yalnızca gerçek kurulum aşamalarını bildirir."""
import os
import sys

import libcalamares

sys.path.insert(0, '/usr/lib/oguzdows')


def pretty_name():
    return 'OğuzDows kurulum sonucu kaydediliyor'


def run():
    import install_status
    try:
        gs = libcalamares.globalstorage
        loader = gs.value('bootLoader') or {}
        target = loader.get('installPath', '')
        if gs.value('firmwareType') == 'efi':
            target = next((p.get('device', '') for p in (gs.value('partitions') or []) if p.get('mountPoint') == '/boot/efi'), '')
        install_status.stage(os.environ.get('OGUZDOWS_INSTALL_SESSION', ''),
                             libcalamares.job.configuration.get('stage'),
                             firmware=gs.value('firmwareType'), target=target)
    except (OSError, ValueError, TypeError) as error:
        return ('Kurulum sonucu kaydedilemedi', str(error))
    return None

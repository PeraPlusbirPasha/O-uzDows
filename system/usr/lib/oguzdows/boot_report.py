"""Disk açılışını tanılamak için salt-okunur, internetsiz rapor. Onarım yapmaz."""
import json
from pathlib import Path

from hardware import command_output
from install_status import read_status


def report():
    mode = 'UEFI' if Path('/sys/firmware/efi').is_dir() else 'BIOS / CSM'
    try:
        build = json.loads(Path('/usr/share/oguzdows/build-info.json').read_text())
    except (OSError, ValueError):
        build = {}
    state = read_status()
    return '\n'.join([
        'OğuzDows · Salt-okunur disk açılış raporu',
        'Bu rapor hiçbir bölüm, önyükleyici veya firmware ayarını değiştirmez.',
        'Şu anki oturumun açılış kipi: ' + mode,
        'Not: Canlı USB kipi, diskteki kurulumun kipini tek başına kanıtlamaz.',
        'Sürüm bilgisi: ' + json.dumps(build, ensure_ascii=False),
        'Son kurucu durumu: ' + json.dumps(state, ensure_ascii=False),
        '\nDiskler, boyutlar ve bölüm türleri:',
        command_output(['/usr/bin/lsblk', '-o', 'NAME,SIZE,MODEL,TYPE,FSTYPE,PTTYPE,PARTTYPE,MOUNTPOINTS']),
        '\nFotoğraftaki Reboot and Select proper Boot device hatası firmware aşamasındadır.',
        'Diskin algılanması, önyükleme sırası, BIOS/UEFI kipi ve GRUB hedefi ayrıca incelenmelidir.',
        'Bu raporla birlikte cihaz modelini ve hata fotoğrafını paylaşabilirsin.',
        'Disk adını tahmin ederek grub-install, mkfs veya bölümleme komutu çalıştırma.',
        'Hiçbir bilgi otomatik olarak gönderilmedi. Raporu kaydedip paylaşmak senin tercihin.',
    ]) + '\n'

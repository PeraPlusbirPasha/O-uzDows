"""Beş görünüm; hepsi aynı hafif Xfce. Root, ağ ve sürekli süreç yok."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

PROFILES = {
    'oguzdows': {'name': 'OğuzDows', 'description': 'Ay yıldız, koyu tonlar, üst panel.', 'position': 6, 'length': 100, 'size': 38, 'gtk': 'OguzDows', 'layout': 'O|HMC', 'wm': 'OguzDows'},
    'kde': {'name': 'KDE tarzı', 'description': 'Altta geniş görev çubuğu, koyu uygulamalar.', 'position': 10, 'length': 100, 'size': 44, 'gtk': 'Adwaita-dark', 'layout': 'O|HMC', 'wm': 'OguzDows'},
    'gnome': {'name': 'GNOME tarzı', 'description': 'Sade üst çubuk, açık uygulamalar.', 'position': 6, 'length': 100, 'size': 34, 'gtk': 'Adwaita', 'layout': 'O|C', 'wm': 'OguzDows'},
    'xfce': {'name': 'Klasik Xfce', 'description': 'İnce panel ve alışıldık hafif görünüm.', 'position': 6, 'length': 100, 'size': 30, 'gtk': 'Adwaita', 'layout': 'O|HMC', 'wm': 'Default'},
    'mac': {'name': 'Mac esintisi', 'description': 'Ortalanmış alt panel, solda pencere düğmeleri.', 'position': 10, 'length': 68, 'size': 48, 'gtk': 'Adwaita', 'layout': 'CHM|O', 'wm': 'OguzDows'},
}


def settings(identifier):
    if identifier not in PROFILES:
        raise ValueError('Bilinmeyen görünüm tarzı.')
    item = PROFILES[identifier]
    return [
        ('xfce4-panel', '/panels/panel-1/position', 'string', f"p={item['position']};x=0;y=0"),
        ('xfce4-panel', '/panels/panel-1/length', 'uint', str(item['length'])),
        ('xfce4-panel', '/panels/panel-1/size', 'uint', str(item['size'])),
        ('xfce4-panel', '/panels/panel-1/enter-opacity', 'uint', '100'),
        ('xfce4-panel', '/panels/panel-1/leave-opacity', 'uint', '100'),
        ('xsettings', '/Net/ThemeName', 'string', item['gtk']),
        ('xsettings', '/Gtk/CursorThemeName', 'string', 'OguzDowsTespih'),
        ('xsettings', '/Gtk/CursorThemeSize', 'int', '32'),
        ('xsettings', '/Gtk/EnableAnimations', 'bool', 'false'),
        ('xsettings', '/Gtk/DecorationLayout', 'string', 'close,minimize,maximize:menu' if identifier == 'mac' else ('menu:close' if identifier == 'gnome' else 'menu:minimize,maximize,close')),
        ('xfwm4', '/general/theme', 'string', item['wm']),
        ('xfwm4', '/general/button_layout', 'string', item['layout']),
        ('xfwm4', '/general/use_compositing', 'bool', 'false'),
    ]


def run(command):
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=12)


def state_directory():
    return Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'oguzdows/profiles'


def set_property(channel, path, kind, value, execute):
    base = ['xfconf-query', '-c', channel, '-p', path]
    if value is None:
        # İlk ayarda bulunmayan özellik geri dönüşte oluşturulmuş bırakılmaz.
        execute([*base, '--reset'])
    elif execute([*base, '-s', value]).returncode and execute([*base, '-n', '-t', kind, '-s', value]).returncode:
        raise RuntimeError('Xfce ayarı uygulanamadı: ' + path)


def apply(identifier, directory=None, execute=run):
    choices = settings(identifier)
    directory = state_directory() if directory is None else directory
    previous = []
    for channel, path, kind, _ in choices:
        value = execute(['xfconf-query', '-c', channel, '-p', path])
        previous.append((channel, path, kind, value.stdout.strip() if value.returncode == 0 else None))
    directory.mkdir(parents=True, exist_ok=True)
    backup = directory / 'before-first-change.json'
    if not backup.exists():
        with backup.open('x', encoding='utf-8') as stream:
            json.dump(previous, stream, ensure_ascii=False)
        backup.chmod(0o600)
    try:
        for item in choices:
            set_property(*item, execute)
    except (OSError, RuntimeError, subprocess.SubprocessError):
        for item in previous:
            try:
                set_property(*item, execute)
            except (OSError, RuntimeError, subprocess.SubprocessError):
                pass
        raise
    (directory / 'selected').write_text(identifier + '\n')


def restore(directory=None, execute=run):
    directory = state_directory() if directory is None else directory
    values = json.loads((directory / 'before-first-change.json').read_text())
    allowed = {(channel, path, kind) for channel, path, kind, _ in settings('oguzdows')}
    if not isinstance(values, list) or len(values) > len(allowed):
        raise ValueError('Görünüm yedeği geçersiz.')
    for row in values:
        if (not isinstance(row, list) or len(row) != 4 or not all(isinstance(value, str) for value in row[:3])
                or tuple(row[:3]) not in allowed or not (isinstance(row[3], str) or row[3] is None)):
            raise ValueError('Görünüm yedeği geçersiz; serbest komut çalıştırılmadı.')
    for row in values:
        set_property(*row, execute)

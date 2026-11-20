"""Beş hafif Xfce tarzı, bağımsız açık/koyu seçimi ve geri alınabilir ayarlar."""
from __future__ import annotations

import fcntl
import json
import os
import subprocess
import tempfile
from pathlib import Path

PROFILES = {
    'oguzdows': {'name': 'OğuzDows', 'description': 'XP esintili Başlat, altta görev çubuğu; özgün renkler.', 'position': 10, 'length': 100, 'size': 36, 'layout': 'O|HMC', 'appearance': 'light'},
    'kde': {'name': 'KDE tarzı', 'description': 'Altta geniş görev çubuğu, koyu uygulamalar.', 'position': 10, 'length': 100, 'size': 44, 'layout': 'O|HMC', 'appearance': 'dark'},
    'gnome': {'name': 'GNOME tarzı', 'description': 'Sade üst çubuk ve az pencere düğmesi.', 'position': 6, 'length': 100, 'size': 34, 'layout': 'O|C', 'appearance': 'light'},
    'xfce': {'name': 'Klasik Xfce', 'description': 'İnce panel ve alışıldık hafif görünüm.', 'position': 6, 'length': 100, 'size': 30, 'layout': 'O|HMC', 'appearance': 'light'},
    'mac': {'name': 'Mac esintisi', 'description': 'Ortalanmış alt panel, solda pencere düğmeleri.', 'position': 10, 'length': 68, 'size': 48, 'layout': 'CHM|O', 'appearance': 'light'},
}
APPEARANCES = {'light': 'Açık', 'dark': 'Koyu'}


def theme(identifier, appearance):
    if identifier not in PROFILES or appearance not in APPEARANCES:
        raise ValueError('Bilinmeyen görünüm veya tema.')
    if identifier == 'oguzdows':
        return 'OguzDowsXP' if appearance == 'light' else 'OguzDowsXPDark'
    return 'OguzDowsLight' if appearance == 'light' else 'OguzDows'


def settings(identifier, appearance=None):
    if identifier not in PROFILES:
        raise ValueError('Bilinmeyen görünüm tarzı.')
    item = PROFILES[identifier]
    appearance = item['appearance'] if appearance is None else appearance
    gtk = theme(identifier, appearance)
    return [
        ('xfce4-panel', '/panels/panel-1/position', 'string', f"p={item['position']};x=0;y=0"),
        ('xfce4-panel', '/panels/panel-1/length', 'uint', str(item['length'])),
        ('xfce4-panel', '/panels/panel-1/size', 'uint', str(item['size'])),
        ('xfce4-panel', '/panels/panel-1/enter-opacity', 'uint', '100'),
        ('xfce4-panel', '/panels/panel-1/leave-opacity', 'uint', '100'),
        ('xfce4-panel', '/plugins/plugin-1/button-title', 'string', 'Başlat' if identifier == 'oguzdows' else 'OğuzDows'),
        ('xfce4-panel', '/plugins/plugin-1/show-button-title', 'bool', 'true'),
        ('xfce4-panel', '/plugins/plugin-1/show-button-icon', 'bool', 'true'),
        ('xfce4-panel', '/plugins/plugin-1/view-mode', 'int', '0'),
        ('xsettings', '/Net/ThemeName', 'string', gtk),
        ('xsettings', '/Gtk/ApplicationPreferDarkTheme', 'bool', str(appearance == 'dark').lower()),
        ('xsettings', '/Gtk/CursorThemeName', 'string', 'OguzDowsTespih'),
        ('xsettings', '/Gtk/CursorThemeSize', 'int', '32'),
        ('xsettings', '/Gtk/EnableAnimations', 'bool', 'false'),
        ('xsettings', '/Gtk/DecorationLayout', 'string', 'close,minimize,maximize:menu' if identifier == 'mac' else ('menu:close' if identifier == 'gnome' else 'menu:minimize,maximize,close')),
        ('xfwm4', '/general/theme', 'string', gtk),
        ('xfwm4', '/general/button_layout', 'string', item['layout']),
        ('xfwm4', '/general/use_compositing', 'bool', 'false'),
    ]


def run(command):
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=12)


def state_directory():
    return Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'oguzdows/profiles'


def selection(directory=None):
    directory = state_directory() if directory is None else directory
    def read(name):
        try:
            return (directory / name).read_text().strip()
        except OSError:
            return ''
    identifier, appearance = read('selected'), read('appearance')
    identifier = identifier if identifier in PROFILES else 'oguzdows'
    return identifier, appearance if appearance in APPEARANCES else PROFILES[identifier]['appearance']


def atomic_text(path, text):
    descriptor, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def set_property(channel, path, kind, value, execute):
    base = ['xfconf-query', '-c', channel, '-p', path]
    if value is None:
        if execute([*base, '--reset']).returncode:
            # Reset olmamış bir ayar zaten bulunmayabilir.
            if execute(base).returncode == 0:
                raise RuntimeError('Xfce ayarı geri alınamadı: ' + path)
    elif execute([*base, '-s', value]).returncode and execute([*base, '-n', '-t', kind, '-s', value]).returncode:
        raise RuntimeError('Xfce ayarı uygulanamadı: ' + path)


def transaction(choices, directory, execute, metadata):
    directory.mkdir(parents=True, exist_ok=True)
    # İki açık karşılayıcı aynı ilk yedeği veya tema tercihini yarıştırmasın.
    with (directory / '.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('Başka bir görünüm işlemi devam ediyor.') from error
        previous = []
        # Tema ilk değişiklik olsa bile sonraki tarz değişimi için bütün dar
        # izin listesinin ilk halini sakla. Sadece değişen özellikleri uygula.
        for channel, path, kind, _ in settings('oguzdows'):
            value = execute(['xfconf-query', '-c', channel, '-p', path])
            previous.append((channel, path, kind, value.stdout.strip() if value.returncode == 0 else None))
        backup = directory / 'before-first-change.json'
        if not backup.exists():
            with backup.open('x', encoding='utf-8') as stream:
                json.dump(previous, stream, ensure_ascii=False)
            backup.chmod(0o600)
        old_metadata = {}
        for name in metadata:
            try:
                old_metadata[name] = (directory / name).read_text()
            except FileNotFoundError:
                old_metadata[name] = None
        changed = {(channel, path, kind) for channel, path, kind, _ in choices}
        try:
            for item in choices:
                set_property(*item, execute)
            for name, value in metadata.items():
                if value is None:
                    (directory / name).unlink(missing_ok=True)
                else:
                    atomic_text(directory / name, value)
        except (OSError, RuntimeError, subprocess.SubprocessError):
            for item in previous:
                if item[:3] in changed:
                    try:
                        set_property(*item, execute)
                    except (OSError, RuntimeError, subprocess.SubprocessError):
                        pass
            for name, value in old_metadata.items():
                try:
                    if value is None:
                        (directory / name).unlink(missing_ok=True)
                    else:
                        atomic_text(directory / name, value)
                except OSError:
                    pass
            raise


def apply(identifier, directory=None, execute=run, appearance=None):
    directory = state_directory() if directory is None else directory
    if appearance is None:
        try:
            selected = (directory / 'appearance').read_text().strip()
            appearance = selected if selected in APPEARANCES else None
        except OSError:
            pass
    choices = settings(identifier, appearance)
    transaction(choices, directory, execute, {'selected': identifier + '\n'})


def set_appearance(appearance, directory=None, execute=run):
    if appearance not in APPEARANCES:
        raise ValueError('Bilinmeyen açık/koyu tema seçimi.')
    directory = state_directory() if directory is None else directory
    identifier, _ = selection(directory)
    keys = {('xsettings', '/Net/ThemeName'), ('xsettings', '/Gtk/ApplicationPreferDarkTheme'),
            ('xfwm4', '/general/theme')}
    choices = [row for row in settings(identifier, appearance) if row[:2] in keys]
    # Panel konumu, boyutu, düğme düzeni ve kullanıcının imleci değişmez.
    transaction(choices, directory, execute, {'appearance': appearance + '\n'})


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
    transaction(values, directory, execute, {'selected': None, 'appearance': None})

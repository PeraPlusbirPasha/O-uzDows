"""Bütün Rıfkı metinlerini çevrimdışı seslendirir; kabuk / mikrofon / ağ yok.

Tam metni eşleşen hazır ses varsa aynı yerel ses kullanılır. Diğer bütün
metinler (değişen sonuçlar dahil) Türkçe eSpeak NG ile yerelde WAV'a çevrilir.
"""
from __future__ import annotations

import array
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path

ASSETS = Path('/usr/share/oguzdows/rifki')
MAX_TEXT = 12000


def canonical(text):
    return ' '.join(str(text).split())[:MAX_TEXT]


def text_key(text):
    return hashlib.sha256(('tr-v1\n' + canonical(text)).encode()).hexdigest()


def envelope(path):
    levels = []
    with wave.open(str(path), 'rb') as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            return []
        rate = audio.getframerate()
        while block := audio.readframes(max(1, rate // 25)):
            samples = array.array('h', block)
            if sys.byteorder != 'little':
                samples.byteswap()
            rms = (sum(v*v for v in samples) / max(1, len(samples))) ** .5
            levels.append(min(1., rms / 6500.))
    return levels


def ready_clip(text, assets=ASSETS):
    try:
        manifest = json.loads((assets / 'speech.json').read_text())
        name = manifest.get(text_key(text))
        if not isinstance(name, str) or Path(name).name != name or not name.endswith('.wav'):
            return None
        path = assets / name
        if path.is_file() and not path.is_symlink():
            return path
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


def synthesize(text, directory, engine=None):
    text = canonical(text)
    if not text:
        raise ValueError('Seslendirilecek metin boş.')
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_uid != os.getuid():
        raise OSError('Ses önbelleği güvenli değil.')
    directory.chmod(0o700)
    path = directory / (text_key(text) + '.wav')
    if path.is_file() and not path.is_symlink():
        # Yarım / bozuk WAV ses olarak oynatılmaz.
        try:
            envelope(path)
            os.utime(path, None)
            return path
        except (OSError,ValueError,EOFError,wave.Error):
            path.unlink(missing_ok=True)
    engine = engine or shutil.which('espeak-ng')
    if not engine:
        raise OSError('Türkçe eSpeak NG motoru kurulu değil.')
    fd, name = tempfile.mkstemp(prefix='.voice-', suffix='.wav', dir=directory)
    os.close(fd)
    temporary = Path(name)
    try:
        # Metin argv'ye veya shell'e verilmez; seçenek gibi başlayan metin de veridir.
        subprocess.run([engine, '-v', 'tr', '-s', '168', '-p', '43', '-w', str(temporary), '--stdin'],
                       input=text, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                       timeout=45, check=True)
        envelope(temporary)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    files = sorted((p for p in directory.glob('*.wav') if p.is_file() and not p.is_symlink()), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[48:]:
        old.unlink(missing_ok=True)
    return path


class Speaker:
    """idle ekleyicisi dışarıdan verilir; sentez GTK ana döngüsünü engellemez."""
    def __init__(self, dispatch, on_error=None, assets=ASSETS):
        self.dispatch = dispatch
        self.on_error = on_error or (lambda _: None)
        self.assets = assets
        self.process = None
        self.start = 0.
        self.levels = []
        self.last_text = ''
        self.generation = 0
        self.closed = False
        self.synthesis_lock = threading.Lock()
        self.preference = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'oguzdows/rifki.json'
        self.cache = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'oguzdows/rifki-tts'
        try:
            self.options = json.loads(self.preference.read_text())
            if not isinstance(self.options, dict):
                self.options = {}
        except (OSError, ValueError):
            self.options = {}
        self.enabled = self.options.get('speech', True) is not False

    def stop(self):
        self.generation += 1
        self.levels = []
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=.3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            self.process = None

    def speak(self, text, _clip=None):
        self.last_text = canonical(text)
        self.stop()
        if not self.enabled or self.closed or not self.last_text or os.environ.get('OGUZDOWS_TESTING') == '1':
            return
        generation, words = self.generation, self.last_text
        def prepare():
            try:
                with self.synthesis_lock:
                    if generation!=self.generation or self.closed:
                        return
                    path = ready_clip(words, self.assets) or synthesize(words, self.cache)
                    levels = envelope(path)
                self.dispatch(self.play_ready, generation, path, levels)
            except (OSError, ValueError, wave.Error, subprocess.SubprocessError) as error:
                self.dispatch(self.failed, generation, type(error).__name__)
        threading.Thread(target=prepare, name='rifki-ses', daemon=True).start()

    def play_ready(self, generation, path, levels):
        if generation != self.generation or self.closed or not self.enabled:
            return False
        player = shutil.which('paplay') or shutil.which('aplay')
        if not player:
            self.failed(generation, 'Ses oynatıcısı bulunamadı')
            return False
        try:
            self.process = subprocess.Popen([player, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.levels, self.start = levels, time.monotonic()
            process=self.process
            def finished():
                if process.wait()!=0:
                    self.dispatch(self.failed,generation,'Ses çıkışı kullanılamadı')
            threading.Thread(target=finished,name='rifki-oynatma',daemon=True).start()
        except OSError:
            self.failed(generation, 'Ses aygıtı açılamadı')
        return False

    def failed(self, generation, _detail):
        if generation == self.generation and not self.closed:
            self.on_error('Rıfkı sesi hazırlanamadı. Metin ve kurulum çalışmaya devam ediyor; ses çıkışını / Türkçe ses motorunu kontrol et.')
        return False

    def amplitude(self):
        if self.process is None or self.process.poll() is not None:
            return 0.
        index = int((time.monotonic() - self.start) * 25)
        return self.levels[index] if 0 <= index < len(self.levels) else 0.

    def save_option(self, key, value):
        self.options[key] = value
        try:
            self.preference.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix='.rifki-', dir=self.preference.parent)
            with os.fdopen(fd, 'w') as stream:
                json.dump(self.options, stream)
                stream.write('\n')
            os.replace(name, self.preference)
        except OSError:
            pass

    def set_enabled(self, value):
        self.enabled = bool(value)
        self.save_option('speech', self.enabled)
        if not self.enabled:
            self.stop()

    def close(self):
        self.closed = True
        self.stop()

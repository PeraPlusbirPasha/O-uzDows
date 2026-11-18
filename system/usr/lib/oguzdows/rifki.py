"""Foto-gerçekçi 2B Rıfkı: göz kırpma, nefes, baş hareketi ve sese bağlı ağız."""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_foreign('cairo')
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from rifki_model import reply

ASSETS = Path('/usr/share/oguzdows/rifki')
CLIPS = frozenset({'hello', 'disk', 'working', 'success', 'failure', 'help'})


class Speaker:
    def __init__(self):
        self.process = None
        self.start = 0.0
        self.clip = None
        self.preference = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'oguzdows/rifki.json'
        try:
            self.enabled = json.loads(self.preference.read_text()).get('speech', True) is not False
        except (OSError, ValueError, AttributeError):
            self.enabled = True
        try:
            self.envelopes = json.loads((ASSETS / 'envelopes.json').read_text())
        except (OSError, ValueError):
            self.envelopes = {}

    def stop(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=.4)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            self.process = None
        self.clip = None

    def play(self, name):
        self.stop()
        if not self.enabled or name not in CLIPS or os.environ.get('OGUZDOWS_TESTING') == '1':
            return
        player = shutil.which('paplay') or shutil.which('aplay')
        path = ASSETS / (name + '.wav')
        if not player or not path.is_file():
            return
        try:
            self.process = subprocess.Popen([player, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.start, self.clip = time.monotonic(), name
        except OSError:
            self.process = None

    def amplitude(self):
        if self.process is None or self.process.poll() is not None:
            return 0.0
        levels = self.envelopes.get(self.clip, {}).get('levels', [])
        index = int((time.monotonic() - self.start) * 20)
        return levels[index] if 0 <= index < len(levels) else 0.0

    def set_enabled(self, value):
        self.enabled = bool(value)
        if not self.enabled:
            self.stop()
        try:
            self.preference.parent.mkdir(parents=True, exist_ok=True)
            self.preference.write_text(json.dumps({'speech': self.enabled}) + '\n')
        except OSError:
            pass


class Avatar(Gtk.DrawingArea):
    def __init__(self, speaker=None, reduced=False, size=164):
        super().__init__()
        self.speaker = speaker
        self.reduced = reduced
        self.epoch = time.monotonic()
        self.frames = {}
        for name in ('idle', 'blink', 'talk', 'talk-blink'):
            try:
                self.frames[name] = GdkPixbuf.Pixbuf.new_from_file(str(ASSETS / (name + '.png')))
            except GLib.Error:
                pass
        self.set_size_request(size, size)
        self.set_hexpand(False)
        self.set_halign(Gtk.Align.CENTER)
        self.get_accessible().set_name('Rıfkı, göz kırpan ve konuşurken ağzı hareket eden gerçekçi Van kedisi')
        self.connect('draw', self.draw_cat)
        self.timer = GLib.timeout_add(250 if reduced else 60, self.tick)
        self.connect('destroy', self.closed)

    def tick(self):
        if self.get_mapped():
            self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def closed(self, *_):
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer = None

    def draw_cat(self, _widget, context):
        width, height = self.get_allocated_width(), self.get_allocated_height()
        context.set_source_rgb(1, 1, 1)
        context.paint()
        if not self.frames:
            return False
        t = time.monotonic() - self.epoch
        blink = t % 4.7 > 4.48
        talking = self.speaker is not None and self.speaker.amplitude() > .08
        name = ('talk-blink' if blink else 'talk') if talking else ('blink' if blink else 'idle')
        image = self.frames.get(name, self.frames.get('idle', next(iter(self.frames.values()))))
        size = min(width, height)
        breathe = 1.0 if self.reduced else 1 + .004 * math.sin(t * 1.8)
        context.save()
        context.translate(width / 2, height / 2)
        if not self.reduced:
            context.rotate(math.radians(.55 * math.sin(t * .7)))
        context.scale(size / image.get_width(), size / image.get_height() * breathe)
        Gdk.cairo_set_source_pixbuf(context, image, -image.get_width() / 2, -image.get_height() / 2)
        context.paint()
        context.restore()
        return False


class Companion(Gtk.ApplicationWindow):
    def __init__(self, app, callbacks, reduced=False):
        super().__init__(application=app)
        self.callbacks = callbacks
        self.speaker = Speaker()
        self.status_data = {}
        self.last_stage = ''
        self.set_title('Rıfkı · OğuzDows yardımcın')
        self.set_icon_name('oguzdows')
        self.set_default_size(364, min(570, self.get_screen().get_height() - 80))
        self.set_size_request(290, 370)
        self.get_style_context().add_class('oguzdows-window')
        self.get_style_context().add_class('rifki-window')
        header = Gtk.HeaderBar(title='Rıfkı', subtitle='Çevrimdışı kurulum rehberin')
        header.set_show_close_button(True)
        self.set_titlebar(header)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        body.set_border_width(14)
        self.avatar = Avatar(self.speaker, reduced)
        event = Gtk.EventBox()
        event.add(self.avatar)
        event.connect('button-press-event', lambda *_: self.ask('merhaba'))
        body.pack_start(event, False, False, 0)
        self.stage_label = Gtk.Label(label='Merhaba! Birlikte bakalım.', xalign=0)
        self.stage_label.get_style_context().add_class('section-title')
        self.stage_label.set_line_wrap(True)
        body.pack_start(self.stage_label, False, False, 0)
        self.chat = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.chat.set_left_margin(10)
        self.chat.set_right_margin(10)
        self.chat.set_top_margin(10)
        chat_scroll = Gtk.ScrolledWindow()
        chat_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        chat_scroll.set_size_request(-1, 132)
        chat_scroll.add(self.chat)
        body.pack_start(chat_scroll, True, True, 0)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text('Örneğin: Diskten açılmıyor')
        self.entry.set_max_length(1000)
        self.entry.connect('activate', self.entered)
        body.pack_start(self.entry, False, False, 0)
        chips = Gtk.FlowBox()
        chips.set_selection_mode(Gtk.SelectionMode.NONE)
        chips.set_min_children_per_line(2)
        chips.set_max_children_per_line(3)
        for title, question in (('Disk seçimi', 'disk'), ('Açılış hatası', 'boot'), ('Sonuç', 'sonuç'), ('İnternet', 'internet'), ('Sürücüler', 'sürücü'), ('Duvar kâğıdı', 'duvar')):
            button = Gtk.Button(label=title)
            button.connect('clicked', lambda _, q=question: self.ask(q))
            chips.add(button)
        body.pack_start(chips, False, False, 0)
        self.action = Gtk.Button()
        self.action.set_no_show_all(True)
        self.action.connect('clicked', self.take_action)
        self.action_name = None
        body.pack_start(self.action, False, False, 0)
        self.sound = Gtk.CheckButton(label='Rıfkı konuşsun')
        self.sound.set_active(self.speaker.enabled)
        self.sound.connect('toggled', lambda button: self.speaker.set_enabled(button.get_active()))
        body.pack_start(self.sound, False, False, 0)
        note = Gtk.Label(label='Mikrofon dinlenmez · Mesajların gönderilmez\nRehber yanıtları metin, sesler önceden hazırlanmıştır.', xalign=0)
        note.set_line_wrap(True)
        note.get_style_context().add_class('muted')
        body.pack_start(note, False, False, 0)
        scroll.add(body)
        self.add(scroll)
        self.connect('destroy', lambda *_: self.speaker.stop())
        self.say('Merhaba, ben Rıfkı. Kurulum, disk, açılış ve donanım adımlarında yanındayım. Bana yazabilir veya yardım düğmelerine basabilirsin.', 'hello')

    def say(self, text, clip=None):
        buffer = self.chat.get_buffer()
        buffer.insert(buffer.get_end_iter(), 'Rıfkı: ' + text + '\n\n')
        if buffer.get_char_count() > 16000:
            buffer.delete(buffer.get_start_iter(), buffer.get_iter_at_offset(4000))
        self.chat.scroll_to_iter(buffer.get_end_iter(), 0, False, 0, 1)
        if clip:
            self.speaker.play(clip)

    def entered(self, *_):
        text = self.entry.get_text().strip()
        self.entry.set_text('')
        if text:
            self.ask(text)

    def ask(self, text):
        buffer = self.chat.get_buffer()
        buffer.insert(buffer.get_end_iter(), 'Sen: ' + text[:1000] + '\n')
        answer = reply(text, self.status_data)
        self.say(answer['text'], answer['clip'])
        self.action_name = answer['action']
        names = {'boot-report': 'Salt-okunur açılış raporunu göster', 'network': 'Ağ bağlantılarını aç', 'drivers': 'Donanım sekmesini aç', 'wallpapers': 'Galeriyi aç', 'install': 'Kurulum ekranına dön'}
        if self.action_name in self.callbacks:
            self.action.set_label(names[self.action_name])
            self.action.show()
        else:
            self.action.hide()
        return True

    def take_action(self, *_):
        callback = self.callbacks.get(self.action_name)
        if callback:
            callback()

    def installation(self, data):
        self.status_data = data
        key = (data.get('session'), data.get('stage'), data.get('outcome'))
        if key == self.last_stage:
            return
        self.last_stage = key
        messages = {
            'preparing': ('Kurucu hazırlanıyor', 'Canlı sistem ve kurulum kaynağı kontrol ediliyor. Diskine henüz yazıldığını varsayma.', None),
            'ready': ('Seçimlerini kontrol et', 'Dil, klavye, disk ve kullanıcı bilgilerini kurucuda seç. Son özeti sen onaylayacaksın.', 'disk'),
            'partition': ('Disk işlemleri başladı', 'Onayladığın bölüm düzeni uygulanıyor. Bilgisayarı kapatma.', 'working'),
            'copying': ('Dosyalar yerleşiyor', 'Dosyalar kopyalanıyor. Yüzde ve gerçek ilerleme kurucu ekranında; tahminî bir ilerleme göstermiyorum.', None),
            'bootloader': ('Disk açılışı hazırlanıyor', 'Önyükleyici ve başlangıç dosyaları hazırlanıyor. Bu adım bitmeden başarı bildirmeyeceğim.', None),
            'complete': ('Kurulum tamamlandı', 'Bütün kurulum işleri tamamlandı. Sonuç ekranını incele; diskten ilk açılış ayrıca denenmelidir.', 'success'),
        }
        title, text, clip = messages.get(data.get('stage'), ('Kurucu', 'Kurucu durumunu izliyorum.', None))
        if data.get('outcome') in ('failed', 'incomplete', 'cancelled', 'unknown'):
            title, text, clip = 'Sonucu birlikte inceleyelim', reply('sonuç', data)['text'], 'failure'
        self.stage_label.set_text(title)
        self.say(text, clip)

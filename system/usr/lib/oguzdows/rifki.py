"""Foto-gerçekçi 2B Rıfkı: göz kırpma, nefes, baş hareketi ve sese bağlı ağız."""
from __future__ import annotations

import gi

gi.require_version('Gtk','3.0')
from gi.repository import GLib, Gtk

from rifki_model import reply
from rifki_speech import Speaker
from rifki_pet import DesktopPet, PetView
from rifki_dialogue import HELLO, MOTIONS, PANELS, STAGES
from install_status import description


class Avatar(PetView):
    def __init__(self,speaker=None,reduced=False,size=230):
        super().__init__(speaker,True,width=size,height=round(size*.75))


class Companion(Gtk.ApplicationWindow):
    def __init__(self, app, callbacks, reduced=False, owner=lambda: None):
        super().__init__(application=app)
        self.callbacks = callbacks
        self.speaker = Speaker(GLib.idle_add,self.voice_error)
        self.owner=owner
        self.reduced=reduced
        self.pet=None
        self.current_page='welcome'
        self.last_message=''
        self.last_panel=''
        self.pet_status=Gtk.Label(label='Rıfkı kendi oyun alanında.',xalign=0)
        self.pet_status.set_line_wrap(True)
        self.pet_status.get_style_context().add_class('muted')
        self.status_data = {}
        self.last_stage = ''
        self.set_title('Rıfkı · OğuzDows yardımcın')
        self.set_icon_name('oguzdows')
        self.set_default_size(374, min(700, self.get_screen().get_height() - 80))
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
        self.avatar = PetView(self.speaker, reduced,width=300,height=192)
        event = Gtk.EventBox()
        event.add(self.avatar)
        event.connect('button-press-event', lambda *_: self.ask('merhaba'))
        body.pack_start(event, False, False, 0)
        self.stage_label = Gtk.Label(label='Merhaba! Birlikte bakalım.', xalign=0)
        self.stage_label.get_style_context().add_class('section-title')
        self.stage_label.set_line_wrap(True)
        body.pack_start(self.stage_label, False, False, 0)
        body.pack_start(self.pet_status,False,False,0)
        games=Gtk.FlowBox()
        games.set_selection_mode(Gtk.SelectionMode.NONE)
        games.set_min_children_per_line(2)
        games.set_max_children_per_line(4)
        for action,title in (('jump','Zıpla'),('tail','Kuyruk'),('feather','Tüy topu'),('tea','Çay molası')):
            button=Gtk.Button(label=title)
            button.connect('clicked',lambda _,name=action:self.perform(name))
            games.add(button)
        body.pack_start(games,False,False,0)
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
        speech_buttons=Gtk.Box(spacing=6)
        for title,callback in (('Son mesajı oku',lambda *_:self.speaker.speak(self.last_message)),('Sesi durdur',lambda *_:self.speaker.stop())):
            button=Gtk.Button(label=title)
            button.connect('clicked',callback)
            speech_buttons.pack_start(button,True,True,0)
        body.pack_start(speech_buttons,False,False,0)
        options=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.narration=Gtk.CheckButton(label='Bütün rehber panellerini anlat')
        self.narration.set_active(self.speaker.options.get('narration',True) is not False)
        self.narration.connect('toggled',lambda button:self.speaker.save_option('narration',button.get_active()))
        options.pack_start(self.narration,False,False,0)
        self.attach=Gtk.CheckButton(label='Küçük kedi pencere kenarında görünsün')
        self.attach.set_active(bool(self.speaker.options.get('pet',not reduced)))
        self.attach.connect('toggled',self.pet_toggled)
        options.pack_start(self.attach,False,False,0)
        self.auto=Gtk.CheckButton(label='Kendi kendine oynasın')
        self.auto.set_active(bool(self.speaker.options.get('auto',not reduced)))
        self.auto.connect('toggled',self.auto_toggled)
        options.pack_start(self.auto,False,False,0)
        self.pause=Gtk.CheckButton(label='Hareketi duraklat')
        self.pause.connect('toggled',self.pause_toggled)
        options.pack_start(self.pause,False,False,0)
        read_panel=Gtk.Button(label='Bu paneli anlat')
        read_panel.connect('clicked',lambda *_:self.narrate_page(self.current_page,force=True))
        options.pack_start(read_panel,False,False,0)
        settings=Gtk.Expander(label='Hareket ve ses ayarları')
        settings.add(options)
        settings.connect('notify::expanded',lambda widget,*_:self.say(PANELS['settings']) if widget.get_expanded() else None)
        body.pack_start(settings,False,False,0)
        self.voice_status=Gtk.Label(label='',xalign=0)
        self.voice_status.set_line_wrap(True)
        self.voice_status.get_style_context().add_class('muted')
        body.pack_start(self.voice_status,False,False,0)
        note = Gtk.Label(label='Mikrofon dinlenmez · Mesajların gönderilmez\nHazır ses veya cihazında Türkçe seslendirme.', xalign=0)
        note.set_line_wrap(True)
        note.get_style_context().add_class('muted')
        body.pack_start(note, False, False, 0)
        scroll.add(body)
        self.add(scroll)
        self.connect('destroy', self.closed)
        self.connect('map',lambda *_:self.ensure_pet())
        self.avatar.behaviour.automatic=self.auto.get_active()
        self.say(HELLO)

    def say(self, text, clip=None):
        buffer = self.chat.get_buffer()
        buffer.insert(buffer.get_end_iter(), 'Rıfkı: ' + text + '\n\n')
        if buffer.get_char_count() > 16000:
            buffer.delete(buffer.get_start_iter(), buffer.get_iter_at_offset(4000))
        self.chat.scroll_to_iter(buffer.get_end_iter(), 0, False, 0, 1)
        self.last_message=text
        self.speaker.speak(text,clip)

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
        if answer.get('motion'):
            self.perform(answer['motion'],speak=False)
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

    def voice_error(self,text):
        self.voice_status.set_text(text)

    def ensure_pet(self):
        if self.pet is None and self.attach.get_active():
            self.pet=DesktopPet(self,self.owner,self.speaker,self.reduced,self.pet_status.set_text)
            self.pet.view.behaviour.automatic=self.auto.get_active()
        if self.pet:
            self.pet.enabled=self.attach.get_active()
            self.pet.follow()

    def pet_toggled(self,button):
        self.speaker.save_option('pet',button.get_active())
        self.ensure_pet()

    def auto_toggled(self,button):
        self.speaker.save_option('auto',button.get_active())
        self.avatar.behaviour.automatic=button.get_active()
        if self.pet:
            self.pet.view.behaviour.automatic=button.get_active()

    def pause_toggled(self,button):
        self.avatar.behaviour.set_paused(button.get_active(),__import__('time').monotonic())
        if self.pet:
            self.pet.view.behaviour.set_paused(button.get_active(),__import__('time').monotonic())

    def perform(self,action,speak=True):
        self.avatar.choose(action)
        if self.pet:
            self.pet.choose(action)
        if speak:
            self.say(MOTIONS[action])

    def narrate_page(self,name,force=False,text=None):
        self.current_page=name
        words=text or PANELS.get(name)
        if not words or (not force and (not self.narration.get_active() or self.last_panel==name)):
            return
        self.last_panel=name
        self.say(words)

    def installation(self,data):
        self.status_data=data
        key=(data.get('session'),data.get('stage'),data.get('outcome'),str(data.get('optional_drivers',[])))
        if key==self.last_stage:
            return
        self.last_stage=key
        title,text=STAGES.get(data.get('stage'),('Kurucu','Kurucu durumunu izliyorum.'))
        finished=data.get('outcome') in ('success','failed','incomplete','cancelled','unknown')
        if finished:
            title,text=description(data)
            self.avatar.behaviour.automatic=False
            self.avatar.choose('perch')
            if self.pet:
                self.pet.view.behaviour.automatic=False
                self.pet.choose('perch')
        self.stage_label.set_text(title)
        self.say(text if not finished else title+' '+text)

    def closed(self,*_):
        self.speaker.close()
        if self.pet:
            self.pet.destroy()
            self.pet=None

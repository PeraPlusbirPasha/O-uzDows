#!/usr/bin/env python3
"""OğuzDows rehberi, yerel donanım merkezi ve Türkiye duvar kâğıtları."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardware import is_live, light_profile, memory_kib, read_text, report, supported_broadcom, supported_intel_legacy
import offline
import wallpapers
from pi_support import current_policy, is_pi, model as pi_model

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, Gio, GLib, Gtk


def label(text: str, style: str = "", width: int = 0) -> Gtk.Label:
    widget = Gtk.Label(label=text, xalign=0)
    widget.set_line_wrap(True)
    if width:
        widget.set_max_width_chars(width)
    if style:
        widget.get_style_context().add_class(style)
    return widget


class Welcome(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id="org.oguzdows.Rehber", flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        state_home = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
        self.state_file = state_home / "oguzdows/welcome-seen"
        self.window = None
        self.driver_busy = False
        self.install_busy = False
        self.report_loading = False
        self.report_text = ""
        self.mark_on_close = False
        self.wallpaper_buttons = []

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        args = set(command_line.get_arguments()[1:])
        if args - {"--autostart", "--drivers", "--wallpapers", "--install"}:
            print("Kullanım: oguzdows-welcome [--autostart|--drivers|--wallpapers|--install]", file=sys.stderr)
            return 2
        if "--autostart" in args and self.state_file.exists():
            return 0
        self.mark_on_close = self.mark_on_close or not bool(args & {"--drivers", "--wallpapers"})
        self.activate()
        if "--drivers" in args:
            self.show_drivers()
        if "--wallpapers" in args:
            self.stack.set_visible_child_name("wallpapers")
        if "--install" in args:
            self.stack.set_visible_child_name("welcome")
            GLib.idle_add(self.install)
        return 0

    def do_activate(self) -> None:
        if self.window is None:
            self.build_window()
        self.window.present()

    def build_window(self) -> None:
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_title("OğuzDows Rehberi")
        self.window.set_icon_name("oguzdows")
        self.window.get_style_context().add_class("oguzdows-window")
        self.window.set_position(Gtk.WindowPosition.CENTER)
        screen = self.window.get_screen()
        self.window.set_default_size(min(900, screen.get_width() - 32), min(680, screen.get_height() - 64))
        self.window.set_size_request(520, 360)
        self.window.connect("delete-event", self.on_close)
        header = Gtk.HeaderBar(title="OğuzDows", subtitle="Ay Yıldız")
        header.set_show_close_button(True)
        self.window.set_titlebar(header)
        header.pack_end(label("Canlı oturum" if is_live() else "Senin masaüstün", "pill"))
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        body.set_border_width(24)
        self.stack = Gtk.Stack()
        reduced = not current_policy()["animations"] if is_pi() else light_profile(read_text(Path("/proc/cmdline")), memory_kib())
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE if reduced else Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(160)
        switcher = Gtk.StackSwitcher(stack=self.stack)
        switcher.set_halign(Gtk.Align.CENTER)
        body.pack_start(switcher, False, False, 0)
        self.stack.add_titled(self.welcome_page(), "welcome", "Hoş geldin")
        self.stack.add_titled(self.hardware_page(), "hardware", "Donanım ve Sürücüler")
        self.stack.add_titled(self.wallpapers_page(), "wallpapers", "Duvar Kâğıtları")
        self.stack.connect("notify::visible-child-name", self.page_changed)
        body.pack_start(self.stack, True, True, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(body)
        self.window.add(scroll)
        self.window.show_all()

    def welcome_page(self) -> Gtk.Box:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        hero = Gtk.Box(spacing=22)
        image = Gtk.Image.new_from_file("/usr/share/oguzdows/brand/oguzdows.png")
        image.set_valign(Gtk.Align.CENTER)
        image.get_accessible().set_name("OğuzDows ay yıldız amblemi")
        hero.pack_start(image, False, False, 0)
        words = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        words.pack_start(label("TÜRKÇE · YALIN · ÖZGÜR", "eyebrow"), False, False, 0)
        words.pack_start(label("OğuzDows'a hoş geldin.", "heading", 28), False, False, 0)
        words.pack_start(label("Köklerinden güç alan, seninle hayat bulan masaüstü.", "muted", 50), False, False, 0)
        hero.pack_start(words, True, True, 0)
        page.pack_start(hero, False, False, 12)
        page.pack_start(label("Nasıl başlamak istersin?", "section-title"), False, False, 0)
        choices = Gtk.FlowBox()
        choices.set_selection_mode(Gtk.SelectionMode.NONE)
        choices.set_column_spacing(8)
        choices.set_row_spacing(8)
        choices.set_min_children_per_line(1)
        choices.set_max_children_per_line(3)
        choices.set_homogeneous(True)
        choices.add(self.card("OğuzDows'u keşfet" if is_pi() else "OğuzDows'u dene", "SD/USB üzerindeki kalıcı masaüstünü ve uygulamalarını keşfet." if is_pi() else "Diskine dokunmadan masaüstünü ve uygulamalarını keşfet.", "user-desktop-symbolic", lambda *_: self.window.close(), primary=True))
        if is_pi():
            self.install_button = self.card("Pi masaüstü ayarları", "Sistem zaten kurulu. Görünüm, ekran, ses ve güç ayarlarını düzenle.", "preferences-system-symbolic", lambda *_: self.launch(["/usr/bin/xfce4-settings-manager"]))
        else:
            self.install_button = self.card("OğuzDows'u kur", "Canlı USB'den, internet gerekmeden bilgisayarına yerleştir.", "system-software-install-symbolic", self.install)
            self.install_button.set_sensitive(self.can_install())
            if not is_live():
                self.install_button.set_tooltip_text("Kurulum canlı OğuzDows USB'sinden başlatılır.")
        choices.add(self.install_button)
        choices.add(self.card("Donanımını tanı", "Aygıtları, yüklü firmware'i ve gömülü ek sürücüleri gör.", "preferences-system-symbolic", lambda *_: self.show_drivers()))
        page.pack_start(choices, False, False, 0)
        setup_note = (f"{pi_model() or 'Raspberry Pi'} · {current_policy()['profile']} profili. Değişikliklerin SD/USB üzerinde kalıcıdır." if is_pi() else "Kurulum günlüğü: /var/log/oguzdows/installer.log")
        self.install_status = label(setup_note, "muted", 90)
        page.pack_start(self.install_status, False, False, 0)
        page.pack_start(Gtk.Separator(), False, False, 0)
        page.pack_start(label("Türkçe dil ve Q klavye · İstanbul saat dilimi · Hafif Xfce masaüstü", "muted", 80), False, False, 0)
        gallery = Gtk.Button(label="Türkiye duvar kâğıtlarını keşfet")
        gallery.connect("clicked", lambda *_: self.stack.set_visible_child_name("wallpapers"))
        page.pack_start(gallery, False, False, 0)
        self.show_again = Gtk.CheckButton(label="Bir sonraki girişte bu ekranı yeniden göster")
        page.pack_start(self.show_again, False, False, 0)
        note = "Canlı oturumdaki değişiklikler, kalıcılık ayarlanmadıkça yeniden başlatmada silinir." if is_live() else "Rehbere uygulamalar menüsünden her zaman dönebilirsin."
        page.pack_start(label(note, "muted", 90), False, False, 0)
        return page

    def card(self, title, description, icon, callback, primary=False) -> Gtk.Button:
        button = Gtk.Button()
        button.set_size_request(208, -1)
        button.get_style_context().add_class("card")
        if primary:
            button.get_style_context().add_class("primary")
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG)
        image.set_pixel_size(28)
        image.set_halign(Gtk.Align.START)
        content.pack_start(image, False, False, 0)
        content.pack_start(label(title, "card-title", 24), False, False, 0)
        content.pack_start(label(description, "muted", 25), True, True, 0)
        button.add(content)
        button.connect("clicked", callback)
        return button

    def hardware_page(self) -> Gtk.Box:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.pack_start(label("Önce tanı, sonra kur.", "section-title"), False, False, 8)
        driver_note = ("Pi çekirdekleri ve DTB'leri, VC4/V3D KMS, kartta varsa Broadcom SDIO Wi-Fi / Bluetooth ve USB ağ firmware'i imajdadır. Platform ve SDIO aygıtları da raporlanır; PC için STA sürücüsü Pi Wi-Fi'ına kurulmaz." if is_pi() else "Intel, AMD/ATI, Nouveau; Intel, Realtek, Atheros, Broadcom, Atmel, ZD1211 ve Libertas firmware paketleri ISO'dadır. Aşağıdaki rapor aygıtın gerçekten hangi sürücüye bağlandığını gösterir.")
        page.pack_start(label(driver_note, "muted", 95), False, False, 0)
        self.report_view = Gtk.TextView(editable=False, cursor_visible=False, monospace=True)
        self.report_view.set_left_margin(12)
        self.report_view.set_top_margin(12)
        self.report_view.get_buffer().set_text("Raporu görmek için bu sekmeyi aç.")
        report_scroll = Gtk.ScrolledWindow()
        report_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        report_scroll.set_size_request(-1, 190)
        report_scroll.add(self.report_view)
        page.pack_start(report_scroll, True, True, 0)
        buttons = Gtk.FlowBox()
        buttons.set_selection_mode(Gtk.SelectionMode.NONE)
        buttons.set_min_children_per_line(1)
        buttons.set_max_children_per_line(3)
        buttons.set_column_spacing(8)
        self.refresh_button = Gtk.Button(label="Raporu yenile")
        self.refresh_button.connect("clicked", lambda *_: self.load_report())
        self.save_button = Gtk.Button(label="Raporu kaydet")
        self.save_button.set_sensitive(False)
        self.save_button.connect("clicked", self.save_report)
        network = Gtk.Button(label="Ağ bağlantıları")
        network.connect("clicked", lambda *_: self.launch(["/usr/bin/nm-connection-editor"]))
        for button in (self.refresh_button, self.save_button, network):
            buttons.add(button)
        page.pack_start(buttons, False, False, 0)
        self.broadcom_button = Gtk.Button(label="Gömülü Broadcom STA sürücüsünü kur…")
        self.broadcom_button.set_sensitive(False)
        self.broadcom_button.connect("clicked", lambda *_: self.install_driver("broadcom"))
        page.pack_start(self.broadcom_button, False, False, 0)
        self.intel_button = Gtk.Button(label="Gömülü Intel 2100 / 2200 / 2915 firmware'ini kur…")
        self.intel_button.set_sensitive(False)
        self.intel_button.connect("clicked", lambda *_: self.install_driver("intel-legacy-accept-license"))
        page.pack_start(self.intel_button, False, False, 0)
        if is_pi():
            for button in (self.broadcom_button, self.intel_button):
                button.set_no_show_all(True)
                button.hide()
            page.pack_start(label("mini: ARMv6 veya en fazla 768 MiB; light: en fazla 2 GiB; full: daha fazla RAM. LZ4 zram sınırlıdır, SD swap kapalıdır; overclock uygulanmaz. 512 MiB ile modern web/ofis ağırdır. ARMv6 tarayıcısı temel Netsurf'tür (JavaScript yok). Profil: /etc/oguzdows/pi.conf", "muted", 95), False, False, 0)
        else:
            page.pack_start(label("Bu iki ek paket ve gerekli derleme araçları ISO'ya gömülüdür; eşleşen kartlarda internet gerekmez. Lisans ve yönetici onayı istenir. Canlıda onayladığın seçim disk kurulumuna taşınır. Gri düğme: bu sürücüyle eşleşen kart algılanmadı.", "muted", 95), False, False, 0)
        status = Gtk.Box(spacing=10)
        self.spinner = Gtk.Spinner()
        self.status = label("Donanım bilgilerin cihazında kalır.", "muted", 90)
        status.pack_start(self.spinner, False, False, 0)
        status.pack_start(self.status, True, True, 0)
        page.pack_start(status, False, False, 0)
        return page

    def wallpapers_page(self) -> Gtk.Box:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        page.pack_start(label("Türkiye'nin renkleri masaüstünde.", "section-title"), False, False, 6)
        page.pack_start(label("Özgün çizimlerden oluşan altı duvar kâğıdı. Tamamı çevrimdışı; animasyon veya ek arka plan servisi yok.", "muted", 90), False, False, 0)
        grid = Gtk.FlowBox()
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_min_children_per_line(1)
        grid.set_max_children_per_line(3)
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        for item in wallpapers.catalog():
            button = Gtk.Button()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            box.set_border_width(8)
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(item["preview"], 224, 126, True)
                box.pack_start(Gtk.Image.new_from_pixbuf(pixbuf), False, False, 0)
            except GLib.Error:
                box.pack_start(Gtk.Image.new_from_icon_name("image-x-generic", Gtk.IconSize.DIALOG), False, False, 0)
            box.pack_start(label(item["name"], "card-title", 25), False, False, 0)
            box.pack_start(label("Masaüstüne uygula", "muted"), False, False, 0)
            button.add(box)
            button.connect("clicked", lambda _, choice=item: self.apply_wallpaper(choice))
            grid.add(button)
            self.wallpaper_buttons.append(button)
        page.pack_start(grid, False, False, 0)
        self.wallpaper_status = label("Seçimin SD/USB üzerinde kaydedilir; yeniden başlatınca korunur." if is_pi() else "Seçimin sonraki oturumda korunur. Canlı USB'de kalıcılık yoksa yeniden başlatmada sıfırlanır.", "muted", 90)
        page.pack_start(self.wallpaper_status, False, False, 0)
        return page

    def apply_wallpaper(self, item):
        for button in self.wallpaper_buttons:
            button.set_sensitive(False)
        self.wallpaper_status.set_text("Duvar kâğıdı uygulanıyor…")
        def work():
            try:
                wallpapers.apply(item["id"])
                text = item["name"] + " uygulandı; seçimin kaydedildi."
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                text = str(error)
            GLib.idle_add(self.wallpaper_finished, text)
        threading.Thread(target=work, daemon=True).start()

    def wallpaper_finished(self, text):
        self.wallpaper_status.set_text(text)
        for button in self.wallpaper_buttons:
            button.set_sensitive(True)
        return GLib.SOURCE_REMOVE

    def page_changed(self, *_):
        if self.stack.get_visible_child_name() == "hardware" and not self.report_text:
            self.load_report()

    def show_drivers(self):
        self.stack.set_visible_child_name("hardware")

    def load_report(self):
        if self.report_loading or self.driver_busy or self.install_busy:
            return
        self.report_loading = True
        self.refresh_button.set_sensitive(False)
        self.spinner.start()
        self.status.set_text("Donanım okunuyor…")
        def work():
            try:
                text = report()
                broadcom, intel = ([], []) if is_pi() else (supported_broadcom(), supported_intel_legacy())
            except Exception:
                text, broadcom, intel = "Donanım raporu okunamadı. Yeniden deneyebilirsin.", [], []
            GLib.idle_add(self.report_ready, text, broadcom, intel)
        threading.Thread(target=work, daemon=True).start()

    def report_ready(self, text, broadcom, intel):
        self.report_loading = False
        self.report_text = text
        self.report_view.get_buffer().set_text(text)
        self.spinner.stop()
        self.refresh_button.set_sensitive(True)
        self.save_button.set_sensitive(True)
        self.broadcom_button.set_sensitive(bool(broadcom) and not self.driver_busy and not self.install_busy)
        self.intel_button.set_sensitive(bool(intel) and not self.driver_busy and not self.install_busy)
        for button, devices in ((self.broadcom_button, broadcom), (self.intel_button, intel)):
            button.set_tooltip_text("Algılanan uyumlu aygıt: " + ", ".join(devices) if devices else "Bu ek sürücüyle eşleşen bir kart algılanmadı. Raporundaki PCI/USB kimliğini paylaşabilirsin.")
        self.status.set_text("Rapor hazır. SÜRÜCÜ BAĞLI DEĞİL satırları ayrıca incelenmelidir. Bilgilerin gönderilmedi.")
        return GLib.SOURCE_REMOVE

    def save_report(self, *_):
        dialog = Gtk.FileChooserDialog(title="OğuzDows donanım raporunu kaydet", transient_for=self.window, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons("Vazgeç", Gtk.ResponseType.CANCEL, "Kaydet", Gtk.ResponseType.OK)
        dialog.set_current_name("OguzDows-donanim.txt")
        dialog.set_do_overwrite_confirmation(True)
        if dialog.run() == Gtk.ResponseType.OK:
            try:
                Path(dialog.get_filename()).write_text(self.report_text, encoding="utf-8")
            except OSError:
                self.message("Rapor kaydedilemedi.", "Seçtiğin klasörün yazılabilir olduğundan emin ol.")
        dialog.destroy()

    def can_install(self):
        return is_live() and Path("/usr/local/sbin/oguzdows-installer").is_file()

    def install(self, *_):
        if self.install_busy or self.driver_busy:
            self.message("Başka bir işlem devam ediyor.", "Kurucu veya sürücü işlemi tamamlanana kadar bekle.")
            return GLib.SOURCE_REMOVE
        if not self.can_install():
            self.message("Kurulum canlı USB'den başlatılır.", "Canlı OğuzDows USB'siyle açıldığından emin ol.")
            return GLib.SOURCE_REMOVE
        self.install_busy = True
        self.install_button.set_sensitive(False)
        self.broadcom_button.set_sensitive(False)
        self.intel_button.set_sensitive(False)
        self.install_status.set_text("Yönetici onayı bekleniyor / OğuzDows kurucusu açık…")
        def work():
            try:
                result = subprocess.run(["/usr/bin/pkexec", "/usr/local/sbin/oguzdows-installer"], capture_output=True, text=True, errors="replace", check=False)
                code, detail = result.returncode, (result.stderr or result.stdout).strip()[-5000:]
            except OSError as error:
                code, detail = 1, str(error)
            GLib.idle_add(self.install_finished, code, detail)
        threading.Thread(target=work, daemon=True).start()
        return GLib.SOURCE_REMOVE

    def install_finished(self, code, detail):
        self.install_busy = False
        self.install_button.set_sensitive(self.can_install())
        self.broadcom_button.set_sensitive(bool(supported_broadcom()))
        self.intel_button.set_sensitive(bool(supported_intel_legacy()))
        if code == 0:
            self.install_status.set_text("Kurucu kapandı. Kurulum yaptıysan USB'yi çıkarıp yeniden başlatabilirsin.")
        else:
            self.install_status.set_text("Kurucu tamamlanamadı; hata ayrıntılarını kontrol et.")
            title = "Yetkilendirme iptal edildi." if code in (126, 127) else "OğuzDows kurucusu hata ile kapandı."
            self.message(title, (detail + "\n\nGünlük: /var/log/oguzdows/installer.log").strip())
        return GLib.SOURCE_REMOVE

    def launch(self, command):
        try:
            subprocess.Popen(command)
        except OSError:
            self.message("Uygulama başlatılamadı.", "Gerekli bileşenin kurulu olduğunu kontrol et.")

    def install_driver(self, action):
        if self.driver_busy or self.report_loading or self.install_busy:
            return
        text = offline.license_text(action)
        if not text:
            self.message("Gömülü sürücü lisansı bulunamadı.", "Güncel OğuzDows ISO'sunu kullan; paket lisansı olmadan kurulum başlatılmadı.")
            return
        ready = offline.payload(action) is not None and (action != "broadcom" or offline.headers_available())
        if not ready and action != "broadcom":
            self.message("Gömülü paket doğrulanamadı.", "ISO bütünlüğünü SHA-256 ile denetle. Hiçbir değişiklik yapılmadı.")
            return
        title = "Broadcom STA sürücüsü" if action == "broadcom" else "Intel 2100 / 2200 / 2915 firmware'i"
        dialog = Gtk.Dialog(title=title, transient_for=self.window, modal=True)
        dialog.add_button("Vazgeç", Gtk.ResponseType.CANCEL)
        confirm = dialog.add_button("Onayla ve kur", Gtk.ResponseType.OK)
        confirm.set_sensitive(False)
        content = dialog.get_content_area()
        content.set_spacing(12)
        content.set_border_width(16)
        note = "ISO'daki paket kullanılacak; internet gerekmez." if ready else "Çekirdeğin değişmiş: internetten eşleşen başlıklar ve STA indirilecek."
        content.pack_start(label(note + " Mevcut açık sürücünün yerini alabilir. Canlıda onayladığın seçim disk kurulumuna taşınır.", "", 75), False, False, 0)
        view = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        view.get_buffer().set_text(text)
        scroll = Gtk.ScrolledWindow()
        scroll.set_size_request(460, 240)
        scroll.add(view)
        content.pack_start(scroll, True, True, 0)
        consent = Gtk.CheckButton(label="Yukarıdaki özgün lisansı okudum ve kabul ediyorum.")
        consent.connect("toggled", lambda button: confirm.set_sensitive(button.get_active()))
        content.pack_start(consent, False, False, 0)
        dialog.show_all()
        answer = dialog.run()
        agreed = consent.get_active()
        dialog.destroy()
        if answer != Gtk.ResponseType.OK or not agreed:
            return
        self.driver_busy = True
        self.broadcom_button.set_sensitive(False)
        self.intel_button.set_sensitive(False)
        self.refresh_button.set_sensitive(False)
        self.install_button.set_sensitive(False)
        self.spinner.start()
        self.status.set_text("Yönetici onayı bekleniyor / sürücü kuruluyor. Birkaç dakika sürebilir…")
        def work():
            try:
                command = ["/usr/bin/pkexec", "/usr/local/sbin/oguzdows-driver-helper", action]
                if ready:
                    command.append("--offline")
                result = subprocess.run(command, capture_output=True, text=True, errors="replace", check=False)
                message = result.stdout.strip() if result.returncode == 0 else "Sürücü işlemi tamamlanmadı veya yetkilendirme iptal edildi. " + result.stderr.strip()[-1200:]
            except OSError:
                message = "Sürücü yardımcısı başlatılamadı."
            GLib.idle_add(self.driver_finished, message)
        threading.Thread(target=work, daemon=True).start()

    def driver_finished(self, text):
        self.driver_busy = False
        self.spinner.stop()
        self.refresh_button.set_sensitive(True)
        self.broadcom_button.set_sensitive(bool(supported_broadcom()))
        self.intel_button.set_sensitive(bool(supported_intel_legacy()))
        self.install_button.set_sensitive(self.can_install())
        self.status.set_text(text)
        return GLib.SOURCE_REMOVE

    def message(self, title, detail):
        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True, message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.CLOSE, text=title)
        dialog.format_secondary_text(detail)
        dialog.run()
        dialog.destroy()

    def on_close(self, *_):
        if self.driver_busy or self.install_busy:
            self.message("Kurucu / sürücü işlemi devam ediyor.", "İşlemi yarıda kesmemek için önce kurucuyu kapat veya sürücü işleminin bitmesini bekle.")
            return True
        if self.mark_on_close:
            try:
                if self.show_again.get_active():
                    self.state_file.unlink(missing_ok=True)
                else:
                    self.state_file.parent.mkdir(parents=True, exist_ok=True)
                    self.state_file.write_text("OğuzDows\n", encoding="utf-8")
            except OSError:
                print("OğuzDows karşılama tercihi kaydedilemedi.", file=sys.stderr)
        self.window = None
        return False


if __name__ == "__main__":
    raise SystemExit(Welcome().run(sys.argv))

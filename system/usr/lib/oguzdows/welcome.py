#!/usr/bin/env python3
"""OğuzDows ilk karşılama ve donanım merkezi — yerel GTK 3 arayüzü."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardware import is_live, light_profile, memory_kib, read_text, report, supported_broadcom

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk


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
        self.report_loading = False
        self.report_text = ""
        self.mark_on_close = False

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        args = set(command_line.get_arguments()[1:])
        if args - {"--autostart", "--drivers"}:
            print("Kullanım: oguzdows-welcome [--autostart|--drivers]", file=sys.stderr)
            return 2
        if "--autostart" in args and self.state_file.exists():
            return 0
        self.mark_on_close = self.mark_on_close or "--drivers" not in args
        self.activate()
        if "--drivers" in args:
            self.show_drivers()
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
        self.window.set_default_size(min(900, screen.get_width() - 32), min(640, screen.get_height() - 64))
        self.window.set_size_request(520, 360)
        self.window.connect("delete-event", self.on_close)
        header = Gtk.HeaderBar(title="OğuzDows", subtitle="Ay Yıldız")
        header.set_show_close_button(True)
        self.window.set_titlebar(header)
        badge = label("Canlı oturum" if is_live() else "Senin masaüstün", "pill")
        header.pack_end(badge)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        body.set_border_width(24)
        self.stack = Gtk.Stack()
        reduced = light_profile(read_text(Path("/proc/cmdline")), memory_kib())
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE if reduced else Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(160)
        switcher = Gtk.StackSwitcher(stack=self.stack)
        switcher.set_halign(Gtk.Align.CENTER)
        body.pack_start(switcher, False, False, 0)
        self.stack.add_titled(self.welcome_page(), "welcome", "Hoş geldin")
        self.stack.add_titled(self.hardware_page(), "hardware", "Donanım ve Sürücüler")
        self.stack.connect("notify::visible-child-name", self.page_changed)
        body.pack_start(self.stack, True, True, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(body)
        self.window.add(scroll)
        self.window.show_all()

    def welcome_page(self) -> Gtk.Box:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
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
        choices.add(self.card("OğuzDows'u dene", "Diskine dokunmadan masaüstünü ve uygulamalarını keşfet.", "user-desktop-symbolic", lambda *_: self.window.close(), primary=True))
        install = self.card("OğuzDows'u kur", "Hazır olduğunda OğuzDows'u bilgisayarına yerleştir.", "system-software-install-symbolic", self.install)
        install.set_sensitive(is_live() and Path("/usr/local/sbin/oguzdows-installer").is_file())
        if not is_live():
            install.set_tooltip_text("OğuzDows zaten kurulu. Kurulum canlı USB'den başlatılır.")
        choices.add(install)
        choices.add(self.card("Donanımını tanı", "Sürücüleri incele, eski cihazın için seçenekleri gör.", "preferences-system-symbolic", lambda *_: self.show_drivers()))
        page.pack_start(choices, False, False, 0)
        page.pack_start(Gtk.Separator(), False, False, 0)
        page.pack_start(label("Türkçe dil ve Q klavye · İstanbul saat dilimi · Hafif Xfce masaüstü", "muted", 80), False, False, 0)
        self.show_again = Gtk.CheckButton(label="Bir sonraki girişte bu ekranı yeniden göster")
        self.show_again.set_active(False)
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
        page.pack_start(label("Intel, AMD/ATI, Nouveau ve yaygın Wi-Fi sürücüleri ISO'ya dahildir. Pek çok aygıt otomatik tanınır; uyumluluk modele ve çekirdeğe bağlıdır.", "muted", 95), False, False, 0)
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
        self.broadcom_button = Gtk.Button(label="Ek Broadcom STA sürücüsü kur…")
        self.broadcom_button.set_sensitive(False)
        self.broadcom_button.connect("clicked", self.install_broadcom)
        page.pack_start(self.broadcom_button, False, False, 0)
        page.pack_start(label("Ek sürücü yalnızca desteklenen aygıtlarda sunulur. İnternet ve yönetici onayı gerekir; değişiklikten sonra yeniden başlatılır. Hiçbir sürücü kendiliğinden kurulmaz.", "muted", 95), False, False, 0)
        status = Gtk.Box(spacing=10)
        self.spinner = Gtk.Spinner()
        self.status = label("Donanım bilgilerin cihazında kalır.", "muted", 90)
        status.pack_start(self.spinner, False, False, 0)
        status.pack_start(self.status, True, True, 0)
        page.pack_start(status, False, False, 0)
        return page

    def page_changed(self, *_):
        if self.stack.get_visible_child_name() == "hardware" and not self.report_text:
            self.load_report()

    def show_drivers(self):
        self.stack.set_visible_child_name("hardware")

    def load_report(self):
        if self.report_loading or self.driver_busy:
            return
        self.report_loading = True
        self.refresh_button.set_sensitive(False)
        self.spinner.start()
        self.status.set_text("Donanım okunuyor…")

        def work():
            try:
                text, devices = report(), supported_broadcom()
            except Exception:
                text, devices = "Donanım raporu okunamadı. Yeniden deneyebilirsin.", []
            GLib.idle_add(self.report_ready, text, devices)

        threading.Thread(target=work, daemon=True).start()

    def report_ready(self, text, devices):
        self.report_loading = False
        self.report_text = text
        self.report_view.get_buffer().set_text(text)
        self.spinner.stop()
        self.refresh_button.set_sensitive(True)
        self.save_button.set_sensitive(True)
        self.broadcom_button.set_sensitive(bool(devices))
        self.broadcom_button.set_tooltip_text("Algılanan uyumlu aygıt: " + ", ".join(devices) if devices else "STA gerektiren desteklenmiş bir Broadcom aygıtı algılanmadı.")
        self.status.set_text("Rapor hazır. Bilgilerin hiçbir yere gönderilmedi.")
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

    def install(self, *_):
        self.launch(["/usr/bin/pkexec", "/usr/local/sbin/oguzdows-installer"])

    def launch(self, command):
        try:
            subprocess.Popen(command)
        except OSError:
            self.message("Uygulama başlatılamadı.", "Gerekli bileşenin kurulu olduğunu kontrol et.")

    def install_broadcom(self, *_):
        if self.driver_busy or self.report_loading:
            return
        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True, message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.OK_CANCEL, text="Ek Broadcom STA sürücüsü kurulsun mu?")
        dialog.format_secondary_text("İnternet bağlantısı gerekir. Bu sürücü mevcut açık sürücünün yerine geçebilir. Kurulum sonunda yeniden başlatmalısın. Canlı oturumdaki değişiklikler kalıcı olmayabilir.")
        answer = dialog.run()
        dialog.destroy()
        if answer != Gtk.ResponseType.OK:
            return
        self.driver_busy = True
        self.broadcom_button.set_sensitive(False)
        self.refresh_button.set_sensitive(False)
        self.spinner.start()
        self.status.set_text("Yönetici onayı bekleniyor / sürücü kuruluyor. Bu işlem birkaç dakika sürebilir…")

        def work():
            try:
                result = subprocess.run(["/usr/bin/pkexec", "/usr/local/sbin/oguzdows-driver-helper", "broadcom"], capture_output=True, text=True, check=False)
                text = result.stdout.strip() if result.returncode == 0 else "Sürücü işlemi tamamlanmadı veya yetkilendirme iptal edildi. Ayrıntılar: /var/log/oguzdows/drivers.log"
            except OSError:
                text = "Sürücü yardımcısı başlatılamadı."
            GLib.idle_add(self.driver_finished, text)

        threading.Thread(target=work, daemon=True).start()

    def driver_finished(self, text):
        self.driver_busy = False
        self.spinner.stop()
        self.refresh_button.set_sensitive(True)
        self.broadcom_button.set_sensitive(bool(supported_broadcom()))
        self.status.set_text(text)
        return GLib.SOURCE_REMOVE

    def message(self, title, detail):
        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True, message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.CLOSE, text=title)
        dialog.format_secondary_text(detail)
        dialog.run()
        dialog.destroy()

    def on_close(self, *_):
        if self.driver_busy:
            self.message("Sürücü işlemi devam ediyor.", "Paket yöneticisini yarıda kesmemek için işlem bitene kadar bekle.")
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

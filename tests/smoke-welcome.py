#!/usr/bin/env python3
"""Xvfb altında gerçek GTK penceresini açar; paket kurmaz ve disk silmez.

CI, önce temayı ve render-assets.py çıktısını /usr/share altına yerleştirir.
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from support import ROOT, load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("test-results"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if not Gtk.init_check([])[0]:
        raise RuntimeError("GTK için bir görüntü sunucusu gerekli; Xvfb ile çalıştırın.")
    errors = []
    with tempfile.TemporaryDirectory(prefix="oguzdows-ui-") as state:
        os.environ["XDG_STATE_HOME"] = state
        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-theme-name", "OguzDows")
        provider = Gtk.CssProvider()
        provider.load_from_path(str(ROOT / "system/usr/share/themes/OguzDows/gtk-3.0/gtk.css"))
        notify_provider = Gtk.CssProvider()
        notify_provider.load_from_path(str(ROOT / "system/usr/share/themes/OguzDows/xfce-notify-4.0/gtk.css"))
        welcome = load("oguzdows_welcome_smoke", "system/usr/lib/oguzdows/welcome.py")
        app = welcome.Welcome()
        app.register(None)
        app.activate()
        app.mark_on_close = True
        loop = GLib.MainLoop()

        def screenshot(name):
            window = app.window.get_window()
            width, height = app.window.get_size()
            pixbuf = Gdk.pixbuf_get_from_window(window, 0, 0, width, height)
            if pixbuf is None:
                raise AssertionError("GTK ekran görüntüsü alınamadı")
            pixbuf.savev(str(args.output / name), "png", [], [])

        def start():
            try:
                assert app.stack.get_visible_child_name() == "welcome"
                assert not app.show_again.get_active()
                screenshot("welcome.png")
                app.window.resize(600, 440)
            except Exception as error:
                errors.append(str(error))
            return GLib.SOURCE_REMOVE

        def gallery():
            try:
                screenshot("welcome-small.png")
                assert len(app.wallpaper_buttons) == 6, "Türkiye galerisinde altı seçim bulunmalı"
                app.stack.set_visible_child_name("wallpapers")
            except Exception as error:
                errors.append(str(error))
            return GLib.SOURCE_REMOVE

        def hardware():
            try:
                screenshot("wallpapers.png")
                app.window.resize(900, 600)
                app.show_drivers()
            except Exception as error:
                errors.append(str(error))
            return GLib.SOURCE_REMOVE

        def closed(*_):
            # Gtk.Window.close() kapanış olayını kuyruğa koyar. Tercih ancak
            # delete-event işlendikten sonra yazılır; önce kontrol etmek yarıştı.
            try:
                assert app.state_file.is_file(), "İlk açılış tercihi kaydedilmedi"
            except Exception as error:
                errors.append(str(error))
            finally:
                loop.quit()

        def finish():
            if app.report_loading:
                return GLib.SOURCE_CONTINUE
            try:
                assert app.stack.get_visible_child_name() == "hardware"
                assert app.report_text, "Donanım raporu üretilmedi"
                assert app.save_button.get_sensitive()
                assert app.intel_button is not None
                assert app.install_status is not None
                # Başlatma hatası sessizce kaybolmasın; gerçek kurucu çağırma.
                original_message = app.message
                messages = []
                app.message = lambda *args: messages.append(args)
                app.install_finished(1, "Kurucu başlatma hata testi")
                app.message = original_message
                assert messages and "Kurucu başlatma hata testi" in messages[0][1]
                screenshot("hardware.png")
                app.window.connect("destroy", closed)
                app.window.close()
            except Exception as error:
                errors.append(str(error))
                loop.quit()
            return GLib.SOURCE_REMOVE

        def timed_out():
            errors.append("GTK kontrolü 45 saniyede tamamlanmadı.")
            loop.quit()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(350, start)
        GLib.timeout_add(800, gallery)
        GLib.timeout_add(1400, hardware)
        GLib.timeout_add(5000, finish)
        GLib.timeout_add(45000, timed_out)
        loop.run()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("GTK karşılama, küçük ekran, donanım sekmesi ve ilk açılış tercihi doğrulandı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

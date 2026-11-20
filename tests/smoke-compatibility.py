#!/usr/bin/env python3
"""Gerçek GTK: dosya incelemesi, onay varsayılanı ve cihaz merkezi. Motor çalışmaz."""
import argparse
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GLib, Gtk
from support import load
from test_compatibility import pe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('test-results'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    errors = []
    with tempfile.TemporaryDirectory() as temporary:
        os.environ.update(XDG_CONFIG_HOME=temporary, XDG_DATA_HOME=temporary, XDG_STATE_HOME=temporary, OGUZDOWS_TESTING='1')
        module = load('compat_gtk_smoke', 'system/usr/lib/oguzdows/compatibility.py')
        app = module.Compatibility()
        app.register(None)
        app.activate()
        loop = GLib.MainLoop()
        path = Path(temporary) / 'test.exe'
        path.write_bytes(pe())
        def capture(window, name):
            native = window.get_window()
            native.process_updates(True)
            width, height = window.get_size()
            image = Gdk.pixbuf_get_from_window(native, 0, 0, width, height)
            assert image is not None
            image.savev(str(args.output / name), 'png', [], [])
        def start():
            try:
                assert app.receipt is None and not app.run_button.get_sensitive()
                capture(app.window, 'compatibility.png')
                app.inspect(path)
            except Exception as error:
                errors.append(str(error)); loop.quit()
            return GLib.SOURCE_REMOVE
        def inspected():
            if app.busy:
                return GLib.SOURCE_CONTINUE
            try:
                assert app.receipt and app.receipt['kind'] == 'exe'
                assert not app.ack.get_active() and not app.run_button.get_sensitive()
                capture(app.window, 'compatibility-inspected.png')
                app.reasons = []  # Sadece GUI onay iptal yolu; gerçek Wine yok.
                app.ack.set_active(True)
                assert app.run_button.get_sensitive()
                def cancel():
                    for widget in Gtk.Window.list_toplevels():
                        if isinstance(widget, Gtk.MessageDialog):
                            try:
                                assert widget.get_response_for_widget(widget.get_default_widget()) == Gtk.ResponseType.CANCEL
                            except Exception as error:
                                errors.append(str(error))
                            finally:
                                widget.response(Gtk.ResponseType.CANCEL)
                            return GLib.SOURCE_REMOVE
                    return GLib.SOURCE_CONTINUE
                # Default yanıtı API üzerinden ayrıca izlenir; hiçbir motor / kopya çağrısı yok.
                GLib.timeout_add(100, cancel)
                with patch.object(module.core, 'stage', side_effect=AssertionError('İptalde kopya alınamaz')) as stage:
                    app.approve()
                    stage.assert_not_called()
                assert 'Vazgeçildi' in app.status.get_text()
                app.window.destroy()
                device_module = load('devices_gtk_smoke', 'system/usr/lib/oguzdows/devices.py')
                device_app = device_module.Devices()
                device_app.register(None)
                device_app.activate()
                def finish():
                    capture(device_app.window, 'device-center.png')
                    device_app.window.destroy()
                    loop.quit()
                    return GLib.SOURCE_REMOVE
                GLib.timeout_add(250, finish)
            except Exception as error:
                errors.append(str(error)); loop.quit()
            return GLib.SOURCE_REMOVE
        def timeout():
            errors.append('Uyumluluk GTK testi zaman aşımı.'); loop.quit(); return GLib.SOURCE_REMOVE
        GLib.timeout_add(300, start)
        GLib.timeout_add(800, inspected)
        GLib.timeout_add_seconds(20, timeout)
        loop.run()
    if errors:
        raise RuntimeError('\n'.join(errors))
    print('Uyumluluk GTK / EXE inceleme / iptal / cihaz merkezi geçti. Wine, APK veya paket kurulmadı.')


if __name__ == '__main__':
    main()

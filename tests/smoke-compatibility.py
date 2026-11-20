#!/usr/bin/env python3
"""Her GTK uygulaması ayrı süreçte: inceleme / varsayılan iptal / cihaz merkezi."""
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
    parser.add_argument('--component', choices=('compatibility', 'devices'), default='compatibility')
    parser.add_argument('--phone', action='store_true', help='Dar host ekranı / telefon yerleşimi; fiziksel cihaz testi değil')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    errors = []
    with tempfile.TemporaryDirectory() as temporary:
        os.environ.update(XDG_CONFIG_HOME=temporary, XDG_DATA_HOME=temporary, XDG_STATE_HOME=temporary, OGUZDOWS_TESTING='1')
        module = load('compat_gtk_' + args.component, 'system/usr/lib/oguzdows/' + args.component + '.py')
        if args.phone:
            profile = module.device_support.get('pinephone')
            module.device_support.current = lambda *_args, **_kwargs: profile
        app = module.Compatibility() if args.component == 'compatibility' else module.Devices()
        assert app.register(None)
        app.activate()
        loop = GLib.MainLoop()
        path = Path(temporary) / 'test.exe'
        path.write_bytes(pe())
        def capture(name):
            native = app.window.get_window()
            native.process_updates(True)
            width, height = app.window.get_size()
            if args.phone:
                assert width <= app.window.get_screen().get_width(), 'Uyumluluk / cihaz merkezi dar ekranın dışına taşmamalı'
            image = Gdk.pixbuf_get_from_window(native, 0, 0, width, height)
            assert image is not None
            image.savev(str(args.output / name), 'png', [], [])
        def close():
            app.window.destroy()
            loop.quit()
        def start():
            try:
                if args.component == 'devices':
                    capture('device-center.png')
                    close()
                    return GLib.SOURCE_REMOVE
                assert app.receipt is None and not app.run_button.get_sensitive()
                capture('compatibility.png')
                app.inspect(path)
            except Exception as error:
                errors.append(str(error)); loop.quit()
            return GLib.SOURCE_REMOVE
        def inspected():
            if args.component == 'devices':
                return GLib.SOURCE_REMOVE
            if app.busy:
                return GLib.SOURCE_CONTINUE
            try:
                assert app.receipt and app.receipt['kind'] == 'exe'
                assert not app.ack.get_active() and not app.run_button.get_sensitive()
                capture('compatibility-inspected.png')
                app.reasons = []  # Yalnızca UI onay iptali; motorlar yok / çağrılmaz.
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
                GLib.timeout_add(100, cancel)
                with patch.object(module.core, 'stage', side_effect=AssertionError('İptalde kopya alınamaz')) as stage:
                    app.approve()
                    stage.assert_not_called()
                assert 'Vazgeçildi' in app.status.get_text()
                close()
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
    print(args.component + ': gerçek GTK geçti; Wine, APK veya paket kurulmadı.')


if __name__ == '__main__':
    main()

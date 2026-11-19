#!/usr/bin/env python3
"""Gerçek mağaza başlatıcısı + GNOME Yazılımlar + Xfwm pencere yaşam döngüsü.

Paket kurmaz; Flathub kurulumu / PackageKit işlemi sınamaz. Geçici kullanıcı
ayarları ve sınırlı yerel eklentilerle yalnızca gerçek uygulama ömrünü sınar.
"""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkX11', '3.0')
from gi.repository import Gdk, GdkX11, Gio, GLib, Gtk
from Xlib import X
from Xlib.protocol import event
from support import ROOT, load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('test-results'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if not Gtk.init_check([])[0]:
        raise RuntimeError('Xvfb gerekli.')
    errors = []
    report = {'real_gnome_software': True, 'real_isolated_launcher': True, 'real_xfwm': True,
              'remote_added': False, 'package_installation_tested': False, 'packagekit_exercised': False,
              'consent_preanswered_for_lifecycle_test': True}
    lifecycle = load('native_store_lifecycle', 'system/usr/lib/oguzdows/store_lifecycle.py')
    with tempfile.TemporaryDirectory(prefix='oguzdows-store-native-') as directory:
        os.environ.update(XDG_CONFIG_HOME=directory, XDG_STATE_HOME=directory,
                          XDG_CACHE_HOME=directory, GSETTINGS_BACKEND='keyfile', GSK_RENDERER='cairo',
                          GNOME_SOFTWARE_PLUGINS_ALLOWLIST='appstream,flatpak,icons,key-colors,provenance,provenance-license')
        # İnceleme servisine gönderim / ilk açılış tanıtımı bu ömür testinin işi değil.
        for key, value in (('first-run', 'false'), ('review-server', "''")):
            subprocess.run(['gsettings', 'set', 'org.gnome.software', key, value], check=True)
        state = Path(directory) / 'oguzdows/store-choice'
        state.parent.mkdir(parents=True)
        state.write_text('asked\n')
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        def has_owner():
            result = bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
                'org.freedesktop.DBus', 'NameHasOwner', GLib.Variant('(s)', ('org.gnome.Software',)),
                GLib.VariantType.new('(b)'), Gio.DBusCallFlags.NONE, 3000, None)
            return result.unpack()[0]
        assert not has_owner(), 'Mağaza açılmadan native D-Bus servisi çalışmamalı.'
        with (args.output / 'store-xfwm.log').open('w') as wm_log, (args.output / 'store-native.log').open('w') as shop_log:
            wm = subprocess.Popen(['xfwm4', '--compositor=off'], stdout=wm_log, stderr=subprocess.STDOUT)
            wrapper, monitor = None, None
            phase = {'name': 'waiting-wm', 'ticks': 0}
            loop = GLib.MainLoop()
            def tick():
                nonlocal wrapper, monitor
                try:
                    phase['ticks'] += 1
                    if phase['ticks'] > 600:
                        raise AssertionError('Gerçek mağaza ömür testi 120 saniyeyi aştı: ' + phase['name'] + ' · ' + phase.get('last_wm_error', ''))
                    if phase['name'] == 'waiting-wm':
                        try:
                            if monitor is None:
                                monitor = lifecycle.X11Windows()
                            monitor.windows()
                        except Exception as error:
                            phase['last_wm_error'] = str(error)
                            return GLib.SOURCE_CONTINUE
                        wrapper = subprocess.Popen(['/usr/bin/python3', '-I', str(ROOT / 'system/usr/lib/oguzdows/store.py'), '--updates'],
                            stdout=shop_log, stderr=subprocess.STDOUT)
                        phase['name'] = 'waiting-window'
                    else:
                        monitor.consume()
                        if phase['name'] != 'exit-requested' and wrapper.poll() is not None:
                            raise AssertionError('Mağaza başlatıcısı beklenmedik biçimde kapandı; store-native.log dosyasına bakın.')
                    if phase['name'] == 'waiting-window':
                        windows = monitor.windows()
                        if not windows:
                            return GLib.SOURCE_CONTINUE
                        assert has_owner()
                        phase['window'] = windows[0]
                        native = GdkX11.X11Window.foreign_new_for_display(Gdk.Display.get_default(), windows[0])
                        if native:
                            image = Gdk.pixbuf_get_from_window(native, 0, 0, native.get_width(), native.get_height())
                            if image:
                                image.savev(str(args.output / 'store-native.png'), 'png', [], [])
                        monitor.connection.create_resource_object('window', windows[0]).iconify(monitor.connection.get_default_screen())
                        monitor.connection.flush()
                        phase['name'], phase['check_after'] = 'minimized', phase['ticks'] + 15
                    elif phase['name'] == 'minimized' and phase['ticks'] >= phase['check_after']:
                        assert has_owner() and wrapper.poll() is None
                        assert phase['window'] in monitor.windows(), 'Küçültülen pencere yanlışlıkla kapalı sayıldı.'
                        report['minimize_preserved'] = True
                        monitor.connection.create_resource_object('window', phase['window']).map()
                        monitor.connection.flush()
                        phase['name'], phase['check_after'] = 'restored', phase['ticks'] + 8
                    elif phase['name'] == 'restored' and phase['ticks'] >= phase['check_after']:
                        connection = monitor.connection
                        request = event.ClientMessage(window=phase['window'],
                            client_type=connection.intern_atom('_NET_CLOSE_WINDOW'), data=(32, [X.CurrentTime, 1, 0, 0, 0]))
                        monitor.root.send_event(request, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
                        connection.flush()
                        phase['name'] = 'closed-by-window-manager'
                    elif phase['name'] == 'closed-by-window-manager':
                        clients = monitor.root.get_full_property(monitor.clients, X.AnyPropertyType)
                        controls = []
                        for identifier in clients.value:
                            window = monitor.connection.create_resource_object('window', int(identifier))
                            try:
                                identity = window.get_full_property(monitor.application, X.AnyPropertyType)
                                if identity is not None and bytes(identity.value).rstrip(b'\0') == b'org.oguzdows.Magaza':
                                    controls.append(int(identifier))
                            except Exception:
                                continue
                        if not controls:
                            return GLib.SOURCE_CONTINUE
                        assert has_owner() and wrapper.poll() is None
                        report['normal_close_requires_explicit_completion'] = True
                        native = GdkX11.X11Window.foreign_new_for_display(Gdk.Display.get_default(), controls[0])
                        image = Gdk.pixbuf_get_from_window(native, 0, 0, native.get_width(), native.get_height())
                        if image:
                            image.savev(str(args.output / 'store-completion-consent.png'), 'png', [], [])
                        # İşlem bulunmayan testte açık kullanıcı komutunun gerçek
                        # uzak Gtk.Application aktarımını da doğrula.
                        subprocess.run(['/usr/bin/python3', '-I', str(ROOT / 'system/usr/lib/oguzdows/store.py'), '--quit'],
                            stdout=shop_log, stderr=subprocess.STDOUT, check=True, timeout=15)
                        phase['name'] = 'exit-requested'
                    elif phase['name'] == 'exit-requested' and wrapper.poll() is not None and not has_owner():
                        assert wrapper.returncode == 0
                        report.update(explicit_exit_completed=True, dbus_owner_after_close=False, wrapper_after_close=False)
                        loop.quit()
                        return GLib.SOURCE_REMOVE
                except Exception as error:
                    errors.append(str(error))
                    loop.quit()
                    return GLib.SOURCE_REMOVE
                return GLib.SOURCE_CONTINUE
            GLib.timeout_add(200, tick)
            try:
                loop.run()
            finally:
                # Başarısız UI testi bile native mağazayı kendi güvenli çıkış
                # komutuyla kapatır; testte hiçbir paket işlemi başlatılmamıştır.
                if wrapper and wrapper.poll() is None:
                    try:
                        subprocess.run(['/usr/bin/python3', '-I', str(ROOT / 'system/usr/lib/oguzdows/store.py'), '--quit'],
                            stdout=shop_log, stderr=subprocess.STDOUT, check=False, timeout=30)
                        wrapper.wait(timeout=30)
                    except (OSError, subprocess.SubprocessError) as error:
                        errors.append('Test temizliği: ' + str(error))
                if monitor:
                    monitor.close()
                wm.terminate()
                wm.wait(timeout=10)
    report['errors'] = errors
    (args.output / 'store-native.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    if errors:
        details = '\n'.join((args.output / name).read_text(errors='replace')[-1800:]
                            for name in ('store-native.log', 'store-xfwm.log'))
        raise AssertionError('\n'.join(errors) + '\nGerçek mağaza günlükleri:\n' + details)
    print('Gerçek mağaza küçültülünce açık kaldı; pencere kapatmak iş iptal etmedi. Açık tam çıkıştan sonra native süreç / D-Bus sahibi kalmadı. Paket kurulmadı.')


if __name__ == '__main__':
    main()

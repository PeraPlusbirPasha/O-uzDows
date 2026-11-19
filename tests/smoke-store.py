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
from Xlib import X, Xutil
from Xlib.protocol import event
from support import ROOT, load
from x11_smoke import request_minimize


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
              'consent_preanswered_for_lifecycle_test': True, 'private_system_bus_without_services': True,
              'gnome_software_version': subprocess.check_output(['/usr/bin/gnome-software', '--version'], text=True).strip()}
    lifecycle = load('native_store_lifecycle', 'system/usr/lib/oguzdows/store_lifecycle.py')
    with tempfile.TemporaryDirectory(prefix='oguzdows-store-native-', ignore_cleanup_errors=True) as directory:
        os.environ.update(XDG_CONFIG_HOME=directory, XDG_STATE_HOME=directory, XDG_DATA_HOME=directory,
                          XDG_CACHE_HOME=directory, XDG_RUNTIME_DIR=directory, GSETTINGS_BACKEND='keyfile',
                          GSK_RENDERER='cairo', GDK_DISABLE='gl,vulkan', GDK_BACKEND='x11',
                          GTK_A11Y='none', MESA_SHADER_CACHE_DISABLE='true', GS_DEBUG='1', OGUZDOWS_STORE_DEBUG='1',
                          GNOME_SOFTWARE_PLUGINS_ALLOWLIST='appstream,flatpak,icons,key-colors,provenance,provenance-license')
        # Konteynerde systemd/system-bus yoktur. Yalnızca bu testin kendi
        # UNIX soketi; hiçbir gerçek sistem servisini/paket yöneticisini açmaz.
        system_socket = Path(directory) / 'system-bus'
        os.environ['DBUS_SYSTEM_BUS_ADDRESS'] = 'unix:path=' + str(system_socket)
        bus_config = Path(directory) / 'private-system-bus.conf'
        bus_config.write_text('<busconfig><type>system</type><listen>' + os.environ['DBUS_SYSTEM_BUS_ADDRESS']
            + '</listen><auth>EXTERNAL</auth><policy context="default"><allow user="*"/>'
              '<allow own="*"/><allow send_destination="*"/><allow receive_sender="*"/>'
              '</policy></busconfig>\n')
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
        with (args.output / 'store-xfwm.log').open('w') as wm_log, (args.output / 'store-native.log').open('w') as shop_log, (args.output / 'store-system-bus.log').open('w') as bus_log:
            system_bus = subprocess.Popen(['dbus-daemon', '--nofork', '--config-file=' + str(bus_config)], stdout=bus_log, stderr=subprocess.STDOUT)
            wm = subprocess.Popen(['xfwm4', '--compositor=off'], stdout=wm_log, stderr=subprocess.STDOUT)
            wrapper, monitor = None, None
            phase = {'name': 'waiting-wm', 'ticks': 0}
            loop = GLib.MainLoop()
            def diagnose():
                snapshot = {'native_dbus_owner': has_owner(), 'wrapper_exit': wrapper.poll() if wrapper else None,
                            'wm_exit': wm.poll(), 'system_bus_exit': system_bus.poll()}
                for name, command in (('root_properties', ['xprop', '-root', '_NET_CLIENT_LIST', '_NET_SUPPORTING_WM_CHECK']),
                                      ('window_tree', ['xwininfo', '-root', '-tree'])):
                    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=5)
                    snapshot[name] = (result.stdout + result.stderr)[-2200:]
                if monitor:
                    clients = monitor.root.get_full_property(monitor.clients, X.AnyPropertyType)
                    snapshot['managed_windows'] = []
                    for identifier in (clients.value if clients is not None else ()):
                        result = subprocess.run(['xprop', '-id', str(int(identifier)), '_GTK_APPLICATION_ID',
                                                 'WM_CLASS', 'WM_STATE', '_NET_WM_PID'],
                                                capture_output=True, text=True, check=False, timeout=5)
                        snapshot['managed_windows'].append(result.stdout[-1200:])
                snapshot['native_processes'] = []
                for entry in Path('/proc').iterdir():
                    if not entry.name.isdigit():
                        continue
                    try:
                        if (entry / 'comm').read_text().strip() == 'gnome-software':
                            snapshot['native_processes'].append({'pid': int(entry.name),
                                'wchan': (entry / 'wchan').read_text().strip()})
                    except OSError:
                        continue
                report['failure_snapshot'] = snapshot
                # Sadece başarısız, paket işi yapmayan CI testinde soğuk
                # başlangıcı tekrarla. Bu bir başarılı ömür kanıtı sayılmaz.
                if not snapshot['native_dbus_owner'] and Path('/usr/bin/gdb').is_file():
                    with (args.output / 'store-gdb.log').open('w') as trace:
                        try:
                            result = subprocess.run(['/usr/bin/gdb', '--batch', '--return-child-result',
                                '-ex', 'run', '-ex', 'thread apply all bt', '--args',
                                '/usr/bin/gnome-software', '--mode=updates'],
                                stdout=trace, stderr=subprocess.STDOUT, timeout=25, check=False)
                            report['failure_reproduction_gdb_exit'] = result.returncode
                        except subprocess.TimeoutExpired:
                            report['failure_reproduction_gdb_timeout'] = True
            def tick():
                nonlocal wrapper, monitor
                try:
                    phase['ticks'] += 1
                    if phase['ticks'] > 600:
                        raise AssertionError('Gerçek mağaza ömür testi 120 saniyeyi aştı: ' + phase['name'] + ' · ' + phase.get('last_wm_error', ''))
                    if phase['name'] == 'waiting-wm':
                        if system_bus.poll() is not None:
                            raise AssertionError('Testin özel system-bus süreci açılamadı.')
                        if not system_socket.exists():
                            return GLib.SOURCE_CONTINUE
                        try:
                            if monitor is None:
                                monitor = lifecycle.X11Windows()
                            monitor.windows()
                        except Exception as error:
                            phase['last_wm_error'] = str(error)
                            return GLib.SOURCE_CONTINUE
                        phase.pop('last_wm_error', None)
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
                        request_minimize(monitor, windows[0])
                        phase['name'], phase['check_after'] = 'minimized', phase['ticks'] + 15
                    elif phase['name'] == 'minimized' and phase['ticks'] >= phase['check_after']:
                        assert has_owner() and wrapper.poll() is None
                        window = monitor.connection.create_resource_object('window', phase['window'])
                        state = window.get_wm_state()
                        assert state is not None and state.state == Xutil.IconicState, 'Xfwm küçültme isteğini uygulamadı.'
                        assert window.get_attributes().map_state != X.IsViewable, 'Küçültülen pencere hâlâ görünür.'
                        assert phase['window'] in monitor.windows(), 'Küçültülen pencere yanlışlıkla kapalı sayıldı.'
                        report['minimize_preserved'] = True
                        window.map()
                        monitor.connection.flush()
                        phase['name'], phase['check_after'] = 'restored', phase['ticks'] + 8
                    elif phase['name'] == 'restored' and phase['ticks'] >= phase['check_after']:
                        connection = monitor.connection
                        window = connection.create_resource_object('window', phase['window'])
                        state = window.get_wm_state()
                        assert state is not None and state.state == Xutil.NormalState, 'Xfwm pencereyi geri getirmedi.'
                        assert window.get_attributes().map_state == X.IsViewable, 'Geri getirilen pencere görünür değil.'
                        report['restore_verified'] = True
                        request = event.ClientMessage(window=phase['window'],
                            client_type=connection.intern_atom('_NET_CLOSE_WINDOW'), data=(32, [X.CurrentTime, 1, 0, 0, 0]))
                        monitor.root.send_event(request, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
                        connection.flush()
                        phase['name'] = 'closed-by-window-manager'
                    elif phase['name'] == 'closed-by-window-manager':
                        clients = monitor.root.get_full_property(monitor.clients, X.AnyPropertyType)
                        controls = []
                        for identifier in (clients.value if clients is not None else ()):
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
                    try:
                        diagnose()
                    except Exception as diagnostic_error:
                        report['diagnostic_error'] = str(diagnostic_error)
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
                system_bus.terminate()
                system_bus.wait(timeout=10)
    report['phase'] = phase['name']
    report['errors'] = errors
    (args.output / 'store-native.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    if errors:
        print('::notice title=Mağaza hata anı::' + json.dumps(report, ensure_ascii=False).replace('%', '%25'), flush=True)
        for name in ('store-native.log', 'store-gdb.log'):
            path = args.output / name
            if not path.exists():
                continue
            tail = path.read_text(errors='replace')[-6000:]
            for index in range(0, len(tail), 3000):
                print('::notice title=Mağaza ' + name + ' ' + str(index // 3000 + 1) + '::'
                      + tail[index:index + 3000].replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A'), flush=True)
        details = '\n'.join((args.output / name).read_text(errors='replace')[-1800:]
                            for name in ('store-system-bus.log', 'store-xfwm.log', 'store-native.log'))
        raise AssertionError('\n'.join(errors) + '\nGerçek mağaza günlükleri:\n' + details)
    print('::notice title=Mağaza gerçek süreç ömrü::' + json.dumps(report, ensure_ascii=False))
    print('Gerçek mağaza küçültülünce açık kaldı; pencere kapatmak iş iptal etmedi. Açık tam çıkıştan sonra native süreç / D-Bus sahibi kalmadı. Paket kurulmadı.')


if __name__ == '__main__':
    main()

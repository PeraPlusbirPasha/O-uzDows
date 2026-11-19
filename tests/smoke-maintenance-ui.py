#!/usr/bin/env python3
"""Gerçek GTK + xfconf; ağ / pkexec / paket kurulumunu TAKLİT eder."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GLib, Gtk
from support import load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('test-results'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if not Gtk.init_check([])[0]:
        raise RuntimeError('Xvfb gerekli.')
    errors = []
    original_hook = sys.excepthook
    def error_hook(kind, value, trace):
        errors.append(str(value))
        original_hook(kind, value, trace)
    sys.excepthook = error_hook
    with tempfile.TemporaryDirectory(prefix='oguzdows-tools-ui-') as directory:
        os.environ.update(XDG_CONFIG_HOME=directory, XDG_STATE_HOME=directory, OGUZDOWS_TESTING='1')
        Gtk.Settings.get_default().set_property('gtk-theme-name', 'OguzDows')
        profiles = load('tools_smoke_profiles', 'system/usr/lib/oguzdows/profiles.py')
        # Gerçek komut biçimi ve D-Bus xfconf daemonu: sadece geçici kullanıcı
        # dizininde; bir masaüstü kurmaz ve sistem ayarlarını değiştirmez.
        for name in profiles.PROFILES:
            profiles.apply(name)
            for channel, path, _kind, expected in profiles.settings(name):
                result = subprocess.run(['xfconf-query', '-c', channel, '-p', path], capture_output=True, text=True, check=True)
                assert result.stdout.strip() == expected, (name, path, result.stdout)
        profiles.restore()
        updater = load('tools_smoke_updater', 'system/usr/lib/oguzdows/updater.py')
        culture = load('tools_smoke_culture', 'system/usr/lib/oguzdows/culture.py')
        store = load('tools_smoke_store', 'system/usr/lib/oguzdows/store.py')
        update = updater.Updater()
        tools = culture.Culture()
        shop = store.Store(force_setup=True)
        apps = (update, tools, shop)
        for app in apps:
            app.register(None)
            app.activate()
        assert not update.busy and update.plan is None and not update.apply_button.get_sensitive()
        assert tools.timer is None and not tools.busy
        assert not shop.busy
        calls = []
        plan = {'request': 'upgrade', 'token': 'a' * 64, 'changes': [{'package': 'firmware-realtek', 'version': '2'}],
                'note': 'Güvenli test planı; kurulum yapılmaz.', 'detail': 'Inst firmware-realtek (2 test [all])'}
        def fake_run(command, **_kwargs):
            assert command[:2] == updater.HELPER, command
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, json.dumps(plan), '')
        def no_spawn(*_args, **_kwargs):
            raise AssertionError('Bu GTK testi gerçek program / yetkili yardımcı başlatamaz.')
        loop = GLib.MainLoop()
        def screenshot(app, name):
            app.window.present()
            for _ in range(30):
                if not Gtk.events_pending():
                    break
                Gtk.main_iteration_do(False)
            native = app.window.get_window()
            native.process_updates(True)
            width, height = app.window.get_size()
            image = Gdk.pixbuf_get_from_window(native, 0, 0, width, height)
            assert image is not None
            image.savev(str(args.output / name), 'png', [], [])
        def start():
            try:
                assert not calls, 'Pencereyi açmak APT / ağ çalıştırmamalı'
                update.show_plan(plan)
                assert update.apply_button.get_sensitive()
                update.request.set_active_id('desktop:kde')
                assert update.plan is None and not update.apply_button.get_sensitive()
                update.show_plan(plan)
                update.confirm = lambda *_: False
                update.apply()
                assert not calls, 'Onay iptalinde paket çağrısı yapılamaz'
                update.show_drivers({'drivers': [{'id': 'realtek', 'packages': ['firmware-realtek'], 'installed': True, 'unbound': False}], 'note': 'Aygıt raporu · test'})
                assert update.drivers.get_active_id() == 'realtek'
                update.stack.set_visible_child_name('drivers')
                screenshot(update, 'updater-drivers.png')
                update.stack.set_visible_child_name('sources')
                update.memory()
                screenshot(update, 'updater-sources.png')
                update.stack.set_visible_child_name('updates')
                screenshot(update, 'updater-plan.png')
                update.window.resize(600, 440)
                tools.start_timer(5)
                assert tools.timer is not None
                tools.stop_timer()
                assert tools.timer is None
                tools.editor.get_buffer().set_text('istanbul ısparta')
                tools.transform(culture.core.turkish_upper)
                buffer = tools.editor.get_buffer()
                assert buffer.get_text(*buffer.get_bounds(), True) == 'İSTANBUL ISPARTA'
                for name in ('tea', 'text', 'backup', 'share'):
                    tools.stack.set_visible_child_name(name)
                    screenshot(tools, 'imece-' + name + '.png')
                screenshot(shop, 'store-consent.png')
                update.backend(['plan', 'upgrade'], update.show_plan)
                assert update.busy and update.closing()
                GLib.timeout_add(500, finish)
            except Exception as error:
                errors.append(str(error))
                loop.quit()
            return GLib.SOURCE_REMOVE
        def finish():
            if update.busy:
                return GLib.SOURCE_CONTINUE
            try:
                assert len(calls) == 1 and calls[0][2:] == ['plan', 'upgrade']
                assert update.apply_button.get_sensitive()
                screenshot(update, 'updater-small.png')
                update.finished(None, None, 'Yönetici onayı verilmedi · güvenli hata testi')
                assert not update.apply_button.get_sensitive()
                assert update.stack.get_visible_child_name() == 'updates'
                screenshot(update, 'updater-auth-cancelled.png')
                assert not {'PIL', 'cairo', 'rifki_pet', 'rifki_scene'}.intersection(sys.modules)
                for app in apps:
                    app.window.destroy()
                    app.quit()
            except Exception as error:
                errors.append(str(error))
            finally:
                loop.quit()
            return GLib.SOURCE_REMOVE
        def timeout():
            errors.append('GTK bakım testi 30 saniyede tamamlanmadı.')
            loop.quit()
            return GLib.SOURCE_REMOVE
        with patch.object(updater.subprocess, 'run', side_effect=fake_run), patch.object(updater.subprocess, 'Popen', side_effect=no_spawn):
            GLib.timeout_add(350, start)
            GLib.timeout_add_seconds(30, timeout)
            loop.run()
        (args.output / 'maintenance-ui.json').write_text(json.dumps({'gtk': True, 'native_xfconf_profiles': 5,
            'apt_mocked': True, 'package_installation_tested': False, 'network_used': False, 'errors': errors}, ensure_ascii=False, indent=2) + '\n')
    if errors:
        raise AssertionError('\n'.join(errors))
    print('Bakım GTK, beş gerçek xfconf profili, dört İmece paneli ve onay iptali doğrulandı. Paket kurulmadı.')


if __name__ == '__main__':
    main()

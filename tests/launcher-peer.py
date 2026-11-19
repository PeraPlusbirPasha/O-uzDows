#!/usr/bin/env python3
"""D-Bus smoke için ayrı GTK süreci; kurucu yerine güvenli bir bekleyici.

Komutlar yalnızca üst test sürecinin stdin borusundan gelir. Gerçek yetki,
kurucu, paket yöneticisi veya disk aracı çağrılmaz.
"""
import sys
import threading

import gi

gi.require_version('Gtk','3.0')
from gi.repository import GLib

from support import load


def main():
    release=threading.Event()
    module=load('light_launcher_peer','system/usr/lib/oguzdows/install_launcher.py')
    def fake_installer():
        release.wait(15)
        return 126,'','Deneme: yönetici onayı iptal edildi.'
    module.run_installer=fake_installer
    app=module.Installer()
    if not app.register(None):
        raise RuntimeError('Test başlatıcısı D-Bus’a kaydedilemedi')
    app.activate()
    loop=GLib.MainLoop()
    def close():
        app.set_busy(False)
        release.set()
        app.window.destroy()
        loop.quit()
        return GLib.SOURCE_REMOVE
    def command(_source,condition):
        if condition & (GLib.IO_HUP|GLib.IO_ERR):
            return close()
        word=sys.stdin.readline().strip()
        if word=='finish':
            release.set()
        elif word=='busy':
            app.set_busy(True)
        elif word in ('quit',''):
            return close()
        else:
            raise RuntimeError('Bilinmeyen test komutu')
        return GLib.SOURCE_CONTINUE
    GLib.io_add_watch(sys.stdin,GLib.IO_IN|GLib.IO_HUP|GLib.IO_ERR,command)
    GLib.timeout_add(15000,close)
    loop.run()
    release.set()
    return 0


if __name__=='__main__':
    raise SystemExit(main())

"""Hafif başlatıcının sonuç / yetki sınırları; GTK veya gerçek kurucu açılmaz."""
import json
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from support import load

# Birim testleri GI paketine veya görüntü sunucusuna bağımlı değildir.
gi=SimpleNamespace(require_version=lambda *_:None)
gtk=SimpleNamespace(Application=object,ApplicationWindow=object,Image=object)
with patch.dict(sys.modules,{'gi':gi,'gi.repository':SimpleNamespace(Gtk=gtk,GLib=SimpleNamespace(SOURCE_REMOVE=False),Gio=object,GdkPixbuf=object)}):
    launcher=load('light_launcher_unit','system/usr/lib/oguzdows/install_launcher.py')
    rifki=load('light_rifki_unit','system/usr/lib/oguzdows/rifki.py')


class LauncherTests(unittest.TestCase):
    def make_window(self):
        app=launcher.Installer.__new__(launcher.Installer)
        app.busy=True
        for name in ('title','detail','log','close_button','restart','window','activity'):
            setattr(app,name,Mock())
        app.set_busy=Mock(side_effect=lambda value:setattr(app,'busy',bool(value)))
        return app

    def test_only_the_existing_fixed_polkit_helper_is_started(self):
        with patch.object(launcher.subprocess,'run',return_value=subprocess.CompletedProcess([],126,'','izin verilmedi')) as child:
            self.assertEqual(launcher.run_installer(),(126,'','izin verilmedi'))
        self.assertEqual(child.call_args.args,(['/usr/bin/pkexec','/usr/local/sbin/oguzdows-installer'],))
        self.assertNotIn('shell',child.call_args.kwargs)

    def test_missing_helper_is_a_visible_failure_not_a_gui_exception(self):
        with patch.object(launcher.subprocess,'run',side_effect=OSError('bulunamadı')):
            code,output,detail=launcher.run_installer()
        self.assertEqual((code,output),(1,''))
        self.assertIn('bulunamadı',detail)

    def test_every_non_success_result_keeps_reboot_hidden(self):
        for code,output in ((0,''),(1,''),(126,''),(127,''),(10,''),(0,'OGUZDOWS_RESULT_JSON={bad}')):
            with self.subTest(code=code,output=output):
                app=self.make_window()
                app.finished(code,output,'görünür ayrıntı')
                self.assertFalse(app.busy)
                self.assertNotEqual(app.data['outcome'],'success')
                app.restart.set_visible.assert_called_once_with(False)
                app.log.get_buffer.return_value.set_text.assert_called_once_with('görünür ayrıntı')
                app.close_button.set_sensitive.assert_called_once_with(True)
                app.window.present.assert_called_once()

    def test_success_and_optional_warning_are_distinct_without_auto_reboot(self):
        for optional in ([],[{'action':'broadcom','status':'skipped','message':'uyumlu aygıt yok'}]):
            app=self.make_window()
            data={'version':1,'session':'a'*32,'complete':True,'outcome':'success','optional_drivers':optional}
            with patch.object(launcher.subprocess,'Popen') as reboot:
                app.finished(0,launcher.install_status.PREFIX+json.dumps(data),'')
                reboot.assert_not_called()
            app.restart.set_visible.assert_called_once_with(True)
            title=app.title.set_text.call_args.args[0]
            self.assertEqual('uyarı' in title,bool(optional))
            self.assertIn('ayrıca',app.detail.set_text.call_args.args[0])

    def test_an_unverified_result_cannot_reboot_even_if_callback_is_invoked(self):
        for data in ({},{'outcome':'success','complete':False},{'outcome':'failed','complete':True}):
            app=self.make_window()
            app.data=data
            with patch.object(launcher.subprocess,'Popen') as reboot:
                app.reboot()
                reboot.assert_not_called()

    def test_result_audio_never_announces_success_for_a_partial_failed_or_missing_result(self):
        for data in ({},{'outcome':'unknown'},{'outcome':'incomplete'},{'outcome':'failed'}, {'outcome':'success','complete':False}):
            self.assertEqual(rifki.Companion.result_cue(data),'failure')
        self.assertEqual(rifki.Companion.result_cue({'outcome':'cancelled'}),'cancelled')
        self.assertEqual(rifki.Companion.result_cue({'outcome':'success','complete':True}),'success')
        self.assertEqual(rifki.Companion.result_cue({'outcome':'success','complete':True,'optional_drivers':[{'status':'failed'}]}),'warning')

    def test_installation_freezes_motion_and_stops_playback_without_creating_a_timer(self):
        companion=SimpleNamespace(installing=False,avatar=Mock(),speaker=Mock(),last_stage='old')
        rifki.Companion.set_installing(companion,True)
        self.assertTrue(companion.installing)
        self.assertTrue(companion.avatar.frozen)
        companion.speaker.stop.assert_called_once_with()
        rifki.Companion.set_installing(companion,False)
        self.assertFalse(companion.installing)
        self.assertFalse(companion.avatar.frozen)
        self.assertIsNone(companion.last_stage)

    def test_protocol_output_is_unchanged_and_error_detail_is_bounded(self):
        output=launcher.install_status.PREFIX+'{"outcome":"failed"}'
        with patch.object(launcher.subprocess,'run',return_value=subprocess.CompletedProcess([],1,output,'x'*7000)):
            code,actual,detail=launcher.run_installer()
        self.assertEqual((code,actual),(1,output))
        self.assertEqual(detail,'x'*5000)


if __name__=='__main__':
    unittest.main()

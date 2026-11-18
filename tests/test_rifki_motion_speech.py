"""Hareket / ses testleri; pencere veya gerçek ses aygıtı açılmaz."""
import json
import math
import os
import shutil
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from PIL import ImageChops

from support import ROOT, load

motion=load('rifki_motion_test','system/usr/lib/oguzdows/rifki_motion.py')
scene_module=load('rifki_scene_test','system/usr/lib/oguzdows/rifki_scene.py')
speech=load('rifki_speech_test','system/usr/lib/oguzdows/rifki_speech.py')
model=load('rifki_model_more_tests','system/usr/lib/oguzdows/rifki_model.py')
dialogue=load('rifki_dialogue_tests','system/usr/lib/oguzdows/rifki_dialogue.py')
ASSETS=ROOT/'system/usr/share/oguzdows/rifki'


def silent_wav(path):
    with wave.open(str(path),'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(22050)
        out.writeframes(b'\0\0'*2205)


class MotionTests(unittest.TestCase):
    def test_jump_starts_and_lands_exactly_and_has_an_arc(self):
        a,b=(0.,0.),(100.,10.)
        self.assertEqual(motion.jump_path(a,b,0),a)
        self.assertEqual(motion.jump_path(a,b,1),b)
        self.assertLess(motion.jump_path(a,b,.5)[1],0)
        self.assertEqual(motion.jump_path(a,b,99),b)

    def test_perch_respects_monitor_bounds_titlebar_controls_and_no_space(self):
        for work in (motion.Rect(0,0,1024,768),motion.Rect(-1280,0,1280,1024)):
            result=motion.perch_position(motion.Rect(work.x+90,210,800,520),work)
            self.assertIsNotNone(result)
            self.assertGreaterEqual(result.x,work.x)
            self.assertGreaterEqual(result.y,work.y)
            self.assertLessEqual(result.x+result.width,work.x+work.width)
            self.assertLess(result.x+result.width,work.x+90+800-80)
        self.assertIsNone(motion.perch_position(motion.Rect(0,0,1024,768),motion.Rect(0,0,1024,768)))

    def test_pause_freezes_and_resumes_without_time_jump(self):
        behavior=motion.Behaviour(0)
        behavior.choose('tea',1)
        behavior.set_paused(True,4)
        self.assertEqual(behavior.tick(50),('tea',3))
        behavior.set_paused(False,60)
        self.assertEqual(behavior.tick(61),('tea',4))
        with self.assertRaises(ValueError):
            behavior.choose('execute-command',100)

    def test_reduced_motion_is_not_automatic_and_states_are_finite(self):
        behavior=motion.Behaviour(0,reduced=True)
        self.assertFalse(behavior.automatic)
        self.assertEqual(behavior.tick(1000)[0],'perch')
        for action in motion.ACTIONS:
            for t in (0.,.1,1.,4.,9.,20.,10000.):
                state=motion.pose_state(action,t)
                for value in (state['x'],state['y'],state['scale'],state['paw'],state['tail'],state['breathe']):
                    self.assertTrue(math.isfinite(value))
                self.assertGreater(state['scale'],0)

    def test_all_real_rendered_behaviours_differ_and_keep_alpha(self):
        renderer=scene_module.Scene(ASSETS/'rig')
        outputs=[]
        for action,t in (('perch',1),('jump',1),('tail',1),('feather',3),('tea',9)):
            first=renderer.render(action,t,.4)
            second=renderer.render(action,t+.6,.4)
            self.assertEqual(first.size,(300,224))
            self.assertEqual(first.mode,'RGBA')
            self.assertEqual(first.getpixel((0,0))[3],0)
            self.assertIsNotNone(ImageChops.difference(first,second).getbbox(),action)
            outputs.append(first.tobytes())
        self.assertEqual(len(set(outputs)),len(outputs))
        # Kaynak dosyalar kare başına yeniden açılmaz; sınırlı önbellek kullanılır.
        with patch.object(scene_module.Image,'open',side_effect=AssertionError('Frame IO')):
            for i in range(30):
                renderer.render('tea',i/20)
        self.assertLessEqual(len(renderer.cache),24)

    def test_motion_questions_do_not_become_system_commands(self):
        for question,expected in (('zıpla','jump'),('kuyruğunu salla','tail'),('tüy topuyla oyna','feather'),('çay demle','tea')):
            answer=model.reply(question)
            self.assertEqual(answer['motion'],expected)
            self.assertIsNone(answer['action'])
        self.assertEqual(model.reply('sudo rm -rf /dev/test')['action'],'boot-report')


class SpeechTests(unittest.TestCase):
    def test_ready_audio_is_matched_by_the_entire_text_never_by_a_generic_success_tag(self):
        mapping=json.loads((ASSETS/'speech.json').read_text())
        self.assertEqual(len(mapping),10)
        for text in (dialogue.HELLO,*[dialogue.PANELS[name] for name in ('welcome','hardware','wallpapers')],*[model.reply(topic)['text'] for topic in ('boot','internet','sürücü','duvar','pil','kurulum')]):
            self.assertIsNotNone(speech.ready_clip(text,ASSETS),text)
        self.assertIsNone(speech.ready_clip('Kurulum başarısız oldu.',ASSETS))
        self.assertIsNone(speech.ready_clip('OğuzDows başarıyla kuruldu. Değişen disk adı.',ASSETS))

    def test_arbitrary_text_is_stdin_not_a_shell_or_a_speech_option(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)/'voice'
            calls=[]
            def run(command,**kwargs):
                calls.append((command,kwargs))
                silent_wav(Path(command[command.index('-w')+1]))
                return subprocess.CompletedProcess(command,0)
            text='--option; $(touch /tmp/never) Türkçe yanıt'
            with patch.object(speech.subprocess,'run',side_effect=run):
                path=speech.synthesize(text,directory,engine='/usr/bin/espeak-ng')
                self.assertEqual(len(calls),1)
                self.assertNotIn(text,calls[0][0])
                self.assertEqual(calls[0][1]['input'],text)
                self.assertEqual(calls[0][0][-1],'--stdin')
                self.assertIn('tr',calls[0][0])
                self.assertEqual(path.stat().st_mode & 0o777,0o600)
                self.assertEqual(directory.stat().st_mode & 0o777,0o700)
                self.assertEqual(speech.synthesize(text,directory),path)
                self.assertEqual(len(calls),1)

    def test_failed_synthesis_does_not_publish_a_broken_audio_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)/'voice'
            with patch.object(speech.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'fake')):
                with self.assertRaises(subprocess.CalledProcessError):
                    speech.synthesize('hata',directory,engine='/usr/bin/espeak-ng')
            self.assertEqual(list(directory.iterdir()),[])

    def test_stale_synthesis_after_new_message_or_mute_cannot_play(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ,{'XDG_CONFIG_HOME':temporary}):
            speaker=speech.Speaker(lambda f,*a:f(*a))
            generation=speaker.generation
            speaker.stop()
            with patch.object(speech.subprocess,'Popen') as popen:
                speaker.play_ready(generation,Path('/unused.wav'),[])
                popen.assert_not_called()
            speaker.set_enabled(False)
            self.assertFalse(speaker.enabled)
            self.assertFalse(json.loads(speaker.preference.read_text())['speech'])
            speaker.close()

    @unittest.skipUnless(shutil.which('espeak-ng'),'Türkçe ses motoru yerelde yok; iki tabanlı CI bunu gerçekten çalıştırır')
    def test_real_offline_turkish_engine_generates_all_panel_and_dynamic_result_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            for text in (*dialogue.PANELS.values(),'Kurulum tamamlanamadı. Ek sürücü uyarısı var.'):
                path=speech.synthesize(text,Path(temporary)/'voice')
                with wave.open(str(path),'rb') as audio:
                    self.assertGreater(audio.getnframes(),audio.getframerate())
                self.assertTrue(any(v>0 for v in speech.envelope(path)))


if __name__=='__main__':
    unittest.main()

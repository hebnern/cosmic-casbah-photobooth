import kivy.core.camera
import camera_android
kivy.core.camera.Camera = camera_android.CameraAndroid

from kivy.logger import Logger
import logging
Logger.setLevel(logging.INFO)

import os
import time
import datetime
import re

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.camera import Camera
from kivy.utils import platform
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.config import Config
from kivy.base import EventLoop
from kivy.graphics.texture import Texture

camera_sound = SoundLoader.load('camera_click.wav')
countdown_sound = SoundLoader.load('countdown_blip.wav')

from kivy.core.window import Window
Window.softinput_mode = 'below_target'

output_path = '/sdcard/Pictures/photobooth'
if not os.path.exists(output_path):
    os.makedirs(output_path)

cur_session_id = None
cur_img_id = None

class StartScreen(Screen):
    def on_enter(self):
        global cur_session_id, cur_img_id
        now = datetime.datetime.now()
        cur_session_id = time.mktime(now.timetuple())
        cur_img_id = 0

class CameraScreen(Screen):
    _states = [
        { 'msg': "Ready?", 'duration': 2.0, 'action': 'play' },
        { 'msg': "Let's go!", 'duration': 2.0 },

        { 'msg': '3', 'duration': 1.5, 'sound': countdown_sound },
        { 'msg': '2', 'duration': 1.5, 'sound': countdown_sound },
        { 'msg': '1', 'duration': 1.5, 'sound': countdown_sound },
        { 'msg': '', 'duration': 1.0, 'sound': camera_sound, 'action': 'capture_image' },
        { 'msg': "Hot damn, that looks good!\nLet's take another.", 'duration': 3.0 },

        { 'msg': '3', 'duration': 1.5, 'sound': countdown_sound, 'action': 'play' },
        { 'msg': '2', 'duration': 1.5, 'sound': countdown_sound },
        { 'msg': '1', 'duration': 1.5, 'sound': countdown_sound },
        { 'msg': '', 'duration': 1.0, 'sound': camera_sound, 'action': 'capture_image' },
        { 'msg': "Hells yes!\nHow about one more?", 'duration': 3.0 },

        { 'msg': '3', 'duration': 1.5, 'sound': countdown_sound, 'action': 'play' },
        { 'msg': '2', 'duration': 1.5, 'sound': countdown_sound },
        { 'msg': '1', 'duration': 1.5, 'sound': countdown_sound },
        { 'msg': '', 'duration': 1.0, 'sound': camera_sound, 'action': 'capture_image' },
        { 'msg': "Wowza!", 'duration': 3.0 },
        { 'action': 'done' },
    ]

    def on_pre_enter(self):
        viewport = self.ids['viewport']
        camera = self.ids['camera']
        viewport.texture = camera.texture

    def on_next_state(self, dt=None):
        state = CameraScreen._states[self.cur_state]

        msg = state.get('msg', '')
        self.ids['message'].text = msg

        action = state.get('action', None)
        if action == 'capture_image':
            self.capture()
        elif action == 'done':
            self.manager.current = 'email_entry'
        elif action == 'play':
            viewport = self.ids['viewport']
            camera = self.ids['camera']
            viewport.texture = camera.texture

        sound = state.get('sound', None)
        if sound:
            sound.play()

        duration = state.get('duration', None)
        if duration:
            Clock.schedule_once(self.on_next_state, duration)

        self.cur_state += 1

    def on_enter(self):
        self.cur_state = 0
        self.on_next_state()

    def capture(self):
        viewport = self.ids['viewport']
        camera = self.ids['camera']

        ct = camera.texture
        snapshot = Texture.create(
            size=ct.size[:2],
            colorfmt=ct.colorfmt,
            bufferfmt=ct.bufferfmt
        )
        snapshot.blit_buffer(
            ct.pixels,
            colorfmt=ct.colorfmt,
            bufferfmt=ct.bufferfmt
        )
        # snapshot.flip_horizontal()
        # snapshot.flip_vertical()
        viewport.texture = snapshot

        camera._camera.take_picture(self.jpeg_cb)

    def jpeg_cb(self, data):
        global cur_session_id, cur_img_id
        output_file = '%s/%d_%d.jpg' % (output_path, cur_session_id, cur_img_id)
        with open(output_file, 'wb') as f:
            f.write(data)

        cur_img_id += 1

class EmailEntryScreen(Screen):
    def __init__(self, *args, **kwargs):
        super(EmailEntryScreen, self).__init__(*args, **kwargs)
        self._event = None
        self.ids['email'].bind(text=self.validate_email)
        self.ids['email'].bind(focus=self.on_email_focus_changed)
        self.ids['ok_btn'].bind(on_press=self.on_ok_btn)
        self.ids['cancel_btn'].bind(on_press=self.on_cancel_btn)

    def on_ok_btn(self, e):
        # write session
        email = self.ids['email'].text
        output_file = '%s/%d.txt' % (output_path, cur_session_id)
        with open(output_file, 'w') as f:
            f.write(email)

        app = App.get_running_app()
        app.root.transition.direction = 'left'
        app.root.current = 'thanks'

    def on_cancel_btn(self, e):
        app = App.get_running_app()
        app.root.transition.direction = 'left'
        app.root.current = 'thanks'

    def on_pre_enter(self):
        self.ids['email'].text = ''
        self.reset_timeout()

    def reset_timeout(self):
        def timeout_cb(dt):
            app = App.get_running_app()
            app.root.transition.direction = 'left'
            app.root.current = 'start'

        Clock.unschedule(timeout_cb)
        Clock.schedule_once(timeout_cb, 60)

    def on_email_focus_changed(self, email_input_widget, has_focus):
        if not has_focus:
            app = App.get_running_app()
            app.configure_android_app()

    def validate_email(self, email_input_widget, email_text):
        email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        self.ids['ok_btn'].disabled = re.match(email_regex, email_text) is None
        self.reset_timeout()

class ThanksScreen(Screen):
    def on_enter(self):
        def restart_cb(dt):
            app = App.get_running_app()
            app.root.transition.direction = 'left'
            app.root.current = 'start'

        Clock.schedule_once(restart_cb, 3)

class PhotoBoothApp(App):
    def build(self):
        self.configure_android_app()
        EventLoop.window.bind(on_keyboard=self.hook_keyboard)
        sm = ScreenManager()
        sm.add_widget(StartScreen(name='start'))
        sm.add_widget(CameraScreen(name='camera'))
        sm.add_widget(EmailEntryScreen(name='email_entry'))
        sm.add_widget(ThanksScreen(name='thanks'))
        return sm

    def hook_keyboard(self, window, key, *largs):
        if key == 27:
            return True

    def configure_android_app(self):
        if platform == 'android':
            def do_configure():
                from jnius import autoclass

                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                View = autoclass('android.view.View')
                Params = autoclass('android.view.WindowManager$LayoutParams')

                PythonActivity.mActivity.getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE |
                    View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION |
                    View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN |
                    View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
                    View.SYSTEM_UI_FLAG_FULLSCREEN |
                    View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                )
                PythonActivity.mActivity.getWindow().addFlags(Params.FLAG_KEEP_SCREEN_ON)
            from android.runnable import Runnable
            Runnable(do_configure)()

if __name__ == '__main__':
    PhotoBoothApp().run()

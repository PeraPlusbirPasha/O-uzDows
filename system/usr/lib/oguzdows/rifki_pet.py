"""Küçük, odak çalmayan ve tıklamaları geçiren X11 pencere kedisi.

Yalnızca rehber / Calamares penceresi izlenir. Başka uygulamalar okunmaz veya
hareket ettirilmez. Üstte yer yoksa kedi kendi oyun alanında kalır.
"""
from __future__ import annotations

import time

import cairo
import gi

gi.require_version('Gtk','3.0')
gi.require_version('Gdk','3.0')
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from rifki_motion import Behaviour, LABELS, Rect, perch_position
from rifki_scene import Scene


class PetView(Gtk.DrawingArea):
    def __init__(self, speaker=None, reduced=False, width=300, height=224, transparent=False):
        super().__init__()
        self.speaker=speaker
        self.transparent=transparent
        self.reduced=reduced
        self.behaviour=Behaviour(time.monotonic(),reduced)
        self.frame=None
        self.pixbuf=None
        self.scene=None
        self.last_frame=0.
        try:
            self.scene=Scene()
        except (OSError,ValueError,KeyError):
            pass
        self.set_size_request(width,height)
        self.connect('draw',self.paint)
        self.connect('destroy',self.closed)
        self.timer=GLib.timeout_add(125 if reduced else 42,self.tick)
        self.get_accessible().set_name('Rıfkı, konuşan ve hareket eden küçük Van kedisi')

    def choose(self, action):
        self.behaviour.choose(action,time.monotonic())
        self.tick()

    def tick(self):
        if not self.get_mapped() or self.scene is None:
            return GLib.SOURCE_CONTINUE
        now=time.monotonic()
        background=not self.transparent and not self.get_toplevel().is_active()
        if background and now-self.last_frame<.24:
            return GLib.SOURCE_CONTINUE
        self.last_frame=now
        action,t=self.behaviour.tick(now)
        width,height=self.get_allocated_width(),self.get_allocated_height()
        if width<2 or height<2:
            return GLib.SOURCE_CONTINUE
        amplitude=self.speaker.amplitude() if self.speaker else 0.
        image=self.scene.render(action,t,amplitude,size=(width,height),reduced=self.reduced,shelf=not self.transparent)
        self.frame=image
        raw=GLib.Bytes.new(image.tobytes())
        self.pixbuf=GdkPixbuf.Pixbuf.new_from_bytes(raw,GdkPixbuf.Colorspace.RGB,True,8,width,height,width*4)
        self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def paint(self,_widget,context):
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.set_source_rgba(0,0,0,0) if self.transparent else context.set_source_rgb(.10,.15,.19)
        context.paint()
        context.set_operator(cairo.OPERATOR_OVER)
        if self.pixbuf:
            Gdk.cairo_set_source_pixbuf(context,self.pixbuf,0,0)
            context.paint()
        return False

    def closed(self,*_):
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer=None


class DesktopPet(Gtk.Window):
    def __init__(self, companion, owner, speaker, reduced=False, on_status=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.companion=companion
        self.owner=owner
        self.reduced=reduced
        self.on_status=on_status or (lambda _:None)
        self.enabled=not reduced
        self.last_anchor=None
        self.anchor_override=None
        self.last_move=None
        self.set_title('Rıfkı · küçük kedi')
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_app_paintable(True)
        self.set_border_width(0)
        self.get_style_context().add_class('rifki-pet')
        visual=self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.view=PetView(speaker,reduced,transparent=True)
        self.view.behaviour.automatic=not reduced
        self.add(self.view)
        self.connect('realize',self.realized)
        self.connect('delete-event',self.dismiss)
        self.connect('destroy',self.closed)
        self.view.connect('draw',self.shape_after)
        self.wnck=None
        self.wnck_screen=None
        try:
            gi.require_version('Wnck','3.0')
            from gi.repository import Wnck
            self.wnck=Wnck
            self.wnck_screen=Wnck.Screen.get_default()
        except (ValueError,ImportError):
            pass
        self.timer=GLib.timeout_add(750,self.follow)

    def realized(self,*_):
        # Boş INPUT şekli: görünür tüylerin üstündeki tıklama bile kurucuya gider.
        self.get_window().input_shape_combine_region(cairo.Region(),0,0)
        self.get_window().set_pass_through(True)

    def dismiss(self,*_):
        self.enabled=False
        self.hide()
        return True

    def target(self):
        if self.anchor_override is not None:
            return self.anchor_override
        if self.wnck_screen is not None:
            self.wnck_screen.force_update()
            for window in reversed(self.wnck_screen.get_windows_stacked()):
                group=window.get_class_group()
                name=group.get_res_class().lower() if group and group.get_res_class() else ''
                if 'calamares' not in name or window.is_minimized():
                    continue
                # Hata / onay diyaloğu açıksa oyuncak animasyonu ilerlemez.
                if window.get_window_type()!=self.wnck.WindowType.NORMAL:
                    return None
                return Rect(*window.get_geometry())
        owner=self.owner()
        if owner and owner.get_visible() and owner.get_window():
            return Rect(*owner.get_position(),*owner.get_size())
        return None

    def follow(self):
        if not self.enabled or not self.companion.get_visible():
            self.hide()
            return GLib.SOURCE_CONTINUE
        target=self.target()
        if target is None:
            self.hide()
            return GLib.SOURCE_CONTINUE
        display=Gdk.Display.get_default()
        monitor=display.get_monitor_at_point(target.x,target.y)
        if monitor is None:
            self.hide()
            return GLib.SOURCE_CONTINUE
        area=monitor.get_workarea()
        geometry=perch_position(target,Rect(area.x,area.y,area.width,area.height))
        if geometry is None:
            self.hide()
            self.on_status('Üst kenarda yeterli yer yok; Rıfkı kendi oyun alanında.')
            return GLib.SOURCE_CONTINUE
        if self.last_anchor!=geometry:
            self.last_anchor=geometry
            self.view.set_size_request(geometry.width,geometry.height)
            self.resize(geometry.width,geometry.height)
            self.move(geometry.x,geometry.y)
        if not self.get_visible():
            self.show_all()
        action,_=self.view.behaviour.tick(time.monotonic())
        self.on_status(LABELS.get(action,'Rıfkı yanında')+' · Tıklamalar pencereye geçer')
        return GLib.SOURCE_CONTINUE

    def shape_after(self,*_):
        # Compositor kapalı eski cihazlarda siyah / opak dikdörtgen bırakma.
        if self.get_realized() and not self.get_screen().is_composited() and self.view.frame is not None:
            alpha=self.view.frame.getchannel('A')
            region=cairo.Region()
            pixels=alpha.load()
            for y in range(0,alpha.height,3):
                xs=[x for x in range(alpha.width) if pixels[x,y]>40]
                if xs:
                    region.union(cairo.RectangleInt(min(xs),y,max(xs)-min(xs)+1,min(3,alpha.height-y)))
            self.get_window().shape_combine_region(region,0,0)
            self.get_window().input_shape_combine_region(cairo.Region(),0,0)
        return False

    def choose(self,action):
        self.view.choose(action)
        self.follow()

    def closed(self,*_):
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer=None

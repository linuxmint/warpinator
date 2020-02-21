#!/usr/bin/python3
# coding: utf-8

# copied from cinnamon-screensaver framedImage.py

from gi.repository import Gtk, GdkPixbuf, Gio, GLib, GObject, Gdk

# image from a path or icon name, but rendered onto a surface so it looks nice in
# hidpi environments.

class SurfaceImage(Gtk.Image):
    def __init__(self, path=None, size=Gtk.IconSize.BUTTON):
        super(SurfaceImage, self).__init__()
        self.path = path
        self.pixel_size = size

    def set_from_path(self, path, size):
        self.path = path

        try:
            self.pixel_size = Gtk.icon_size_lookup(size)[0]
        except:
            self.pixel_size = 24

        self.generate_image_internal()

    def generate_image_internal(self):
        pixbuf = None
        scaled_size = self.pixel_size * self.get_scale_factor()

        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(self.path, scaled_size, scaled_size)
        except GLib.Error as e:
            print("Could not load avatar image '%s':" %(self.path, e.message))
            pixbuf = None

        if pixbuf:
            surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf,
                                                           self.get_scale_factor(),
                                                           None)
            self.set_from_surface(surface)
        else:
            self.set_from_icon_name("avatar-default-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
            self.set_pixel_size(self.pixel_size)


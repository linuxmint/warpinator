#!/usr/bin/python3
import os
import sys
import time
import getpass
import random
import setproctitle
import locale
import gettext

import socket
import xmlrpc.server
import xmlrpc.client
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceStateChange

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('XApp', '1.0')
from gi.repository import Gtk, GLib, XApp, Gio, GObject, Gdk

import util
import config
import prefs

# Don't let warp run as root
if os.getuid() == 0:
    print("Warp should not be run as root. Please run it in user mode.")
    sys.exit(1)

# i18n
locale.bindtextdomain(config.PACKAGE, config.localedir)
gettext.bindtextdomain(config.PACKAGE, config.localedir)
gettext.textdomain(config.PACKAGE)
_ = gettext.gettext

setproctitle.setproctitle("warp")

dnd_string = """
.ebox:drop(active) {
    background-image: linear-gradient(to top, grey, transparent);
    transition: 100ms;
}
"""

class WarpServer(object):
    def __init__(self):
        self.port = 8080
        self.my_ip = util.getmyip()
        self.save_location = GLib.get_home_dir()
        self.my_nick = None
        self.service_name = "warp.%s._http._tcp.local." % self.my_ip

    def register_zeroconf(self):
        desc = {}

        self.info = ServiceInfo("_http._tcp.local.",
                                self.service_name,
                                socket.inet_aton(self.my_ip), self.port, 0, 0,
                                desc, "somehost.local.")
        self.zc = Zeroconf()
        self.zc.register_service(self.info)

    @util._async
    def serve_forever(self):
        self.register_zeroconf()
        addr = ("0.0.0.0", self.port)
        with xmlrpc.server.SimpleXMLRPCServer(addr) as server:
            print("Listening on", addr)
            server.register_function(self.get_nick, "get_nick")
            server.register_function(self.receive_file, "receive_file")
            server.serve_forever()

    def set_prefs(self, nick, path):
        self.save_location = path
        self.my_nick = nick

    def get_nick(self):
        if self.my_nick != None:
            return self.my_nick

        return "%s@%s" % (getpass.getuser(), socket.gethostname())

    def receive_file(self, sender, basename, binary_data):
        print("server received %s from %s" % (basename, sender))
        with open(os.path.join(self.save_location, basename), "wb") as handle:
            handle.write(binary_data.data)

        return True

    def close(self):
        self.zc.unregister_service(self.info)

class ProxyItem(Gtk.EventBox):
    def __init__(self, name, proxy):
        super(ProxyItem, self).__init__(height_request=40)
        self.proxy = proxy
        self.name = name
        self.nick = proxy.get_nick()
        self.dropping = False
        self.get_style_context().add_class("ebox")

        w = Gtk.Frame()
        self.add(w)

        self.layout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        w.add(self.layout)

        w = Gtk.Label(label=self.nick)
        self.layout.pack_start(w, True, True, 6)

        entry = Gtk.TargetEntry.new("text/uri-list",  0, 0)
        self.drag_dest_set(Gtk.DestDefaults.ALL,
                           (entry,),
                           Gdk.DragAction.COPY)
        self.connect("drag-drop", self.on_drag_drop)
        self.connect("drag-data-received", self.on_drag_data_received)

        self.show_all()

    def on_click(self, data=None):
        self.proxy.click("%s" % (self.name,))

    def on_drag_drop(self, widget, context, x, y, time, data=None):
        atom =  widget.drag_dest_find_target(context, None)
        self.dropping = True
        widget.drag_get_data(context, atom, time)

    def on_drag_data_received (self, widget, context, x, y, data, info, time, user_data=None):
        if not self.dropping:
            Gdk.drag_status(context, Gdk.DragAction.COPY, time)
            return
        if data:
            if context.get_selected_action() == Gdk.DragAction.COPY:
                uris = data.get_uris()
                self.send_files(uris)

        Gtk.drag_finish(context, True, False, time)
        self.dropping = False

    def send_files(self, uri_list):
        for uri in uri_list:
            f = Gio.File.new_for_uri(uri)
            print("Sending %s to %s" % (f.get_path(), self.name))
            with open(f.get_path(), "rb") as handle:
                data = handle.read()
                self.proxy.receive_file(self.name, f.get_basename(), xmlrpc.client.Binary(data))

class WarpApplication(Gtk.Application):
    def __init__(self):
        super(WarpApplication, self).__init__(application_id="com.linuxmint.warp",
                                              flags=Gio.ApplicationFlags.IS_SERVICE)
        self.window = None
        self.status_icon = None
        self.peers = {}
        self.nick = None

        self.server = None
        self.service_browser = None
        self.zeroconf = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.my_ip = util.getmyip()
        print("Initializing Warp on %s\n" % self.my_ip)

        self.prefs_settings = Gio.Settings(schema_id=util.PREFS_SCHEMA)
        self.prefs_settings.connect("changed", self.on_prefs_changed)

        self.server = WarpServer()
        self.on_prefs_changed(self.prefs_settings, None, None)
        self.server.serve_forever()

        self.setup_browser()
        self.activate()

    def do_activate(self):
        if self.status_icon == None:
            self.setup_status_icon()
        if self.window == None:
            self.setup_window()

    def setup_window(self):
        self.builder = Gtk.Builder.new_from_file(os.path.join(config.pkgdatadir, "warp-window.ui"))
        self.window =self.builder.get_object("window")
        self.box = self.builder.get_object("flowbox")
        self.above_toggle = self.builder.get_object("keep_above")
        self.menu_button = self.builder.get_object("menu_button")
        self.open_location_button = self.builder.get_object("open_location")

        menu = Gtk.Menu()
        item = Gtk.MenuItem(label=_("Preferences"))
        item.connect("activate", self.open_preferences)
        menu.add(item)

        item = Gtk.MenuItem(label=_("Quit"))
        item.connect("activate", self.exit_app)
        menu.add(item)
        menu.show_all()

        dnd_css = Gtk.CssProvider()

        if dnd_css.load_from_data(dnd_string.encode()):
            Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), dnd_css, 600)

        self.menu_button.set_popup(menu)

        self.window.set_icon_name("warp")
        self.window.connect("delete-event",
                            lambda widget, event: widget.hide_on_delete())
        self.above_toggle.connect("toggled",
                                  lambda widget, window: window.set_keep_above(widget.props.active), self.window)
        self.above_toggle.set_active(self.prefs_settings.get_boolean(util.START_PINNED_KEY))
        self.open_location_button.connect("clicked", self.on_open_location_clicked)

        self.add_window(self.window)

        if self.prefs_settings.get_boolean(util.START_WITH_WINDOW_KEY):
            self.window.present()

    def open_preferences(self, menuitem, data=None):
        w = prefs.Preferences()
        w.set_transient_for(self.window)
        w.connect("delete-event", self.on_prefs_closed)
        # Disable keep above while the prefs window is displayed.  Otherwise you have a modal
        # window underneath its parent.
        self.window.set_keep_above(False)
        w.present()

    def on_prefs_closed(self, widget, event, data=None):
        self.window.set_keep_above(self.above_toggle.get_active())

    def exit_app(self, menuitem, data=None):
        self.server.close()
        self.quit()

    def on_prefs_changed(self, settings, pspec=None, data=None):
        file = Gio.File.new_for_uri(settings.get_string(util.FOLDER_NAME_KEY))
        self.nick = settings.get_string(util.BROADCAST_NAME_KEY)

        self.server.set_prefs(self.nick, file.get_path())

    def on_open_location_clicked(self, widget, data=None):
        app = Gio.AppInfo.get_default_for_type("inode/directory", True)
        try:
            file = Gio.File.new_for_uri(self.prefs_settings.get_string(util.FOLDER_NAME_KEY))
            app.launch((file,), None)
        except GLib.Error as e:
            print("Could not open received files location: %s" % e.message)

    ####  BROWSER ##############################################

    def setup_browser(self):
        print("\nSearching for others...\n")
        self.zeroconf = Zeroconf()
        self.browser = ServiceBrowser(self.zeroconf, "_http._tcp.local.", self)

    def remove_service(self, zeroconf, _type, name):
        print("\nService %s removed\n" % (name,))
        self.remove_peer(name)

    def add_service(self, zeroconf, _type, name):
        info = zeroconf.get_service_info(_type, name)
        print("\nService %s added, service info: %s\n" % (name, info))
        if info and name.count("warp"):
            addrstr = "http://{}:{}".format(socket.inet_ntoa(info.address), info.port)
            proxy = xmlrpc.client.ServerProxy(addrstr)

            if name == self.server.service_name:
                print("Not adding my own service (%s)" % name)
                return

            self.add_peer(name, proxy)

    @util._idle
    def add_peer(self, name, proxy):
        if name in self.peers.keys():
            return False

        print("Add peer: %s" % name)
        button = ProxyItem(name, proxy)

        self.peers[name] = button
        self.box.add(button)
        return False

    @util._idle
    def remove_peer(self, name):
        print("Remove peer: %s" % name)

        try:
            self.peers[name].destroy()
            del self.peers[name]
        except KeyError as e:
            print("Existing proxy item not found, why not?")

    # STATUS ICON ##########################################################################

    def setup_status_icon(self):
        self.status_icon = XApp.StatusIcon()
        self.status_icon.set_icon_name("warp-symbolic")
        self.status_icon.connect("activate", self.on_tray_icon_activate)

        menu = Gtk.Menu()

        item = Gtk.MenuItem(label=_("Open Warp folder"))
        item.connect("activate", self.on_open_location_clicked)
        menu.add(item)
        item = Gtk.MenuItem(label=_("Quit"))
        item.connect("activate", self.exit_app)
        menu.add(item)
        menu.show_all()

        self.status_icon.set_secondary_menu(menu)

    def on_tray_icon_activate(self, icon, button, time=0):
        if self.window.is_active():
            self.window.hide()
        else:
            if not self.window.get_visible():
                self.window.present()
                self.window.set_keep_above(self.above_toggle.props.active)
            else:
                # When there is more than one monitor, either gtk or
                # window managers (I've seen this in cinnamon, mate, xfce)
                # get confused if the mintupdate window is topmost on one
                # monitor, but the current focus is actually a window in
                # another monitor.  Focusing makes sure this window will
                # become 'active' for purposes of the hiding code above.

                self.window.get_window().raise_()
                self.window.get_window().focus(time)


if __name__ == "__main__":
    w = WarpApplication()
    w.run(sys.argv)

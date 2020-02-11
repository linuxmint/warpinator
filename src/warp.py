#!/usr/bin/python3
import os
import sys
import time
import getpass
import random
import setproctitle
import locale
import gettext
import queue
import threading

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

TRANSFER_START = "start"
TRANSFER_DATA = "data"
TRANSFER_COMPLETE = "end"
TRANSFER_FOLDER = "folder"
TRANSFER_ABORT = "aborted"

RESPONSE_EXISTS = "exists"
RESPONSE_OK = "ok"
RESPONSE_DISKFULL = "diskfull"
RESPONSE_ERROR = "error"

FILE_INFOS = "standard::size,standard::name,standard::type"

dnd_string = """
.ebox:drop(active) {
    background-image: linear-gradient(to top, grey, transparent);
    transition: 100ms;
}
"""

class Aborted(Exception):
    pass

class NeverStarted(Exception):
    pass

class WarpServer(object):
    def __init__(self):
        self.port = 8080
        self.my_ip = util.getmyip()
        self.save_location = GLib.get_home_dir()
        self.my_nick = None
        self.service_name = "warp.%s._http._tcp.local." % self.my_ip

        self.file_receiver = FileReceiver(self.save_location)

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
        with xmlrpc.server.SimpleXMLRPCServer(addr, allow_none=True) as server:
            print("Listening on", addr)
            server.register_function(self.get_nick, "get_nick")
            server.register_function(self.receive, "receive")
            server.serve_forever()

    def set_prefs(self, nick, path):
        self.save_location = path
        self.file_receiver.save_path = path
        self.my_nick = nick

    def get_nick(self):
        if self.my_nick != None:
            return self.my_nick

        return "%s@%s" % (getpass.getuser(), socket.gethostname())

    def receive(self, sender, basename, state, binary_data=None):
        print("server received state %s for file %s from %s" % (state, basename, sender))
        path = os.path.join(self.save_location, basename)

        if state == TRANSFER_START and GLib.file_test(path, GLib.FileTest.EXISTS):
            return RESPONSE_EXISTS

        return self.file_receiver.receive(basename, state, binary_data)

    def close(self):
        self.file_receiver.stop()
        self.zc.unregister_service(self.info)

class ProxyItem(Gtk.EventBox):
    def __init__(self, name, proxy):
        super(ProxyItem, self).__init__(height_request=40,
                                        margin=6)
        self.proxy = proxy
        self.name = name
        self.nick = ""

        self.file_sender = FileSender(self.name, self.proxy, self.progress_callback)

        self.dropping = False
        self.get_style_context().add_class("ebox")

        frame = Gtk.Frame()
        self.add(frame)

        self.layout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                              border_width=4)
        frame.add(self.layout)

        overlay = Gtk.Overlay()

        self.progress = Gtk.ProgressBar(no_show_all=True)
        overlay.add(self.progress)

        self.label = Gtk.Label(label=self.nick)
        overlay.add_overlay(self.label)

        self.layout.pack_start(overlay, True, True, 0)

        entry = Gtk.TargetEntry.new("text/uri-list",  0, 0)
        self.drag_dest_set(Gtk.DestDefaults.ALL,
                           (entry,),
                           Gdk.DragAction.COPY)
        self.connect("drag-drop", self.on_drag_drop)
        self.connect("drag-data-received", self.on_drag_data_received)

        GLib.timeout_add_seconds(1, self.try_update_proxy_nick)
        self.show_all()

    def try_update_proxy_nick(self, data=None):
        # Why does this happen?  Why can't there be some sort of ready
        # callback for a ServerProxy being 'ready'?
        try:
            self.nick = self.proxy.get_nick()
            self.label.set_markup("<b>%s</b>" % self.nick)

        except ConnectionRefusedError:
            print("Retrying proxy check")
            return True

        return False

    def on_drag_drop(self, widget, context, x, y, time, data=None):
        atom =  widget.drag_dest_find_target(context, None)
        self.dropping = True
        widget.drag_get_data(context, atom, time)

    def on_drag_data_received(self, widget, context, x, y, data, info, time, user_data=None):
        if not self.dropping:
            Gdk.drag_status(context, Gdk.DragAction.COPY, time)
            return
        if data:
            if context.get_selected_action() == Gdk.DragAction.COPY:
                uris = data.get_uris()
                self.file_sender.send_files(uris)

        Gtk.drag_finish(context, True, False, time)
        self.dropping = False

    def progress_callback(self, progress):
        if progress > 1.0:
            progress = 1.0

        self.progress.set_fraction(progress)
        self.progress.set_visible(progress != 0)

    def do_destroy(self):
        self.file_sender.stop()

        Gtk.Widget.do_destroy(self)

class FileSender:
    CHUNK_SIZE = 1024 * 1024
    def __init__(self, name, proxy, progress_callback):
        self.proxy = proxy
        self.name = name
        self.progress_callback = progress_callback

        self.cancellable = None
        self.queue = queue.Queue()
        self.send_thread = threading.Thread(target=self._send_file_thread)
        self.send_thread.start()

        self.total_transfer_size = 0
        self.current_transfer_size = 0
        self.file_to_size_map = {}

    def send_files(self, uri_list):
        self._process_files(uri_list)

    @util._async
    def _process_files(self, uri_list):
        # expanded uri list will be (full_uri, relative_uri)
        expanded_uri_list = []

        def process_folder(top_dir):
            top_dir_parent_uri = top_dir.get_parent().get_uri()

            def process_subfolders_recursively(rec_dir):
                rec_enumerator = rec_dir.enumerate_children(FILE_INFOS, Gio.FileQueryInfoFlags.NONE, None)
                rec_info = rec_enumerator.next_file(None)

                while rec_info:
                    rec_child = rec_enumerator.get_child(rec_info)

                    if rec_info.get_file_type() == Gio.FileType.DIRECTORY:
                        process_subfolders_recursively(rec_child)
                    else:
                        size = rec_info.get_size()
                        rec_child_uri = rec_child.get_uri()
                        self.file_to_size_map[rec_child_uri] = size
                        rec_pair = (rec_child_uri, os.path.relpath(rec_child_uri, top_dir_parent_uri))
                        expanded_uri_list.append(rec_pair)

                    rec_info = rec_enumerator.next_file(None)

            enumerator = top_dir.enumerate_children(FILE_INFOS, Gio.FileQueryInfoFlags.NONE, None)
            info = enumerator.next_file(None)

            while info:
                child = enumerator.get_child(info)

                if info.get_file_type() == Gio.FileType.DIRECTORY:
                    process_subfolders_recursively(child)
                else:
                    size = info.get_size()
                    child_uri = child.get_uri()
                    self.file_to_size_map[child_uri] = size
                    sub_pair = (child_uri, os.path.relpath(child_uri, top_dir_parent_uri))
                    expanded_uri_list.append(sub_pair)

                info = enumerator.next_file(None)

        # treat individual files as normal, somehow keep relative locations for dir children
        for uri in uri_list:
            file = Gio.File.new_for_uri(uri)
            info = file.query_info(FILE_INFOS, Gio.FileQueryInfoFlags.NONE, None)

            if info and info.get_file_type() == Gio.FileType.DIRECTORY:
                process_folder(file)
                continue
            else:
                size = info.get_size()
                self.file_to_size_map[uri] = size
                expanded_uri_list.append((uri, uri))

        new_total = 0
        for size in self.file_to_size_map.values():
            new_total += size

        self.total_transfer_size = new_total
        self.current_transfer_size = 0

        GLib.idle_add(self.queue_files, expanded_uri_list)
        exit()

    def queue_files(self, uri_list):
        for pair in uri_list:
            self.queue.put(pair)

    def _send_file_thread(self):
        while True:
            pair = self.queue.get()
            if pair is None:
                break
            self._real_send(pair)
            self.queue.task_done()
            if self.queue.empty():
                GLib.timeout_add_seconds(1, self.progress_callback, 0)

    def _real_send(self, pair):
        uri, relative_uri = pair

        file = Gio.File.new_for_uri(uri)
        dest_path = relative_uri if relative_uri else file.get_basename()

        self.cancellable = Gio.Cancellable()

        try:
            stream = file.read(self.cancellable)

            if self.cancellable.is_cancelled():
                stream.close()
                raise NeverStarted("Cancelled while opening file");

            response = self.proxy.receive(self.name,
                                          dest_path,
                                          TRANSFER_START,
                                          None)

            if response == RESPONSE_EXISTS:
                raise NeverStarted("File exists at remote location")

            while True:
                bytes = stream.read_bytes(self.CHUNK_SIZE, self.cancellable)

                if self.cancellable.is_cancelled():
                    stream.close()
                    raise Aborted("Cancelled while reading file contents");

                if (bytes.get_size() > 0):
                    self.proxy.receive(self.name,
                                       dest_path,
                                       TRANSFER_DATA,
                                       xmlrpc.client.Binary(bytes.get_data()))
                    self.current_transfer_size += bytes.get_size()

                    progress =self.current_transfer_size / self.total_transfer_size
                    GLib.idle_add(self.progress_callback, progress)
                else:
                    break

            self.proxy.receive(self.name,
                               dest_path,
                               TRANSFER_COMPLETE,
                               None)

            del self.file_to_size_map[file.get_uri()]

            stream.close()
        except Aborted as e:
            self.proxy.receive(self.name,
                               dest_path,
                               TRANSFER_ABORT,
                               None)
        except NeverStarted as e:
            print("File %s already exists, skipping: %s" % (file.get_path(), str(e)))

    def _report_progress(self, progress):
        GLib.idle_add(self.progress_callback, progress)

    def stop(self):
        if self.cancellable:
            self.cancellable.cancel()
        self.queue.put(None)
        self.send_thread.join()


class FileReceiver:
    CHUNK_SIZE = 1024 * 1024
    def __init__(self, save_path):
        self.save_path = save_path
        self.cancellable = None

        # Packets from any source
        self.request_queue = queue.Queue()
        self.open_files = {}

        self.thread = threading.Thread(target=self._receive_file_thread)
        self.thread.start()

    def receive(self, basename, status, data=None):

        path = os.path.join(self.save_path, basename)

        if status in (TRANSFER_DATA, TRANSFER_COMPLETE, TRANSFER_ABORT) and not self.open_files[path]:
            return RESPONSE_ERROR

        self.request_queue.put((basename, status, data))

        return RESPONSE_OK

    def _receive_file_thread(self):
        while True:
            packet = self.request_queue.get()
            if packet == None:
                break

            self._real_receive(packet)

            self.request_queue.task_done()

    def _real_receive(self, packet):
        (basename, status, data) = packet
        self.cancellable = Gio.Cancellable()

        path = os.path.join(self.save_path, basename)

        if status == TRANSFER_START:
            new_file = Gio.File.new_for_path(path)

            try:
                os.makedirs(new_file.get_parent().get_path(), exist_ok=True)
                self.open_files[path] = new_file.create(Gio.FileCreateFlags.NONE,
                                                        self.cancellable)
            except GLib.Error as e:
                print("Could not open file %s for writing: %s" % (path, e.message))

            if self.cancellable.is_cancelled():
                del self.open_files[path]

            return
        if status == TRANSFER_COMPLETE:
            try:
                self.open_files[path].close(self.cancellable)
            except GLib.Error as e:
                print("Could not close file %s from writing: %s" % (path, e.message))

            del self.open_files[path]
            return

        if status == TRANSFER_ABORT:
            aborted_file = Gio.File.new_for_path(path)

            try:
                self.open_files[path].close(self.cancellable)
                aborted_file.delete(self.cancellable)
            except GLib.Error as e:
                print("Could not cleanly abort file %s from writing: %s" % (path, e.message))

            del self.open_files[path]
            return

        if status == TRANSFER_DATA:
            stream = self.open_files[path]

            try:
                stream.write(data.data, self.cancellable)
            except GLib.Error as e:
                print("Could not write data to file %s: %s" % (path, e.message))
                try:
                    stream.close()
                    aborted_file = Gio.File.new_for_path(path)
                    aborted_file.delete(self.cancellable)
                except GLib.Error as e:
                    print("Could not abort after write error: %s" % e.message)

            return

    def stop(self):
        if self.cancellable:
            self.cancellable.cancel()
        self.request_queue.put(None)
        self.thread.join()

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
        self.save_path = GLib.get_home_dir()

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
        self.box = self.builder.get_object("proxy_box")
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

    def exit_app(self, menuitem=None, data=None):
        print("Shut down")
        self.server.close()
        for item in self.peers.values():
            item.destroy()
        self.quit()

    def on_prefs_changed(self, settings, pspec=None, data=None):
        self.nick = settings.get_string(util.BROADCAST_NAME_KEY)

        save_path = settings.get_string(util.FOLDER_NAME_KEY)
        if save_path != "":
            self.save_path = save_path
            file = Gio.File.new_for_uri(save_path)
            self.server.set_prefs(self.nick, save_path)

    def on_open_location_clicked(self, widget, data=None):
        app = Gio.AppInfo.get_default_for_type("inode/directory", True)
        try:
            file = Gio.File.new_for_uri(self.save_path)
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
            proxy = xmlrpc.client.ServerProxy(addrstr, allow_none=True)

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

    try:
        w.run(sys.argv)
    except KeyboardInterrupt:
        w.exit_app()

    exit(0)
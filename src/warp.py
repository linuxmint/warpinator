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
import re

import socket
import xmlrpc.server
import xmlrpc.client
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceStateChange

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('XApp', '1.0')
from gi.repository import Gtk, GLib, XApp, Gio, GObject, Gdk

import config
import prefs
import transfers
import util

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

class PermissionRequest():
    def __init__(self, name, nick, size, count, timestamp_str):
        self.name = name
        self.nick = nick
        self.size = size
        self.count = count
        self.time_str = timestamp_str

        self.permission = util.TRANSFER_REQUEST_PENDING

class WarpServer(GObject.Object):
    def __init__(self, peers, service_name, ip):
        self.my_ip = ip
        self.service_name = service_name
        self.port = 8080
        self.peer_list = peers
        self.save_location = GLib.get_home_dir()
        self.my_nick = "%s@%s" % (getpass.getuser(), socket.gethostname())

        self.permission_requests = []

        self.file_receiver = transfers.FileReceiver(self.save_location)

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
        with xmlrpc.server.SimpleXMLRPCServer(addr, allow_none=True, logRequests=False) as server:
            print("Listening on", addr)
            server.register_function(self._get_nick, "get_nick")
            server.register_function(self._files_exist, "files_exist")
            server.register_function(self._receive, "receive")
            server.register_function(self._check_needs_permission, "check_needs_permission")
            server.register_function(self._get_permission, "get_permission")
            server.register_function(self._abort_transfer, "abort_transfer")
            server.register_function(self._update_progress, "update_progress")
            server.register_function(self._update_my_info, "update_my_info")
            server.serve_forever()

    def set_prefs(self, nick, path):
        self.save_location = path
        self.file_receiver.save_path = path

        if nick != "":
            self.my_nick = nick

        print("Save path: %s" % self.save_location)
        print("Visible as '%s'" % self.my_nick)

    def _get_nick(self):
        if self.my_nick != None:
            return self.my_nick

    def _update_my_info(self, sender):
        try:
            peer = self.peer_list[sender]
            peer.update_proxy_info()
        except KeyError:
            print("Received change notification for unknown proxy - what's up: %s" % name)
            return False

        return True

    def _files_exist(self, base_names):
        for name in base_names:
            path = os.path.join(self.save_location, name)
            print("(server side) Checking if file or folder %s already exists." % (path,))
            if GLib.file_test(path, GLib.FileTest.EXISTS):
                return True

        return False

    def _receive(self, sender, basename, folder=False, symlink_target=None, serial=0, binary_data=None):
        # print("receive data for file %s from %s (serial %d) - folder:%d symlink:%s" % (basename, sender, serial, folder, symlink_target))

        return self.file_receiver.receive(basename, folder, symlink_target, serial, binary_data)

    def _check_needs_permission(self):
        return prefs.ask_permission_for_transfer()

    def _get_permission(self, name, nick, size, count, time_str):
        for req in self.permission_requests:
            if req.name == name:
                if req.time_str == time_str:
                    if req.permission != util.TRANSFER_REQUEST_PENDING:
                        self.permission_requests.remove(req)
                    return req.permission
                else:
                    return util.TRANSFER_REQUEST_EXISTING

        request = PermissionRequest(name, nick, size, count, time_str)
        self.permission_requests.append(request)

        try:
            peer = self.peer_list[name]
            peer.ask_user_permission(request)
        except KeyError:
            print("Received transfer request for unknown proxy - what's up: %s" % name)
            return False

        return util.TRANSFER_REQUEST_PENDING

    def _abort_transfer(self, name):
        print("Server size: Abort transfer from", name)
        pass

    def _update_progress(self, name, progress, speed, time_left, finished):
        GLib.idle_add(self._update_progress_at_idle, name, progress, speed, time_left, finished, priority=GLib.PRIORITY_DEFAULT)
        return True

    def _update_progress_at_idle(self, name, progress, speed, time_left, finished):
        try:
            peer = self.peer_list[name]
            peer.receive_progress_callback(progress, speed, time_left, finished)
        except KeyError:
            print("Received progress for unknown proxy - what's up: %s" % name)

        return False

    def close(self):
        self.file_receiver.stop()
        self.zc.unregister_service(self.info)

class ProxyItem(object):
    def __init__(self, my_name, name, proxy):
        super(ProxyItem, self).__init__()
        self.my_name = my_name
        self.proxy = proxy
        self.name = name
        self.nick = ""
        self.send_stat_delay_timer = 0
        self.receive_stat_delay_timer = 0
        self.active_request = None

        self.builder = Gtk.Builder.new_from_file(os.path.join(config.pkgdatadir, "warp-window.ui"))
        self.widget =self.builder.get_object("proxy_widget")
        self.page_stack = self.builder.get_object("page_stack")

        self.status_page = self.builder.get_object("status_page")
        self.nick_label = self.builder.get_object("nick_label")
        self.progress_box = self.builder.get_object("progress_box")
        self.send_progress_bar = self.builder.get_object("send_progress_bar")
        self.receive_progress_bar = self.builder.get_object("receive_progress_bar")
        self.sender_awaiting_approval_label = self.builder.get_object("sender_awaiting_approval_label")
        self.req_transfer_label = self.builder.get_object("req_transfer_label")
        self.req_accept_button = self.builder.get_object("req_accept_button")
        self.req_accept_button.connect("clicked", self.on_request_response, True)
        self.req_decline_button = self.builder.get_object("req_decline_button")
        self.req_decline_button.connect("clicked", self.on_request_response, False)

        self.file_sender = transfers.FileSender(self.my_name, self.name, self.nick, self.proxy, self.send_progress_callback)
        self.dropping = False

        entry = Gtk.TargetEntry.new("text/uri-list",  0, 0)
        self.widget.drag_dest_set(Gtk.DestDefaults.ALL,
                                  (entry,),
                                  Gdk.DragAction.COPY)
        self.widget.connect("drag-drop", self.on_drag_drop)
        self.widget.connect("drag-data-received", self.on_drag_data_received)

        self.update_proxy_info()
        self.hide_receive_stats()
        self.hide_send_stats()
        self.widget.show_all()

    def send_changed_to_peer(self):
        # Tells the server this proxy represents to refresh its info on us (this is called by WarpApplication,
        # when something like our nick changes.
        self.proxy.update_my_info(self.my_name)

    def update_proxy_info(self):
        # This is sent by our local server, telling us to grab new info from the remote server this proxy represents.
        GLib.timeout_add_seconds(1, self.try_update_proxy_nick)

    def transfer_active(self):
        # FIXME: Make a more appropriate method of doing this.
        return self.send_progress_bar.props.visible or self.receive_progress_bar.props.visible

    def try_update_proxy_nick(self, data=None):
        # Why does this happen?  Why can't there be some sort of ready
        # callback for a ServerProxy being 'ready'?
        try:
            self.nick = self.proxy.get_nick()
            self.nick_label.set_markup("<b>%s</b>" % self.nick)
            self.file_sender.peer_nick = self.nick

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

    def queue_send_showing_stats(self):
        if self.send_stat_delay_timer > 0:
            GLib.source_remove(self.send_stat_delay_timer)

        self.page_stack.set_visible_child_name("status")
        self.send_stat_delay_timer = GLib.timeout_add(500, self.show_send_stats_timeout)

    def show_send_stats_timeout(self, data=None):
        self.send_stat_delay_timer = 0
        self.send_progress_bar.show()

    def hide_send_stats(self):
        self.send_progress_bar.set_fraction(0)
        self.send_progress_bar.set_text(_("Sending"))
        self.send_progress_bar.hide()

    def send_progress_callback(self, data=util.ProgressCallbackInfo()):
        cb_info = data

        if cb_info.transfer_starting or cb_info.transfer_cancelled:
            self.page_stack.set_visible_child_name("status")
            return

        if not self.send_progress_bar.get_visible() and not cb_info.finished and not cb_info.sender_awaiting_approval:
            self.queue_send_showing_stats()

        if cb_info.progress > 1.0:
            cb_info.progress = 1.0

        self.send_progress_bar.set_fraction(cb_info.progress)

        if cb_info.speed and cb_info.time_left:
            self.send_progress_bar.set_text(_("Sending - %s - %s" % (cb_info.time_left, cb_info.speed)))

        if cb_info.finished:
            if self.send_stat_delay_timer > 0:
                GLib.source_remove(self.send_stat_delay_timer)
                self.send_stat_delay_timer = 0
            else:
                self.hide_send_stats()

        if cb_info.sender_awaiting_approval:
            self.page_stack.set_visible_child_name("sender_awaiting_approval")
            markup = gettext.ngettext("Waiting on approval to send %d file",
                                      "Waiting on approval to send %d files", cb_info.count) \
                                      % (cb_info.count,)
            self.sender_awaiting_approval_label.set_markup(markup)

    def queue_receive_showing_stats(self):
        if self.receive_stat_delay_timer > 0:
            GLib.source_remove(self.receive_stat_delay_timer)

        self.receive_stat_delay_timer = GLib.timeout_add(500, self.show_receive_stats_timeout)

    def show_receive_stats_timeout(self, data=None):
        self.receive_stat_delay_timer = 0
        self.receive_progress_bar.show()

    def hide_receive_stats(self):
        self.receive_progress_bar.set_fraction(0)
        self.receive_progress_bar.set_text(_("Receiving"))
        self.receive_progress_bar.hide()

    def receive_progress_callback(self, progress, speed, time_left, finished=False):
        # print("Receive progress callback - server", progress, speed, time_left)
        if not self.receive_progress_bar.get_visible():
            self.queue_receive_showing_stats()

        if progress > 1.0:
            progress = 1.0

        self.receive_progress_bar.set_fraction(progress)

        if speed and time_left:
            self.receive_progress_bar.set_text(_("Receiving - %s - %s" % (time_left, speed)))

        if finished:
            if self.receive_stat_delay_timer > 0:
                GLib.source_remove(self.receive_stat_delay_timer)
                self.receive_stat_delay_timer = 0
            else:
                self.hide_receive_stats()

    def ask_user_permission(self, request):
        print("ask from ", request.nick)
        self.active_request = request

        self.page_stack.set_visible_child_name("transfer_request")

        markup = gettext.ngettext("<b>%s</b> wants to send you %d file (%s)",
                                  "<b>%s</b> wants to send you %d files (%s)", request.count) \
                                  % (request.nick, request.count, GLib.format_size(request.size))

        self.req_transfer_label.set_markup(markup)

    def on_request_response(self, widget, approve):
        if approve:
            self.active_request.permission = util.TRANSFER_REQUEST_GRANTED
        else:
            self.active_request.permission = util.TRANSFER_REQUEST_DECLINED
        self.active_request = None

        self.page_stack.set_visible_child_name("status")

    def destroy(self):
        self.widget.destroy()
        self.file_sender.stop()

class WarpApplication(Gtk.Application):
    def __init__(self):
        super(WarpApplication, self).__init__(application_id="com.linuxmint.warp",
                                              flags=Gio.ApplicationFlags.IS_SERVICE)
        self.window = None
        self.status_icon = None
        self.peers = {}
        self.nick = None

        self.server = None
        self.my_ip = util.getmyip()
        self.my_server_name = "warp.%s._http._tcp.local." % self.my_ip

        self.service_browser = None
        self.zeroconf = None
        self.save_path = GLib.get_home_dir()

        self.prefs_changed_source_id = 0

        self.ip_extractor = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")

    def do_startup(self):
        Gtk.Application.do_startup(self)
        print("Initializing Warp on %s" % self.my_ip)

        prefs.prefs_settings.connect("changed", self.on_prefs_changed)

        self.server = WarpServer(self.peers, self.my_server_name, self.my_ip)
        self.on_prefs_changed(prefs.prefs_settings, None, None)
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
        self.add_window(self.window)

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
        self.above_toggle.set_active(prefs.get_start_pinned())
        self.open_location_button.connect("clicked", self.on_open_location_clicked)

        if prefs.get_start_with_window():
            self.window.present()

    def open_preferences(self, menuitem, data=None):
        transfer_active = False
        # We won't allow nick changes while there is ongoing activity ?? for now
        for item in self.peers.values():
            if item.transfer_active():
                transfer_active = True
                break
        w = prefs.Preferences(transfer_active)
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
        if self.prefs_changed_source_id > 0:
            GLib.source_remove(self.prefs_changed_source_id)

        self.prefs_changed_source_id = GLib.timeout_add_seconds(1, self._on_delayed_prefs_changed)

    def _on_delayed_prefs_changed(self):
        self.prefs_changed_source_id = 0

        self.nick = prefs.get_nick()
        self.save_path = prefs.get_save_path()

        self.server.set_prefs(self.nick, self.save_path)
        for item in self.peers.values():
            item.send_changed_to_peer()
        return False

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
            addrstr = "http://{}:{}".format(self.ip_extractor.search(name)[0], info.port)
            proxy = xmlrpc.client.ServerProxy(addrstr, allow_none=True)
            if name == self.my_server_name:
                print("Not adding my own service (%s)" % name)
                return

            self.add_peer(name, proxy)

    @util._idle
    def add_peer(self, name, proxy):
        if name in self.peers.keys():
            return False

        print("Add peer: %s" % name)
        item = ProxyItem(self.my_server_name, name, proxy)

        self.peers[name] = item
        self.box.add(item.widget)
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
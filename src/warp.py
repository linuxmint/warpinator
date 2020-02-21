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
import functools

import socket
import xmlrpc.server
import xmlrpc.client
import http
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceStateChange
import rpyc
from rpyc.utils.server import ThreadPoolServer

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('XApp', '1.0')
from gi.repository import Gtk, GLib, XApp, Gio, GObject, Gdk

import config
import prefs
import transfers
import util
import pulse
import remote
from remote import SendOp, ReceiveOp
from util import TransferDirection, OpStatus
socket.setdefaulttimeout(10)


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

class PermissionRequest():
    def __init__(self, name, nick, size, count, timestamp_str):
        self.name = name
        self.nick = nick
        self.size = size
        self.count = count
        self.time_str = timestamp_str

        self.permission = util.TRANSFER_REQUEST_PENDING

class WarpService(rpyc.Service):
    # def __init__(self):
        # super(WarpService, self).__init__()
        # GObject.Object.__init__(self)
        # self.service_name = "warp.%s._http._tcp.local." % util.get_ip()
        # print("etfff")
        # self.register_zeroconf()

    # def on_connect(self, conn):
    #     pass

    # def on_disconnect(self, conn):
    #     pass

    def exposed_update_client_info(self, callback):
        acb = rpyc.async_(callback)
        acb(prefs.get_nick(), util.get_hostname(), util.get_ip())

    # @util._async
    def register_zeroconf(self):
        desc = {}


        self.info = ServiceInfo("_http._tcp.local.",
                                self.service_name,
                                socket.inet_aton(util.get_ip()), prefs.get_port(), 0, 0,
                                desc, "somehost.local.")
        self.zc = Zeroconf()
        self.zc.register_service(self.info)

    # def set_prefs(self, app_nick, path):
    #     self.save_location = path
    #     self.file_receiver.save_path = path

    #     self.app_nick = app_nick

    #     print("Save path: %s" % self.save_location)
    #     print("Visible as '%s'" % self.app_nick)

    # ########################### Server ###################
    # @util._async
    # def serve_forever(self):
    #     self.register_zeroconf()
    #     addr = ("0.0.0.0", self.port)

    #     with xmlrpc.server.SimpleXMLRPCServer(addr, allow_none=True, logRequests=False) as server:
    #         print("Listening on", addr)
    #         server.register_function(self._get_nick, "get_nick")
    #         server.register_function(self._update_remote_info, "update_remote_info")
    #         server.register_function(self._files_exist, "files_exist")
    #         server.register_function(self._receive, "receive")
    #         server.register_function(self._permission_needed, "permission_needed")
    #         server.register_function(self._get_permission, "get_permission")
    #         server.register_function(self._prevent_overwriting, "prevent_overwriting")
    #         server.register_function(self._abort_transfer, "abort_transfer")
    #         server.register_function(self._abort_request, "abort_request")
    #         server.register_function(self._update_progress, "update_progress")
    #         server.register_function(self._ping, "ping")
    #         server.serve_forever()

    # def _get_nick(self):
    #     return self.app_nick

    # def _update_remote_info(self, sender, sender_nick):
    #     try:
    #         peer = self.peer_list[sender]
    #         peer.update_proxy_nick(sender_nick)
    #     except KeyError:
    #         print("Received change notification for unknown proxy - what's up: %s" % sender)
    #         return False

    #     return True

    # def _files_exist(self, base_names):
    #     for name in base_names:
    #         path = os.path.join(self.save_location, name)
    #         print("(server side) Checking if file or folder %s already exists." % (path,))
    #         if GLib.file_test(path, GLib.FileTest.EXISTS):
    #             return True

    #     return False

    # def _receive(self, sender, basename, folder=False, symlink_target=None, serial=0, checksum=None, binary_data=None):
    #     # print("receive data for file %s from %s (serial %d) - folder:%d symlink:%s" % (basename, sender, serial, folder, symlink_target))

    #     return self.file_receiver.receive(basename, folder, symlink_target, serial, checksum, binary_data)

    # def _permission_needed(self):
    #     return prefs.require_permission_for_transfer()

    # def _get_permission(self, name, sender_nick, size_str, count_str, time_str):
    #     # XML RPC can't transfer longs, so we stringify for transfer
    #     count = int(count_str)
    #     size = int(size_str)

    #     for req in self.permission_requests:
    #         if req.name == name:
    #             if req.time_str == time_str:
    #                 if req.permission != util.TRANSFER_REQUEST_PENDING:
    #                     self.permission_requests.remove(req)
    #                 return req.permission

    #     request = PermissionRequest(name, sender_nick, size, count, time_str)

    #     if not self.have_free_space(request):
    #         return util.TRANSFER_REQUEST_DISKFULL

    #     self.permission_requests.append(request)

    #     try:
    #         peer = self.peer_list[name]
    #         GLib.idle_add(peer.ask_my_permission, request, priority=GLib.PRIORITY_DEFAULT)
    #     except KeyError:
    #         print("Received transfer request for unknown proxy - what's up: %s" % name)
    #         return False

    #     self.emit("grab-attention")

    #     return util.TRANSFER_REQUEST_PENDING

    # def _prevent_overwriting(self):
    #     return prefs.prevent_overwriting()

    # def _abort_transfer(self, name):
    #     print("Server side: Abort transfer from", name)
    #     pass

    # def _abort_request(self, name, time_str):
    #     for req in self.permission_requests:
    #         if req.name == name:
    #             if req.time_str == time_str:
    #                 req.permission = util.TRANSFER_REQUEST_CANCELLED

    #                 try:
    #                     peer = self.peer_list[name]
    #                     GLib.idle_add(peer.receive_request_withdrawn, req, priority=GLib.PRIORITY_DEFAULT)
    #                 except KeyError:
    #                     print("Received transfer request for unknown proxy - what's up: %s" % name)

    #     return True

    # def _update_progress(self, name, progress, speed, time_left, finished, error):
    #     GLib.idle_add(self._update_progress_at_idle, name, progress, speed, time_left, finished, error, priority=GLib.PRIORITY_DEFAULT)
    #     return True

    # def _ping(self):
    #     return "pong"
    # ################################ / Server ################################

    # def _update_progress_at_idle(self, name, progress, speed, time_left, finished, error):
    #     try:
    #         peer = self.peer_list[name]
    #         peer.receive_progress_callback(progress, speed, time_left, finished, error)
    #     except KeyError:
    #         print("Received progress for unknown proxy - what's up: %s" % name)

    #     return False

    # def have_free_space(self, request):
    #     save_file = Gio.File.new_for_path(self.save_location)

    #     try:
    #         info = save_file.query_filesystem_info(Gio.FILE_ATTRIBUTE_FILESYSTEM_FREE, None)
    #     except GLib.Error as e:
    #         print("Unable to check free space in save location (%s), but proceeding anyhow" % self.save_location)
    #         return True

    #     free = info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_FILESYSTEM_FREE)

    #     # I guess we could have exactly 0 bytes free, but I think you'd have larger problems.  I want to make sure
    #     # here that we don't fail because we didn't get a valid number.
    #     if free == 0:
    #         return True
    #     print("Need: %s, have %s" % (GLib.format_size(request.size), GLib.format_size(free)))
    #     return request.size < free

    # def close(self):
    #     self.file_receiver.stop()
    #     self.zc.unregister_service(self.info)

class ProxyItem(GObject.Object):
    __gsignals__ = {
        'nick-changed': (GObject.SignalFlags.RUN_LAST, None, (str,)),
        'server-connectivity-changed': (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self, app_name, app_nick, proxy_name, proxy, proxy_ip, proxy_port):
        super(ProxyItem, self).__init__()
        self.app_name = app_name
        self.app_nick = app_nick
        self.proxy = proxy
        self.proxy_name = proxy_name
        self.proxy_nick = ""
        self.proxy_ip = proxy_ip
        self.proxy_port = proxy_port
        self.sort_key = proxy_name
        self.send_stat_delay_timer = 0
        self.receive_stat_delay_timer = 0
        self.dropping = False
        self.sort_order = 0

        # Don't allow the local user to drop more files if we're already waiting on a previous request
        self.blocking_new_sends = False

        self.active_receive_request = None

        self.builder = Gtk.Builder.new_from_file(os.path.join(config.pkgdatadir, "warp-window.ui"))
        self.widget =self.builder.get_object("proxy_widget")
        self.page_stack = self.builder.get_object("page_stack")
        self.status_page = self.builder.get_object("status_page")
        self.nick_label = self.builder.get_object("nick_label")
        self.progress_box = self.builder.get_object("progress_box")
        self.send_progress_bar = self.builder.get_object("send_progress_bar")
        self.receive_progress_bar = self.builder.get_object("receive_progress_bar")
        self.sender_awaiting_approval_label = self.builder.get_object("sender_awaiting_approval_label")
        self.sender_awaiting_approval_cancel_button = self.builder.get_object("sender_awaiting_approval_cancel_button")
        self.send_file_menu_button = self.builder.get_object("send_file_menu_button")
        self.req_transfer_label = self.builder.get_object("req_transfer_label")
        self.problem_info_label = self.builder.get_object("problem_info_label")
        self.problem_more_info_label = self.builder.get_object("problem_more_info_label")
        self.connecting_label = self.builder.get_object("connecting_label")

        self.sender_awaiting_approval_cancel_button.connect("clicked", self.cancel_send_request)

        self.recent_menu = Gtk.RecentChooserMenu(show_tips=True, sort_type=Gtk.RecentSortType.MRU, show_not_found=False)
        self.recent_menu.connect("item-activated", self.recent_item_selected)
        self.send_file_menu_button.set_popup(self.recent_menu)
        self.recent_menu.add(Gtk.SeparatorMenuItem(visible=True))
        picker = Gtk.MenuItem(label=_("Browse..."), visible=True)
        picker.connect("activate", self.open_file_picker)
        self.recent_menu.add(picker)

        self.proxy.lock = threading.Lock()
        self.file_sender = transfers.FileSender(self.app_name, self.proxy_name, self.proxy_nick, self.proxy, self.send_progress_callback)

        entry = Gtk.TargetEntry.new("text/uri-list",  0, 0)
        self.status_page.drag_dest_set(Gtk.DestDefaults.ALL,
                                       (entry,),
                                       Gdk.DragAction.COPY)
        self.status_page.connect("drag-drop", self.on_drag_drop)
        self.status_page.connect("drag-data-received", self.on_drag_data_received)
        self.status_page.connect("drag-motion", self.on_drag_motion)

        self.show_connecting()

        # self.pulse = pulse.Pulse(self.proxy, self.proxy_ip, self.proxy_port)
        # self.pulse.connect("state-changed", self.pulse_state_changed)
        # self.pulse.start()

        self.hide_receive_stats()
        self.hide_send_stats()
        self.widget.show_all()

    def pulse_state_changed(self, pulse, online, error, nick):
        if online:
            self.page_stack.set_visible_child_name("status")

            if nick:
                self.update_proxy_nick(nick)
            return

        self.page_stack.set_visible_child_name("problems")
        self.problem_info_label.set_markup(_("Problem communicating with <b>%s</b>.  Check for connectivity or firewall issues." \
                                           % self.proxy_nick))
        self.problem_more_info_label.set_text(_("Details: %s") % str(error) if error else _("Unknown"))

    @util._idle
    def show_connecting(self):
        self.page_stack.set_visible_child_name("connecting")

        try:
            hostname = socket.gethostbyaddr(self.proxy_ip)
        except:
            hostname = self.proxy_ip

        self.connecting_label.set_markup(_("Connecting to <b>%s</b>") % hostname)

    def recent_item_selected(self, recent_chooser, data=None):
        uri = self.recent_menu.get_current_uri()

        self.file_sender.send_files([uri])

    def open_file_picker(self, button, data=None):
        dialog = util.create_file_and_folder_picker()

        res = dialog.run()

        if res == Gtk.ResponseType.ACCEPT:
            uri_list = dialog.get_uris()
            self.file_sender.send_files(uri_list)

        dialog.destroy()

    def update_sort_key(self):
        valid = GLib.utf8_make_valid(self.proxy_nick, -1)
        self.sort_key = GLib.utf8_collate_key(valid.lower(), -1)

    def destroy(self):
        self.destroyed = True # kill heartbeat

        self.widget.destroy()
        self.file_sender.stop()
        self.pulse.destroy()

    ###################### Application calls #######################

    # Our app (local) nick has changed, (for now just our nick) - tell the remote server so our name on that end is updated
    @util._async
    def update_app_nick(self, app_nick):
        self.app_nick = app_nick
        with self.proxy.lock:
            self.proxy.update_remote_info(self.app_name, self.app_nick)

    # The application wants to know if we're currently in the middle of anything
    def transfer_active(self):
        return self.file_sender.get_active()

    ###################### / Application calls #######################

    #################### DND Handler ################

    def on_drag_motion(self, widget, context, x, y, time):
        if not self.pulse.online:
            print("noooooooot online")
            Gdk.drag_status(context, 0, time)
            return

    def on_drag_drop(self, widget, context, x, y, time, data=None):
        atom =  widget.drag_dest_find_target(context, None)
        self.dropping = True
        widget.drag_get_data(context, atom, time)

    def on_drag_data_received(self, widget, context, x, y, data, info, time, user_data=None):
        if not self.pulse.online:
            print("not online")
            Gdk.drag_status(context, 0, time)
            return

        if not self.dropping:
            if self.blocking_new_sends:
                Gdk.drag_status(context, 0, time)
            else:
                Gdk.drag_status(context, Gdk.DragAction.COPY, time)
            return
        if data:
            if context.get_selected_action() == Gdk.DragAction.COPY:
                uris = data.get_uris()
                self.file_sender.send_files(uris)

        Gtk.drag_finish(context, True, False, time)
        self.dropping = False
    #################### / DND Handler ####################

    ##################### Progress widget management ##########################
    # These methods control the visibility of the progress bars.  There's a delay for showing them
    # because on short transfers, they don't last long enough to even report progress, so don't bother
    # showing anything.
    def queue_send_showing_stats(self):
        if self.send_stat_delay_timer > 0:
            GLib.source_remove(self.send_stat_delay_timer)

        self.page_stack.set_visible_child_name("status")
        self.send_stat_delay_timer = GLib.timeout_add(500, self.show_send_stats_timeout)

    def show_send_stats_timeout(self, data=None):
        self.send_stat_delay_timer = 0
        self.send_progress_bar.show()

    def hide_send_stats(self):
        if self.send_stat_delay_timer > 0:
            GLib.source_remove(self.send_stat_delay_timer)
            self.send_stat_delay_timer = 0

        self.send_progress_bar.set_fraction(0)
        self.send_progress_bar.set_text(_("Sending"))
        self.send_progress_bar.hide()

    def queue_receive_showing_stats(self):
        if self.receive_stat_delay_timer > 0:
            GLib.source_remove(self.receive_stat_delay_timer)

        self.receive_stat_delay_timer = GLib.timeout_add(500, self.show_receive_stats_timeout)

    def show_receive_stats_timeout(self, data=None):
        self.receive_stat_delay_timer = 0
        self.receive_progress_bar.show()

    def hide_receive_stats(self):
        if self.receive_stat_delay_timer > 0:
            GLib.source_remove(self.receive_stat_delay_timer)
            self.receive_stat_delay_timer = 0
        self.receive_progress_bar.set_fraction(0)
        self.receive_progress_bar.set_text(_("Receiving"))
        self.receive_progress_bar.hide()
    ####################### /Progress widget management ##############

    ####################### Local client calls #####################
    # These calls are initiated locally, to keep the local representation of the peer up-to-date

    # You are in the process of sending, or attempting to send, files.
    def send_progress_callback(self, data=util.ProgressCallbackInfo()):
        cb_info = data
        if cb_info.transfer_starting or cb_info.is_fail_state():
            self.page_stack.set_visible_child_name("status")
            if cb_info.transfer_refused:
                self.show_refused_message()
            elif cb_info.transfer_exists:
                self.show_exists_message(cb_info.count)
            elif cb_info.transfer_diskfull:
                self.show_diskfull_message(cb_info.size)
            elif cb_info.error:
                self.show_send_error_message(cb_info.error)
            return

        if not self.send_progress_bar.get_visible() and not cb_info.finished and not cb_info.sender_awaiting_approval:
            self.queue_send_showing_stats()

        if cb_info.progress > 1.0:
            cb_info.progress = 1.0

        self.send_progress_bar.set_fraction(cb_info.progress)
        if cb_info.speed and cb_info.time_left:
            self.send_progress_bar.set_text(_("Sending - %s - %s" % (cb_info.time_left, cb_info.speed)))
            return

        if cb_info.finished:
            self.hide_send_stats()
            return

        if cb_info.sender_awaiting_approval:
            self.wait_for_server_approval(cb_info)
            return

    def wait_for_server_approval(self, cb_info):
        self.page_stack.set_visible_child_name("sender_awaiting_approval")
        self.blocking_new_sends = True

        markup = gettext.ngettext("Waiting to send %d file",
                                  "Waiting to send %d files", cb_info.count) \
                                  % (cb_info.count,)
        self.sender_awaiting_approval_label.set_markup(markup)

    def cancel_send_request(self, button, data=None):
        self.file_sender.cancel_send_request()
        self.page_stack.set_visible_child_name("status")

    ####################### / Local client calls #####################

    ############ Server calls (these are for interaction with the local user) ###############

    # The remote peer has begun sending you files.  This is his periodic progress report so you
    # can update the information on your local status widget for that peer
    def receive_progress_callback(self, progress, speed, time_left, finished=False, error=None):
        # print("Receive progress callback - server", progress, speed, time_left)
        if not self.receive_progress_bar.get_visible():
            self.queue_receive_showing_stats()

        if progress > 1.0:
            progress = 1.0

        self.receive_progress_bar.set_fraction(progress)

        if speed and time_left:
            self.receive_progress_bar.set_text(_("Receiving - %s - %s" % (time_left, speed)))

        if finished:
            self.hide_receive_stats()
            if error:
                self.show_receive_error_message(error)

    # The remote peer wants to send files, and your pref is to be able to approve every transfer
    # This sets up the UI to let you know, switching to the query view with approve/disapprove buttons
    def ask_my_permission(self, request):
        self.active_receive_request = request

        markup = gettext.ngettext("<b>%s</b> wants to send you %d file (%s)",
                                  "<b>%s</b> wants to send you %d files (%s)", request.count) \
                                  % (self.proxy_nick, request.count, GLib.format_size(request.size))

        self.widget.get_toplevel().present()
        dialog = Gtk.MessageDialog(title=_("Incoming file"),
                                   # parent=self.widget.get_toplevel(),
                                   destroy_with_parent=True,
                                   message_type=Gtk.MessageType.QUESTION,
                                   use_markup=True,
                                   modal=True,
                                   text=markup)
        dialog.add_buttons(_("Refuse"), Gtk.ResponseType.CANCEL,
                           _("Accept"), Gtk.ResponseType.ACCEPT)

        self.active_receive_request.permission_dialog = dialog

        res = dialog.run()
        dialog.destroy()

        # request may have been cancelled.  Destroying the dialog elsewhere will still return a code,
        # quit early if we're no longer tracking the request (see self.receive_request_withdrawn)
        if not self.active_receive_request:
            return

        if res == Gtk.ResponseType.ACCEPT:
            self.active_receive_request.permission = util.TRANSFER_REQUEST_GRANTED
        else:
            self.active_receive_request.permission = util.TRANSFER_REQUEST_REFUSED

        self.active_receive_request = None

    def show_refused_message(self):
        self.widget.get_toplevel().present()
        dialog = Gtk.MessageDialog(title=_("Transfer Aborted"),
                                   # parent=self.widget.get_toplevel(),
                                   destroy_with_parent=True,
                                   message_type=Gtk.MessageType.WARNING,
                                   use_markup=True,
                                   modal=True,
                                   text=_("<b>%s</b> would not accept your request") % self.proxy_nick)
        dialog.add_buttons(_("Dismiss"), Gtk.ResponseType.CLOSE)

        res = dialog.run()
        dialog.destroy()

        self.active_receive_request = None

    def show_exists_message(self, count):
        self.widget.get_toplevel().present()

        text = gettext.ngettext("File already exists, and overwriting is not currently permitted",
                                "Files already exist, and overwriting is not currently permitted", count)

        dialog = Gtk.MessageDialog(title=_("Transfer to %s Aborted") % self.proxy_nick,
                                   # parent=self.widget.get_toplevel(),
                                   destroy_with_parent=True,
                                   message_type=Gtk.MessageType.WARNING,
                                   text=text)
        dialog.add_buttons(_("Dismiss"), Gtk.ResponseType.CLOSE)

        res = dialog.run()
        dialog.destroy()

    def show_diskfull_message(self, size):
        self.widget.get_toplevel().present()

        text = _("The target machine (<b>%s</b>) does not have enough disk space to complete the transfer (approximately %s required)" \
                 % (self.proxy_nick, GLib.format_size(size)))

        dialog = Gtk.MessageDialog(title=_("Insufficient Disk Space"),
                                   # parent=self.widget.get_toplevel(),
                                   destroy_with_parent=True,
                                   message_type=Gtk.MessageType.WARNING,
                                   use_markup=True,
                                   text=text)
        dialog.add_buttons(_("Dismiss"), Gtk.ResponseType.CLOSE)

        res = dialog.run()
        dialog.destroy()

    def show_send_error_message(self, error):
        self.widget.get_toplevel().present()

        text = _("An error occurred during the file transfer to <b>%s</b>: %s" % (self.proxy_nick, error))

        dialog = Gtk.MessageDialog(title=_("Aborted File Transfer"),
                                   # parent=self.widget.get_toplevel(),
                                   destroy_with_parent=True,
                                   message_type=Gtk.MessageType.ERROR,
                                   use_markup=True,
                                   text=text)
        dialog.add_buttons(_("Dismiss"), Gtk.ResponseType.CLOSE)

        res = dialog.run()
        dialog.destroy()

    def show_receive_error_message(self, error):
        self.widget.get_toplevel().present()

        text = _("An error occurred while receiving a file from <b>%s</b>: %s" % (self.proxy_nick, error))

        dialog = Gtk.MessageDialog(title=_("Aborted File Transfer"),
                                   # parent=self.widget.get_toplevel(),
                                   destroy_with_parent=True,
                                   message_type=Gtk.MessageType.ERROR,
                                   use_markup=True,
                                   text=text)
        dialog.add_buttons(_("Dismiss"), Gtk.ResponseType.CLOSE)

        res = dialog.run()
        dialog.destroy()

    # The remote that initiated a transfer request has canceled it
    def receive_request_withdrawn(self, request):
        if request != self.active_receive_request:
            print("proxy: unknown request cancelled by remote")

        self.active_receive_request = None
        request.permission_dialog.destroy()

        self.page_stack.set_visible_child_name("status")

    # The remote peer has updated their info, and told our server about it, they
    # want us to fetch the new info from the server
    def update_proxy_nick(self, proxy_nick):
        new_nick = proxy_nick

        if self.proxy_nick != new_nick:
            self.proxy_nick = new_nick
            self.update_sort_key()
            self.emit("nick-changed", new_nick)

            self.nick_label.set_markup("<b>%s</b>" % self.proxy_nick)
            self.file_sender.peer_nick = self.proxy_nick

    ######################## /Server Calls#####################################





























ALL_BUTTONS = ("transfer_accept", \
               "transfer_decline", \
               "transfer_cancel_request", \
               "transfer_retry", \
               "transfer_pause", \
               "transfer_resume", \
               "transfer_stop", \
               "transfer_remove", \
               "transfer_open_folder")

INIT_BUTTONS = ()
PERM_TO_SEND_BUTTONS = ("transfer_cancel_request",)
PERM_TO_ACCEPT_BUTTONS = ("transfer_accept", "transfer_decline")
TRANSFER_SENDING_BUTTONS = ("transfer_pause", "transfer_stop")
TRANSFER_RECEIVING_BUTTONS = ("transfer_stop",)
TRANSFER_PAUSED_SENDING_BUTTONS = ("transfer_resume", "transfer_stop")
TRANSFER_PAUSED_RECEIVING_BUTTONS = ()
TRANSFER_FAILED_BUTTONS = ("transfer_retry", "transfer_remove")
TRANSFER_CANCELLED_BUTTONS = ("transfer_remove",)
TRANSFER_COMPLETED_BUTTONS = ("transfer_remove", "transfer_open_folder")

class TransferItem(GObject.Object):
    # __gsignals__ = {
    #     'update-sort': (GObject.SignalFlags.RUN_LAST, None, ())
    # }

    def __init__(self, op):
        super(TransferItem, self).__init__()

        self.op = op

        self.op.connect("progress-changed", self.update_progress)

        self.builder = Gtk.Builder.new_from_file(os.path.join(config.pkgdatadir, "warp-window.ui"))
        self.item = self.builder.get_object("transfer_item")
        self.direction_image = self.builder.get_object("transfer_direction_image")
        self.mime_image = self.builder.get_object("transfer_mime_image")
        self.transfer_description_label = self.builder.get_object("transfer_description_label")
        self.transfer_size_label = self.builder.get_object("transfer_size_label")
        self.op_status_stack = self.builder.get_object("op_status_stack")
        self.op_transfer_status_message = self.builder.get_object("op_transfer_status_message")
        self.op_progress_bar = self.builder.get_object("op_transfer_progress_bar")
        self.accept_button =  self.builder.get_object("transfer_accept")
        self.decline_button =  self.builder.get_object("transfer_decline")
        self.cancel_button =  self.builder.get_object("transfer_cancel_request")
        self.retry_button =  self.builder.get_object("transfer_retry")
        self.pause_button =  self.builder.get_object("transfer_pause")
        self.stop_button =  self.builder.get_object("transfer_stop")
        self.remove_button =  self.builder.get_object("transfer_remove")
        self.folder_button =  self.builder.get_object("transfer_open_folder")

        self.accept_button.connect("clicked", self.accept_button_clicked)
        self.decline_button.connect("clicked", self.decline_button_clicked)
        self.cancel_button.connect("clicked", self.cancel_button_clicked)
        self.retry_button.connect("clicked", self.retry_button_clicked)
        self.pause_button.connect("clicked", self.pause_button_clicked)
        self.stop_button.connect("clicked", self.stop_button_clicked)
        self.remove_button.connect("clicked", self.remove_button_clicked)
        self.folder_button.connect("clicked", self.folder_button_clicked)

        self.refresh_status_widgets()
        self.refresh_buttons_and_icons()

    def update_progress(self, op):
        self.op_progress_bar.set_fraction(self.op.progress)
        self.op_progress_bar.set_text(self.op.progress_text)

    def set_visible_buttons(self, vis_buttons):
        for name in ALL_BUTTONS:
            self.builder.get_object(name).props.visible = False
        for name in vis_buttons:
            self.builder.get_object(name).props.visible = True

    def refresh_status_widgets(self):
        if self.op.status in (OpStatus.TRANSFERRING, OpStatus.PAUSED):
            self.op_progress_bar.set_fraction(self.op.progress)
            self.op_progress_bar.set_text(self.op.progress_text)
        if self.op.status == OpStatus.WAITING_PERMISSION:
            if self.op.direction == TransferDirection.TO_REMOTE_MACHINE:
                self.op_transfer_status_message.set_text(_("Waiting for approval"))
            else:
                self.op_transfer_status_message.set_text(_("Waiting for your approval"))
        elif (self.op.status == OpStatus.CANCELLED_PERMISSION_BY_SENDER and isinstance(self.op, SendOp)) or \
            (self.op.status == OpStatus.CANCELLED_PERMISSION_BY_RECEIVER and isinstance(self.op, ReceiveOp)):
            self.op_transfer_status_message.set_text(_("Request cancelled"))
        elif (self.op.status == OpStatus.CANCELLED_PERMISSION_BY_SENDER and isinstance(self.op, ReceiveOp)):
            self.op_transfer_status_message.set_text(_("Request cancelled by %s") % self.op.sender_name)
        elif (self.op.status == OpStatus.CANCELLED_PERMISSION_BY_RECEIVER and isinstance(self.op, SendOp)):
            self.op_transfer_status_message.set_text(_("Request cancelled by %s") % self.op.receiver_name)
        elif self.op.status == OpStatus.STOPPED_BY_SENDER:
            self.op_transfer_status_message.set_text(_("Cancelled"))
        elif self.op.status == OpStatus.STOPPED_BY_RECEIVER:
            self.op_transfer_status_message.set_text(_("Cancelled by %s") % util.accounts.get_real_name())
        elif self.op.status == OpStatus.FAILED:
            self.op_transfer_status_message.set_text(_("Transfer failed"))
        elif self.op.status == OpStatus.FINISHED:
            self.op_transfer_status_message.set_text(_("Completed"))

    def refresh_buttons_and_icons(self):
        if self.op.direction == TransferDirection.TO_REMOTE_MACHINE:
            self.direction_image.set_from_icon_name("go-up-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        else:
            self.direction_image.set_from_icon_name("go-down-symbolic", Gtk.IconSize.LARGE_TOOLBAR)

        self.mime_image.set_from_gicon(self.op.gicon, Gtk.IconSize.LARGE_TOOLBAR)
        self.transfer_size_label.set_text(self.op.size_string)
        self.transfer_description_label.set_text(self.op.description)

        if self.op.status in (OpStatus.INIT, OpStatus.CALCULATING):
            self.op_status_stack.set_visible_child_name("calculating")
            self.set_visible_buttons(INIT_BUTTONS)
        elif self.op.status == OpStatus.WAITING_PERMISSION:
            self.op_status_stack.set_visible_child_name("message")

            if self.op.direction == TransferDirection.TO_REMOTE_MACHINE:
                self.set_visible_buttons(PERM_TO_SEND_BUTTONS)
            else:
                self.set_visible_buttons(PERM_TO_ACCEPT_BUTTONS)
        elif self.op.status == OpStatus.TRANSFERRING:
            self.op_status_stack.set_visible_child_name("progress-bar")

            if self.op.direction == TransferDirection.TO_REMOTE_MACHINE:
                self.set_visible_buttons(TRANSFER_SENDING_BUTTONS)
            else:
                self.set_visible_buttons(TRANSFER_RECEIVING_BUTTONS)
        elif self.op.status == OpStatus.PAUSED:
            self.op_status_stack.set_visible_child_name("progress-bar")

            if self.op.direction == TransferDirection.TO_REMOTE_MACHINE:
                self.set_visible_buttons(TRANSFER_PAUSED_SENDING_BUTTONS)
            else:
                self.set_visible_buttons(TRANSFER_PAUSED_RECEIVING_BUTTONS)
        elif self.op.status == OpStatus.FAILED:
            self.op_status_stack.set_visible_child_name("message")

            self.set_visible_buttons(TRANSFER_FAILED_BUTTONS)
        elif self.op.status == OpStatus.FINISHED:
            self.op_status_stack.set_visible_child_name("message")

            self.set_visible_buttons(TRANSFER_COMPLETED_BUTTONS)
        elif self.op.status in (OpStatus.CANCELLED_PERMISSION_BY_SENDER,
                                OpStatus.CANCELLED_PERMISSION_BY_RECEIVER,
                                OpStatus.STOPPED_BY_SENDER,
                                OpStatus.STOPPED_BY_RECEIVER):
            self.op_status_stack.set_visible_child_name("message")

            self.set_visible_buttons(TRANSFER_CANCELLED_BUTTONS)


    def accept_button_clicked(self, button):
        self.op.accept_transfer()

    def decline_button_clicked(self, button):
        self.op.decline_transfer_request()

    def cancel_button_clicked(self, button):
        self.op.cancel_transfer_request()

    def retry_button_clicked(self, button):
        self.op.retry_transfer()

    def pause_button_clicked(self, button):
        pass

    def stop_button_clicked(self, button):
        self.op.stop_transfer()

    def remove_button_clicked(self, button):
        self.op.remove_transfer()

    def folder_button_clicked(self, button):
        util.open_save_folder()

    def do_dispose(self):
        # self.remote_machine.disconnect(self.remote_machine_changed_id)
        # self.remote_machine_changed_id = 0

        print("(dispose) Disconnecting op row from TransferOp")
        GObject.Object.do_dispose(self)

class RemoteMachineButton(GObject.Object):
    __gsignals__ = {
        'update-sort': (GObject.SignalFlags.RUN_LAST, None, ()),
        'clicked': (GObject.SignalFlags.RUN_LAST, None, ()),
        'files-dropped': (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self, remote_machine):
        super(RemoteMachineButton, self).__init__()

        self.remote_machine = remote_machine
        self.remote_machine_changed_id = self.remote_machine.connect("machine-info-changed",
                                                                     self._update_machine_info)

        self.builder = Gtk.Builder.new_from_file(os.path.join(config.pkgdatadir, "warp-window.ui"))
        self.button = self.builder.get_object("overview_user_button")
        self.avatar_image = self.builder.get_object("overview_user_avatar_image")
        self.display_name_label = self.builder.get_object("overview_user_display_name")
        self.hostname_label = self.builder.get_object("overview_user_hostname")
        self.ip_label = self.builder.get_object("overview_user_ip")
        self.favorite_image = self.builder.get_object("overview_user_favorite")

        self.button.connect("clicked", lambda button: self.emit("clicked"))

        # DND
        self.drop_pending = False
        entry = Gtk.TargetEntry.new("text/uri-list",  0, 0)
        self.button.drag_dest_set(Gtk.DestDefaults.ALL,
                                  (entry,),
                                  Gdk.DragAction.COPY)
        self.button.connect("drag-drop", self.on_drag_drop)
        self.button.connect("drag-data-received", self.on_drag_data_received)
        # /DND

        # Convenience for window to sort and remove buttons
        self.button.remote_machine = remote_machine
        self.button.connect_name = remote_machine.connect_name

    def _update_machine_info(self, remote_machine):
        self.display_name_label.set_text(self.remote_machine.display_name)
        self.hostname_label.set_text(self.remote_machine.hostname)
        self.ip_label.set_text(self.remote_machine.ip_address)

        if self.remote_machine.avatar_surface:
            self.avatar_image.set_from_surface(self.remote_machine.avatar_surface)
        else:
            self.avatar_image.clear()

        self.refresh_favorite_icon()

        self.emit("update-sort")
        self.button.show_all()

    def refresh_favorite_icon(self):
        if self.remote_machine.favorite:
            self.favorite_image.set_from_icon_name("starred-symbolic", Gtk.IconSize.BUTTON)
        elif self.remote_machine.recent_time != 0:
            self.favorite_image.set_from_icon_name("document-open-recent-symbolic", Gtk.IconSize.BUTTON)
        else:
            self.favorite_image.clear()

    # def on_drag_motion(self, widget, context, x, y, time):
    #     pass
    #     # if not self.pulse.online:
    #     #     Gdk.drag_status(context, 0, time)
    #     #     return

    def on_drag_drop(self, widget, context, x, y, time, data=None):
        atom =  widget.drag_dest_find_target(context, None)
        self.drop_pending = True
        widget.drag_get_data(context, atom, time)

    def on_drag_data_received(self, widget, context, x, y, data, info, time, user_data=None):
        # if not self.pulse.online:
        #     Gdk.drag_status(context, 0, time)
        #     return

        if not self.drop_pending:
            Gdk.drag_status(context, Gdk.DragAction.COPY, time)
            return

        if data:
            if context.get_selected_action() == Gdk.DragAction.COPY:
                uris = data.get_uris()
                self.emit("files-dropped")
                self.remote_machine.send_files(uris)

        Gtk.drag_finish(context, True, False, time)
        self.drop_pending = False

    def do_dispose(self):
        self.remote_machine.disconnect(self.remote_machine_changed_id)
        self.remote_machine_changed_id = 0

        print("(dispose) Disconnecting overview remote button from RemoteMachine")
        GObject.Object.do_dispose(self)

class WarpWindow(GObject.Object):
    __gsignals__ = {
        'exit': (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self):
        super(WarpWindow, self).__init__()

        self.current_selected_remote_machine = None
        self.drop_pending = False

        # overview
        self.builder = Gtk.Builder.new_from_file(os.path.join(config.pkgdatadir, "warp-window.ui"))
        self.window =self.builder.get_object("window")
        self.view_stack = self.builder.get_object("view_stack")
        self.menu_button = self.builder.get_object("menu_button")
        self.user_list_box = self.builder.get_object("user_list_box")
        self.search_entry = self.builder.get_object("search_entry")
        self.app_display_name_label = self.builder.get_object("app_display_name")
        self.app_ip_label = self.builder.get_object("app_ip")
        self.app_hostname_label = self.builder.get_object("app_hostname")
        self.something_wrong_box = self.builder.get_object("no_clients")

        # user view
        self.user_back_button = self.builder.get_object("user_back")
        self.user_back_button.connect("clicked", self.back_to_overview)
        self.user_favorite_button = self.builder.get_object("user_favorite")
        self.user_favorite_button.connect("clicked", self.user_favorite_clicked)
        self.user_favorite_image = self.builder.get_object("user_favorite_image")
        self.user_avatar_image = self.builder.get_object("user_avatar_image")
        self.user_display_name_label = self.builder.get_object("user_display_name")
        self.user_hostname_label = self.builder.get_object("user_hostname")
        self.user_ip_label = self.builder.get_object("user_ip")
        self.user_op_list = self.builder.get_object("user_op_list")

        self.view_stack.set_visible_child_name("startup")

        # Hamburger menu
        menu = Gtk.Menu()
        item = Gtk.MenuItem(label=_("Open save folder"))
        item.connect("activate", self.on_open_location_clicked)
        menu.add(item)

        item = Gtk.MenuItem(label=_("Preferences"))
        item.connect("activate", self.open_preferences)
        menu.add(item)

        item = Gtk.MenuItem(label=_("Quit"))
        item.connect("activate", self.menu_quit)
        menu.add(item)
        menu.show_all()

        self.menu_button.set_popup(menu)
        # end Hamburger menu

        # DND
        self.drop_pending = False
        entry = Gtk.TargetEntry.new("text/uri-list",  0, 0)
        self.user_op_list.drag_dest_set(Gtk.DestDefaults.ALL,
                                        (entry,),
                                        Gdk.DragAction.COPY)
        self.user_op_list.connect("drag-drop", self.on_drag_drop)
        self.user_op_list.connect("drag-data-received", self.on_drag_data_received)
        # /DND

        # self.window.connect("delete-event",
        #                     lambda widget, event: widget.hide_on_delete())

        self.window.connect("delete-event",
                            lambda widget, event: self.emit("exit"))

        self.update_local_user_info()

    def on_drag_drop(self, widget, context, x, y, time, data=None):
        atom =  widget.drag_dest_find_target(context, None)
        self.drop_pending = True
        widget.drag_get_data(context, atom, time)

    def on_drag_data_received(self, widget, context, x, y, data, info, time, user_data=None):
        if not self.drop_pending:
            Gdk.drag_status(context, Gdk.DragAction.COPY, time)
            return

        if data:
            if context.get_selected_action() == Gdk.DragAction.COPY:
                uris = data.get_uris()
                self.current_selected_remote_machine.send_files(uris)

        Gtk.drag_finish(context, True, False, time)
        self.drop_pending = False

    def update_local_user_info(self):
        self.app_display_name_label.set_text(prefs.get_nick())
        self.app_hostname_label.set_text(util.get_hostname())
        self.app_ip_label.set_text(util.get_ip())

    def menu_quit(self, widget, data=None):
        self.emit("exit")

    def on_open_location_clicked(self, widget, data=None):
        util.open_save_folder()

    def grab_user_attention(self, server):
        self.window.set_urgency_hint(True)

    def open_preferences(self, menuitem, data=None):
        w = prefs.Preferences()
        w.set_transient_for(self.window)
        w.present()

    def add_remote_button(self, remote_machine):
        self.view_stack.set_visible_child_name("overview")

        button = RemoteMachineButton(remote_machine)
        button.connect("update-sort", self.sort_buttons)
        button.connect("files-dropped", self.remote_machine_files_dropped)
        button.connect("clicked", self.remote_machine_button_clicked)

        self.user_list_box.add(button.button)
        self.sort_buttons()

    def remove_remote_button(self, remote_machine):
        buttons = self.user_list_box.get_children()

        for child in buttons:
            if child.connect_name == remote_machine.connect_name:
                self.user_list_box.remove(child)

        if len(self.user_list_box.get_children()) == 0:
            self.view_stack.set_visible_child_name("no-remotes")

        self.back_to_overview()
        self.sort_buttons()

    def remote_machine_button_clicked(self, button):
        self.switch_to_user_view(button.remote_machine)

    def remote_machine_files_dropped(self, button):
        self.switch_to_user_view(button.remote_machine)

    def switch_to_user_view(self, remote_machine):
        self.view_stack.set_visible_child_name("user")
        self.current_selected_remote_machine = remote_machine

        self.refresh_remote_machine_view()

    def refresh_remote_machine_view(self):
        if self.view_stack.get_visible_child_name() != "user":
            return

        self.user_display_name_label.set_text(self.current_selected_remote_machine.display_name)
        self.user_hostname_label.set_text(self.current_selected_remote_machine.hostname)
        self.user_ip_label.set_text(self.current_selected_remote_machine.ip_address)
        self.user_avatar_image.set_from_surface(self.current_selected_remote_machine.avatar_surface)

        self.add_op_items()
        self.sync_favorite()

    def clear_user_view(self):
        for item in self.user_op_list:
            item.destroy()

    def add_op_items(self):
        self.clear_user_view()

        if not self.current_selected_remote_machine:
            return

        for op in self.current_selected_remote_machine.transfer_ops:
            self.user_op_list.add(TransferItem(op).item)

    def back_to_overview(self, button=None, data=None):
        self.view_stack.set_visible_child_name("overview")
        self.current_selected_remote_machine = None
        self.clear_user_view()
        self.sort_buttons()

    def user_favorite_clicked(self, widget, data=None):
        prefs.toggle_favorite(self.current_selected_remote_machine.hostname)
        self.sync_favorite()

    def sync_favorite(self):
        if self.current_selected_remote_machine.favorite:
            self.user_favorite_image.set_from_icon_name("starred-symbolic", Gtk.IconSize.BUTTON)
        else:
            self.user_favorite_image.set_from_icon_name("non-starred-symbolic", Gtk.IconSize.BUTTON)

    def get_sorted_button_list(self):
        def cmp_buttons(a, b):
            am = a.remote_machine
            bm = b.remote_machine

            if am.favorite and not bm.favorite:
                return -1
            elif bm.favorite and not am.favorite:
                return +1
            elif am.recent_time > bm.recent_time:
                return -1
            elif bm.recent_time > bm.recent_time:
                return +1

            return -1 if am.display_name < bm.display_name else +1

        children = self.user_list_box.get_children()
        return sorted(children, key=functools.cmp_to_key(cmp_buttons))

    def sort_buttons(self, button=None, data=None):
        sorted_list = self.get_sorted_button_list()
        widgets = self.user_list_box.get_children()

        for button in sorted_list:
            self.user_list_box.reorder_child(button, -1)

        # self.rebuild_status_icon_menu()

    def destroy(self):
        self.window.destroy()

class WarpApplication(Gtk.Application):
    def __init__(self):
        super(WarpApplication, self).__init__(application_id="com.linuxmint.warp",
                                              flags=Gio.ApplicationFlags.IS_SERVICE)
        self.window = None
        self.status_icon = None
        self.prefs_changed_source_id = 0

    def do_startup(self):
        Gtk.Application.do_startup(self)
        print("Initializing Warp on %s\n" % util.get_ip())

        prefs.prefs_settings.connect("changed", self.on_prefs_changed)

        self.activate()

    def do_activate(self):
        # if self.status_icon == None:
            # self.setup_status_icon()
        if self.window == None:
            self.setup_window()

        self.server = remote.LocalMachine()
        self.server.connect("remote-machine-added", self._remote_added)
        self.server.connect("remote-machine-removed", self._remote_removed)
        self.server.connect("remote-machine-ops-changed", self._remote_ops_changed)

    def shutdown(self, window=None):
        print("Beginning shutdown")
        self.server.connect("shutdown-complete", self.ok_for_app_quit)
        self.server.shutdown()

    def ok_for_app_quit(self, local_machine):
        self.window.destroy()
        print("Quitting..")
        self.quit()

    def setup_window(self):
        self.window = WarpWindow()
        self.window.connect("exit", self.shutdown)

        self.add_window(self.window.window)

        if prefs.get_start_with_window():
            self.window.window.present()

    def on_prefs_changed(self, settings, pspec=None, data=None):
        return
        if self.prefs_changed_source_id > 0:
            GLib.source_remove(self.prefs_changed_source_id)

        self.prefs_changed_source_id = GLib.timeout_add_seconds(1, self._on_delayed_prefs_changed)

    def _on_delayed_prefs_changed(self):
        self.prefs_changed_source_id = 0

        # self.app_nick = prefs.get_nick()
        # self.save_path = prefs.get_save_path()

        # self.server.set_prefs(self.app_nick, self.save_path)
        # for item in self.peers.values():
            # item.update_app_nick(self.app_nick)
        return False

    def _remote_added(self, local_machine, remote_machine):
        self.window.add_remote_button(remote_machine)

    def _remote_removed(self, local_machine, remote_machine):
        self.window.remove_remote_button(remote_machine)

    def _remote_ops_changed(self, local_machine, name):
        self.window.refresh_remote_machine_view()


    ####  BROWSER ##############################################


    # STATUS ICON ##########################################################################

    # def setup_status_icon(self):
    #     self.status_icon = XApp.StatusIcon()
    #     self.status_icon.set_icon_name("warp-symbolic")
    #     self.status_icon.connect("activate", self.on_tray_icon_activate)

    # def rebuild_status_icon_menu(self):
    #     menu = Gtk.Menu()

    #     self.add_proxy_menu_entries(menu)
    #     menu.add(Gtk.SeparatorMenuItem())

    #     item = Gtk.MenuItem(label=_("Open Warp folder"))
    #     item.connect("activate", self.on_open_location_clicked)
    #     menu.add(item)
    #     item = Gtk.MenuItem(label=_("Quit"))
    #     item.connect("activate", self.exit_app)
    #     menu.add(item)
    #     menu.show_all()

    #     self.status_icon.set_secondary_menu(menu)

    # def add_proxy_menu_entries(self, menu):
    #     proxy_list = self.get_sorted_proxy_list()
    #     i = 0

    #     for proxy in proxy_list:
    #         item = Gtk.MenuItem(label=proxy.proxy_nick)
    #         self.attach_recent_submenu(item, proxy)
    #         menu.add(item)
    #         i += 1

    #     # If there is more than one proxy, add a 'send to all'
    #     if i > 1:
    #         item = Gtk.MenuItem(label=_("Everyone"))
    #         self.attach_recent_submenu(item, None)
    #         menu.add(item)

    #     menu.show_all()

    # def attach_recent_submenu(self, menu, proxy):
    #     sub = Gtk.RecentChooserMenu(show_tips=True, sort_type=Gtk.RecentSortType.MRU, show_not_found=False)
    #     sub.connect("item-activated", self.status_icon_recent_item_selected, proxy)
    #     sub.add(Gtk.SeparatorMenuItem(visible=True))

    #     picker = Gtk.MenuItem(label=_("Browse..."), visible=True)
    #     picker.connect("activate", self.open_file_picker, proxy)
    #     sub.add(picker)

    #     menu.set_submenu(sub)

    # def status_icon_recent_item_selected(self, chooser, proxy=None):
    #     uri = chooser.get_current_uri()

    #     if proxy:
    #         proxy.file_sender.send_files([uri])
    #     else:
    #         for p in self.peers.values():
    #             p.file_sender.send_files([uri])

    # def open_file_picker(self, button, proxy=None):
    #     dialog = util.create_file_and_folder_picker()

    #     res = dialog.run()

    #     if res == Gtk.ResponseType.ACCEPT:
    #         uri_list = dialog.get_uris()

    #         if proxy:
    #             proxy.file_sender.send_files(uri_list)
    #         else:
    #             for p in self.peers.values():
    #                 p.file_sender.send_files(uri_list)

    #     dialog.destroy()

    # def on_tray_icon_activate(self, icon, button, time=0):
    #     if self.window.is_active():
    #         self.window.hide()
    #     else:
    #         if not self.window.get_visible():
    #             self.window.present()
    #             self.window.set_keep_above(self.above_toggle.props.active)
    #         else:
    #             # When there is more than one monitor, either gtk or
    #             # window managers (I've seen this in cinnamon, mate, xfce)
    #             # get confused if the mintupdate window is topmost on one
    #             # monitor, but the current focus is actually a window in
    #             # another monitor.  Focusing makes sure this window will
    #             # become 'active' for purposes of the hiding code above.

    #             self.window.get_window().raise_()
    #             self.window.get_window().focus(time)

if __name__ == "__main__":

    w = WarpApplication()

    try:
        w.run(sys.argv)
    except KeyboardInterrupt:
        w.shutdown()

    exit(0)
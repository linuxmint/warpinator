#!/usr/bin/python3
import os
import sys
import time
import setproctitle
import locale
import gettext
import functools

import socket

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('XApp', '1.0')
from gi.repository import Gtk, GLib, XApp, Gio, GObject, Gdk

import config
import prefs
import util
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
        if self.op.status == OpStatus.TRANSFERRING:
            self.op_progress_bar.set_fraction(self.op.progress)
            self.op_progress_bar.set_text(self.op.progress_text)
        elif self.op.status == OpStatus.PAUSED:
            self.op_progress_bar.set_text(_("Paused"))
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
        self.remote_machine_changed_id = self.remote_machine.connect("new-incoming-op",
                                                                     self._handle_new_incoming_op)

        self.new_ops = 0

        self.builder = Gtk.Builder.new_from_file(os.path.join(config.pkgdatadir, "warp-window.ui"))
        self.button = self.builder.get_object("overview_user_button")
        self.avatar_image = self.builder.get_object("overview_user_avatar_image")
        self.display_name_label = self.builder.get_object("overview_user_display_name")
        self.hostname_label = self.builder.get_object("overview_user_hostname")
        self.ip_label = self.builder.get_object("overview_user_ip")
        self.favorite_image = self.builder.get_object("overview_user_favorite")
        self.new_transfer_notify_label = self.builder.get_object("new_transfer_notify_label")
        self.new_transfer_notify_box = self.builder.get_object("new_transfer_notify_box")

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
        self.button._delegate = self

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

    def _handle_new_incoming_op(self, remote_machine, op):
        self.new_ops += 1
        self.new_transfer_notify_box.show()

        text = gettext.ngettext("%d new incoming transfer",
                                "%d new incoming transfers", self.new_ops) % (self.new_ops,)
        self.new_transfer_notify_label.set_text(text)
        self.button.get_style_context().add_class("suggested-action")

    def clear_new_op_notification(self):
        self.new_ops = 0
        self.new_transfer_notify_box.hide()
        self.button.get_style_context().remove_class("suggested-action")

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
        self.user_send_button = self.builder.get_object("user_send_button")

        # Send Files button
        self.recent_menu = Gtk.RecentChooserMenu(show_tips=True, sort_type=Gtk.RecentSortType.MRU, show_not_found=False)
        self.recent_menu.connect("item-activated", self.recent_item_selected)
        self.recent_menu.add(Gtk.SeparatorMenuItem(visible=True))
        picker = Gtk.MenuItem(label=_("Browse..."), visible=True)
        picker.connect("activate", self.open_file_picker)
        self.recent_menu.add(picker)
        self.user_send_button.set_popup(self.recent_menu)

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

    def recent_item_selected(self, recent_chooser, data=None):
        uri = self.recent_menu.get_current_uri()

        self.current_selected_remote_machine.send_files([uri])

    def open_file_picker(self, button, data=None):
        dialog = util.create_file_and_folder_picker()

        res = dialog.run()

        if res == Gtk.ResponseType.ACCEPT:
            uri_list = dialog.get_uris()
            self.current_selected_remote_machine.send_files(uri_list)

        dialog.destroy()

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

        # In our list box in the window's scrolled view we want most recent
        # at the top.
        ops = self.current_selected_remote_machine.transfer_ops.copy()
        ops.reverse()

        for op in ops:
            self.user_op_list.add(TransferItem(op).item)

    def back_to_overview(self, button=None, data=None):
        self.view_stack.set_visible_child_name("overview")

        # clear new op notification on overview button for the one
        # we just visited.
        buttons = self.user_list_box.get_children()

        for child in buttons:
            if child.connect_name == self.current_selected_remote_machine.connect_name:
                child._delegate.clear_new_op_notification()

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
#!/usr/bin/python3
import os
import sys
import setproctitle
import locale
import gettext
import functools
import logging
import time

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('XApp', '1.0')
from gi.repository import Gtk, GLib, XApp, Gio, GObject, Gdk

import config
import prefs
import util
import server
import auth
from ops import SendOp, ReceiveOp
from util import TransferDirection, OpStatus, RemoteStatus

# Don't let warp run as root
if os.getuid() == 0:
    print("Warpinator should not be run as root. Please run it in user mode.")
    sys.exit(1)

# i18n
locale.bindtextdomain(config.PACKAGE, config.localedir)
gettext.bindtextdomain(config.PACKAGE, config.localedir)
gettext.textdomain(config.PACKAGE)
_ = gettext.gettext


setproctitle.setproctitle("warpinator")

SERVER_RESTART_TIMEOUT = 12
SERVER_START_TIMEOUT = 8
DISCOVERY_TIMEOUT = 3

ICON_ONLINE = ""
ICON_OFFLINE = "network-offline-symbolic"
ICON_UNREACHABLE = "network-error-symbolic"

INHIBIT_STATES = (OpStatus.CALCULATING,
                  OpStatus.WAITING_PERMISSION,
                  OpStatus.TRANSFERRING,
                  OpStatus.PAUSED)

ALL_BUTTONS = ("transfer_accept", \
               "transfer_decline", \
               "transfer_cancel_request", \
               "transfer_restart", \
               "transfer_pause", \
               "transfer_resume", \
               "transfer_stop", \
               "transfer_remove", \
               "transfer_open_folder")

INIT_BUTTONS = ()
PERM_TO_SEND_BUTTONS = ("transfer_cancel_request",)
PERM_TO_ACCEPT_BUTTONS = ("transfer_accept", "transfer_decline")
TRANSFER_SENDING_BUTTONS = ("transfer_stop",)
# TRANSFER_SENDING_BUTTONS = ("transfer_pause", "transfer_stop") # not implemented yet
TRANSFER_RECEIVING_BUTTONS = ("transfer_stop",)
TRANSFER_PAUSED_SENDING_BUTTONS = ("transfer_resume", "transfer_stop")
TRANSFER_PAUSED_RECEIVING_BUTTONS = ()
TRANSFER_FAILED_SENDING_BUTTONS = ("transfer_restart", "transfer_remove")
TRANSFER_FAILED_UNRECOVERABLE_BUTTONS = ("transfer_remove",)
TRANSFER_FAILED_RECEIVING_BUTTONS = TRANSFER_FAILED_UNRECOVERABLE_BUTTONS
TRANSFER_STOPPED_BY_SENDER_BUTTONS = ("transfer_restart", "transfer_remove")
TRANSFER_STOPPED_BY_RECEIVER_BUTTONS = ("transfer_remove",)
TRANSFER_CANCELLED_BUTTONS = ("transfer_remove",)
TRANSFER_COMPLETED_SENDER_BUTTONS = TRANSFER_CANCELLED_BUTTONS
TRANSFER_FILE_NOT_FOUND_BUTTONS = TRANSFER_CANCELLED_BUTTONS
TRANSFER_COMPLETED_RECEIVER_BUTTONS = ("transfer_remove", "transfer_open_folder")

class OpItem(object):
    def __init__(self, op):
        super(OpItem, self).__init__()
        self.op = op

        self.builder = Gtk.Builder.new_from_file(os.path.join(config.pkgdatadir, "op-item.ui"))

        self.item = self.builder.get_object("op_item")
        self.direction_image = self.builder.get_object("transfer_direction_image")
        self.mime_image = self.builder.get_object("transfer_mime_image")
        self.transfer_description_label = self.builder.get_object("transfer_description_label")
        self.transfer_size_label = self.builder.get_object("transfer_size_label")
        self.op_status_stack = self.builder.get_object("op_status_stack")
        self.op_transfer_status_message = self.builder.get_object("op_transfer_status_message")
        self.op_transfer_problem_label = self.builder.get_object("op_transfer_problem_label")
        self.op_progress_bar = self.builder.get_object("op_transfer_progress_bar")
        self.accept_button =  self.builder.get_object("transfer_accept")
        self.decline_button =  self.builder.get_object("transfer_decline")
        self.cancel_button =  self.builder.get_object("transfer_cancel_request")
        self.restart_button =  self.builder.get_object("transfer_restart")
        self.pause_button =  self.builder.get_object("transfer_pause")
        self.stop_button =  self.builder.get_object("transfer_stop")
        self.remove_button =  self.builder.get_object("transfer_remove")
        self.folder_button =  self.builder.get_object("transfer_open_folder")

        self.accept_button.connect("clicked", self.accept_button_clicked)
        self.decline_button.connect("clicked", self.decline_button_clicked)
        self.cancel_button.connect("clicked", self.cancel_button_clicked)
        self.restart_button.connect("clicked", self.restart_button_clicked)
        self.pause_button.connect("clicked", self.pause_button_clicked)
        self.stop_button.connect("clicked", self.stop_button_clicked)
        self.remove_button.connect("clicked", self.remove_button_clicked)
        self.folder_button.connect("clicked", self.folder_button_clicked)

        self.op.connect("progress-changed", self.update_progress)

        self.refresh_status_widgets()
        self.refresh_buttons_and_icons()

    def update_progress(self, op):
        self.op_progress_bar.set_fraction(self.op.get_progress())
        self.op_progress_bar.set_text(self.op.get_progress_text())

    def set_visible_buttons(self, vis_buttons):
        for name in ALL_BUTTONS:
            self.builder.get_object(name).props.visible = False
        for name in vis_buttons:
            self.builder.get_object(name).props.visible = True

    def refresh_status_widgets(self):
        self.op_transfer_problem_label.hide()

        self.item.set_tooltip_text(self.op.error_msg)

        if self.op.status == OpStatus.TRANSFERRING:
            self.op_progress_bar.set_fraction(self.op.get_progress())
            self.op_progress_bar.set_text(self.op.get_progress_text())
        elif self.op.status == OpStatus.PAUSED:
            self.op_progress_bar.set_text(_("Paused"))
        if self.op.status == OpStatus.WAITING_PERMISSION:
            if self.op.direction == TransferDirection.TO_REMOTE_MACHINE:
                self.op_transfer_status_message.set_text(_("Waiting for approval"))
            else:
                self.op_transfer_status_message.set_text(_("Waiting for your approval"))
                if self.op.existing and prefs.prevent_overwriting():
                    self.op_transfer_problem_label.show()
                    self.op_transfer_problem_label.set_text(_("Files may be overwritten"))
                elif not self.op.have_space:
                    self.op_transfer_problem_label.show()
                    self.op_transfer_problem_label.set_text(_("Not enough disk space"))
        elif (self.op.status == OpStatus.CANCELLED_PERMISSION_BY_SENDER and isinstance(self.op, SendOp)) or \
            (self.op.status == OpStatus.CANCELLED_PERMISSION_BY_RECEIVER and isinstance(self.op, ReceiveOp)):
            self.op_transfer_status_message.set_text(_("Request cancelled"))
        elif (self.op.status == OpStatus.CANCELLED_PERMISSION_BY_SENDER and isinstance(self.op, ReceiveOp)):
            self.op_transfer_status_message.set_text(_("Request cancelled by %s") % self.op.sender_name)
        elif (self.op.status == OpStatus.CANCELLED_PERMISSION_BY_RECEIVER and isinstance(self.op, SendOp)):
            self.op_transfer_status_message.set_text(_("Request cancelled by %s") % self.op.receiver_name)
        elif (self.op.status == OpStatus.STOPPED_BY_SENDER and isinstance(self.op, SendOp)) or \
            (self.op.status == OpStatus.STOPPED_BY_RECEIVER and isinstance(self.op, ReceiveOp)):
            self.op_transfer_status_message.set_text(_("Transfer cancelled"))
        elif (self.op.status == OpStatus.STOPPED_BY_SENDER and isinstance(self.op, ReceiveOp)):
            self.op_transfer_status_message.set_text(_("Transfer cancelled by %s") % self.op.sender_name)
        elif (self.op.status == OpStatus.STOPPED_BY_RECEIVER and isinstance(self.op, SendOp)):
            self.op_transfer_status_message.set_text(_("Transfer cancelled by %s") % self.op.receiver_name)
        elif self.op.status in (OpStatus.FAILED, OpStatus.FAILED_UNRECOVERABLE):
            self.op_transfer_status_message.set_text(_("Transfer failed"))
        elif self.op.status == OpStatus.FILE_NOT_FOUND:
            self.op_transfer_problem_label.show()
            self.op_transfer_status_message.set_text(_("Transfer failed"))
            if self.op.first_missing_file != None:
                self.op_transfer_problem_label.set_text(_("File '%s' not found") % self.op.first_missing_file)
            else:
                self.op_transfer_problem_label.set_text(_("Some files not found"))
        elif self.op.status == OpStatus.FINISHED:
            self.op_transfer_status_message.set_text(_("Completed"))

    def refresh_buttons_and_icons(self):
        if self.op.direction == TransferDirection.TO_REMOTE_MACHINE:
            self.direction_image.set_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON)
        else:
            self.direction_image.set_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)

        if self.op.status == OpStatus.CALCULATING:
            self.mime_image.clear()
        else:
            self.mime_image.set_from_gicon(self.op.gicon, Gtk.IconSize.BUTTON)

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
            if self.op.direction == TransferDirection.TO_REMOTE_MACHINE:
                self.set_visible_buttons(TRANSFER_FAILED_SENDING_BUTTONS)
            else:
                self.set_visible_buttons(TRANSFER_FAILED_RECEIVING_BUTTONS)
            self.op_status_stack.set_visible_child_name("message")
        elif self.op.status == OpStatus.FAILED_UNRECOVERABLE:
            self.set_visible_buttons(TRANSFER_FAILED_UNRECOVERABLE_BUTTONS)
            self.op_status_stack.set_visible_child_name("message")
        elif self.op.status == OpStatus.FILE_NOT_FOUND:
            self.op_status_stack.set_visible_child_name("message")
            self.set_visible_buttons(TRANSFER_FILE_NOT_FOUND_BUTTONS)
        elif self.op.status == OpStatus.FINISHED:
            self.op_status_stack.set_visible_child_name("message")
            if isinstance(self.op, SendOp):
                self.set_visible_buttons(TRANSFER_COMPLETED_SENDER_BUTTONS)
            else:
                self.set_visible_buttons(TRANSFER_COMPLETED_RECEIVER_BUTTONS)
        elif self.op.status in (OpStatus.CANCELLED_PERMISSION_BY_SENDER,
                                OpStatus.CANCELLED_PERMISSION_BY_RECEIVER):
            self.set_visible_buttons(TRANSFER_CANCELLED_BUTTONS)
        elif self.op.status == OpStatus.STOPPED_BY_SENDER and isinstance(self.op, SendOp):
            self.op_status_stack.set_visible_child_name("message")
            self.set_visible_buttons(TRANSFER_STOPPED_BY_SENDER_BUTTONS)
        elif self.op.status in (OpStatus.STOPPED_BY_SENDER, OpStatus.STOPPED_BY_RECEIVER):
            self.op_status_stack.set_visible_child_name("message")
            self.set_visible_buttons(TRANSFER_STOPPED_BY_RECEIVER_BUTTONS)

    def accept_button_clicked(self, button):
        self.op.accept_transfer()

    def decline_button_clicked(self, button):
        self.op.decline_transfer_request()

    def cancel_button_clicked(self, button):
        self.op.cancel_transfer_request()

    def restart_button_clicked(self, button):
        self.op.retry_transfer()

    def pause_button_clicked(self, button):
        pass

    def stop_button_clicked(self, button):
        self.op.stop_transfer()

    def remove_button_clicked(self, button):
        self.op.remove_transfer()

    def folder_button_clicked(self, button):
        if len(self.op.top_dir_basenames) == 1:
            util.open_save_folder(self.op.top_dir_basenames[0])
        else:
            util.open_save_folder()

    def destroy(self):
        self.builder = None
        self.item.get_parent().destroy()
        self.item = None
        try:
            self.op.disconnect_by_func(self.update_progress)
        except:
            pass
        self.op = None

class OverviewButton(GObject.Object):
    __gsignals__ = {
        'update-sort': (GObject.SignalFlags.RUN_LAST, None, ()),
        'clicked': (GObject.SignalFlags.RUN_LAST, None, ()),
        'files-dropped': (GObject.SignalFlags.RUN_LAST, None, ()),
        'need-attention': (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self, remote_machine, simulated=False):
        super(OverviewButton, self).__init__()

        self.remote_machine = remote_machine
        self.remote_machine_changed_id = self.remote_machine.connect("machine-info-changed",
                                                                     self._update_machine_info)
        self.new_incoming_op_id = self.remote_machine.connect("new-incoming-op",
                                                               self._handle_new_incoming_op)
        self.new_incoming_op_id = self.remote_machine.connect("new-outgoing-op",
                                                               self._handle_new_outgoing_op)
        self.remote_machine.connect("remote-status-changed", self.remote_machine_status_changed)
        self.new_ops = 0

        self.builder = Gtk.Builder.new_from_file(os.path.join(config.pkgdatadir, "overview-button.ui"))

        self.button = self.builder.get_object("overview_button")
        self.avatar_image = self.builder.get_object("overview_user_avatar_image")
        self.avatar_box = self.builder.get_object("overview_user_avatar_box")
        self.ip_label = self.builder.get_object("overview_user_ip")
        self.favorite_image = self.builder.get_object("overview_user_favorite")
        self.overview_user_button_stack = self.builder.get_object("overview_user_button_stack")
        self.overview_user_info_label = self.builder.get_object("overview_user_info_label")
        self.overview_user_status_icon = self.builder.get_object("overview_user_status_icon")
        self.overview_user_display_name = self.builder.get_object("overview_user_display_name")
        self.overview_user_hostname = self.builder.get_object("overview_user_hostname")
        self.overview_user_connecting_spinner = self.builder.get_object("overview_user_connecting_spinner")

        self.button.connect("clicked", lambda button: self.emit("clicked"))

        # Convenience for window to sort and remove buttons
        self.button.remote_machine = remote_machine
        self.button.ident = remote_machine.ident
        self.button._delegate = self

        self.button.show_all()
        self.refresh_favorite_icon()
        self.remote_machine_status_changed(self.remote_machine)

    def remote_machine_status_changed(self, remote_machine):
        have_info = remote_machine.display_name != ""
        name = remote_machine.display_name if have_info else remote_machine.display_hostname
        self.clear_new_op_highlighting()

        if remote_machine.status == RemoteStatus.INIT_CONNECTING:
            self.overview_user_connecting_spinner.show()
            self.overview_user_status_icon.hide()
            self.ip_label.set_text(self.remote_machine.ip_address)
            if have_info:
                self.button.set_tooltip_text(_("Connecting"))
            else:
                self.button.set_tooltip_text(_("Connecting to %s") % name)
        elif remote_machine.status == RemoteStatus.ONLINE:
            self.overview_user_connecting_spinner.hide()
            self.overview_user_status_icon.show()
            self.overview_user_status_icon.set_from_icon_name(ICON_ONLINE, Gtk.IconSize.LARGE_TOOLBAR)
            self.button.set_tooltip_text("")
        elif remote_machine.status == RemoteStatus.OFFLINE:
            self.overview_user_connecting_spinner.hide()
            self.overview_user_status_icon.show()
            self.overview_user_status_icon.set_from_icon_name(ICON_OFFLINE, Gtk.IconSize.LARGE_TOOLBAR)
            self.button.set_tooltip_text(_("%s is not online") % name)
        elif remote_machine.status == RemoteStatus.UNREACHABLE:
            self.overview_user_connecting_spinner.hide()
            self.overview_user_status_icon.show()
            self.overview_user_status_icon.set_from_icon_name(ICON_UNREACHABLE, Gtk.IconSize.LARGE_TOOLBAR)
            self.button.set_tooltip_text(_("Cannot connect to %s") % name)
        elif remote_machine.status == RemoteStatus.AWAITING_DUPLEX:
            self.overview_user_connecting_spinner.hide()
            self.overview_user_status_icon.show()
            self.overview_user_status_icon.set_from_icon_name(ICON_UNREACHABLE, Gtk.IconSize.LARGE_TOOLBAR)
            self.button.set_tooltip_text(_("Waiting for %s to complete the connection.") % name)

        self.overview_user_display_name.set_visible(have_info)
        self.overview_user_hostname.set_visible(True)

    def _update_machine_info(self, remote_machine):
        self.overview_user_display_name.set_text(self.remote_machine.display_name)

        if self.remote_machine.user_name != "":
            self.overview_user_hostname.set_text("%s@%s" % (self.remote_machine.user_name, self.remote_machine.display_hostname))
        else:
            self.overview_user_hostname.set_text(self.remote_machine.display_hostname)

        self.ip_label.set_text(self.remote_machine.ip_address)

        if self.remote_machine.avatar_surface:
            self.avatar_image.set_from_surface(self.remote_machine.avatar_surface)
        else:
            self.avatar_image.set_from_icon_name("avatar-default-symbolic", Gtk.IconSize.DND)

        self.remote_machine_status_changed(remote_machine)
        self.refresh_favorite_icon()

        self.emit("update-sort")
        self.button.show_all()

    def _handle_new_incoming_op(self, remote_machine, op):
        self.new_ops += 1

        text = gettext.ngettext("%d new incoming transfer",
                                "%d new incoming transfers", self.new_ops) % (self.new_ops,)

        self.button.set_tooltip_text(text)
        self.button.get_style_context().add_class("suggested-action")

        self.emit("need-attention")

    def _handle_new_outgoing_op(self, remote_machine, op):
        self.new_ops += 1

        if op.status in (OpStatus.FAILED, OpStatus.FILE_NOT_FOUND):
            self.button.get_style_context().add_class("destructive-action")
            self.emit("need-attention")

    def clear_new_op_highlighting(self):
        self.new_ops = 0

        if self.remote_machine.status == RemoteStatus.ONLINE:
            self.button.set_tooltip_text("")

        self.button.get_style_context().remove_class("suggested-action")
        self.button.get_style_context().remove_class("destructive-action")

    def refresh_favorite_icon(self):
        self.favorite_image.show()

        if self.remote_machine.favorite:
            self.favorite_image.set_from_icon_name("starred-symbolic", Gtk.IconSize.BUTTON)
        elif self.remote_machine.recent_time != 0:
            self.favorite_image.set_from_icon_name("document-open-recent-symbolic", Gtk.IconSize.BUTTON)
        else:
            self.favorite_image.clear()

    def do_dispose(self):
        if self.new_incoming_op_id > 0:
            self.remote_machine.disconnect(self.new_incoming_op_id)
            self.new_incoming_op_id = 0

        if self.remote_machine_changed_id > 0:
            self.remote_machine.disconnect(self.remote_machine_changed_id)
            self.remote_machine_changed_id = 0

        # remove circular refs
        self.button.remote_machine = None
        self.button.ident = None
        self.button._delegate = None

        logging.debug("UI: (%s) Disconnecting overview remote button from RemoteMachine" % self.remote_machine.display_hostname)
        GObject.Object.do_dispose(self)

class WarpWindow(GObject.Object):
    __gsignals__ = {
        'exit': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        super(WarpWindow, self).__init__()

        self.current_selected_remote_machine = None
        self.drop_pending = False
        self.window_close_handler_id = 0
        self.selected_op_items = {}

        # overview
        self.builder = Gtk.Builder.new_from_file(os.path.join(config.pkgdatadir, "main-window.ui"))

        self.window =self.builder.get_object("main_window")
        self.view_stack = self.builder.get_object("view_stack")
        self.menu_button = self.builder.get_object("menu_button")
        self.overview_scrolled_window = self.builder.get_object("overview_scrolled_window")
        self.user_list_box = self.builder.get_object("user_list_box")
        self.user_list_no_search_results_label = self.builder.get_object("user_list_no_search_results_label")
        self.search_entry = self.builder.get_object("search_entry")
        self.app_display_name_label = self.builder.get_object("app_display_name")
        self.app_ip_label = self.builder.get_object("app_ip")
        self.app_local_name_label = self.builder.get_object("app_local_name")
        self.something_wrong_label = self.builder.get_object("something_went_wrong_label")
        self.bad_save_folder_label = self.builder.get_object("bad_save_folder_label")

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
        self.user_online_box = self.builder.get_object("user_online_box")
        self.user_online_image = self.builder.get_object("user_online_image")
        self.user_online_label = self.builder.get_object("user_online_label")
        self.user_online_spinner = self.builder.get_object("user_online_spinner")
        self.user_clear_ops_button = self.builder.get_object("user_clear_ops_button")

        # Send Files button
        self.recent_menu = util.get_recent_chooser_menu()
        self.recent_menu.connect("item-activated", self.recent_item_selected)
        self.recent_menu.add(Gtk.SeparatorMenuItem(visible=True))
        picker = Gtk.MenuItem(label=_("Browse..."), visible=True)
        picker.connect("activate", self.open_file_picker)
        self.recent_menu.add(picker)
        self.user_send_button.set_popup(self.recent_menu)

        self.server_start_timeout_id = 0
        self.discovery_time_out_id = 0
        self.server_restarting = False

        self.window.connect("delete-event",
                            self.window_delete_event)

        # Hamburger menu
        menu = Gtk.Menu()
        item = Gtk.MenuItem(label=_("Open save folder"))
        item.connect("activate", self.on_open_location_clicked)
        menu.add(item)

        item = Gtk.MenuItem(label=_("Preferences"))
        item.connect("activate", self.open_preferences)
        menu.add(item)

        item = Gtk.MenuItem(label=_("About"))
        item.connect("activate", self.show_about)
        menu.add(item)

        item = Gtk.MenuItem(label=_("Quit"))
        item.connect("activate", self.menu_quit)
        menu.add(item)
        menu.show_all()

        self.menu_button.set_popup(menu)
        # end Hamburger 

        # DND
        self.drop_pending = False
        self.user_op_list.connect("drag-drop", self.on_drag_drop)
        self.user_op_list.connect("drag-data-received", self.on_drag_data_received)
        self.user_op_list.connect("drag-motion", self.on_drag_motion)
        # /DND

        self.search_entry.connect("search-changed", self.search_entry_changed)
        self.window.connect("key-press-event", self.window_key_press)

        self.window.connect("focus-in-event",
                            lambda window, event: window.set_urgency_hint(False))

        self.user_clear_ops_button.connect("clicked", self.clear_ops_clicked)

        self.update_local_user_info()

    def show_about(self, widget):
        util.AboutDialog(self.window)

    def window_delete_event(self, widget, event, data=None):
        if prefs.use_tray_icon():
            self.window.hide()
        else:
            self.emit("exit")

        return Gdk.EVENT_STOP

    def window_key_press(self, widget, event, data=None):
        if not self.search_entry.has_focus() and self.view_stack.get_visible_child_name() == "overview":
            self.search_entry.grab_focus()
        elif event.keyval == Gdk.KEY_BackSpace and self.view_stack.get_visible_child_name() == "user":
            self.back_to_overview()
            return Gdk.EVENT_STOP

        return Gdk.EVENT_PROPAGATE

    def toggle_visibility(self, time=0):
        if self.window.is_active():
            self.window.hide()
        else:
            self.show(time)

    def show(self, time=0):
            if not self.window.get_visible():
                self.window.present()
            else:
                self.window.get_window().raise_()
                self.window.get_window().focus(time)

    def search_entry_changed(self, entry, data=None):
        query = entry.get_text()
        normalized_query = GLib.utf8_normalize(query, len(query), GLib.NormalizeMode.DEFAULT).lower()

        found_one = False

        for button in self.user_list_box.get_children():
            joined = " ".join([button.remote_machine.display_name,
                               ("%s@%s" % (button.remote_machine.user_name, button.remote_machine.hostname)),
                               button.remote_machine.ip_address])
            normalized_contents = GLib.utf8_normalize(joined, len(joined), GLib.NormalizeMode.DEFAULT).lower()

            if normalized_query in normalized_contents:
                found_one = True
                button.show()
            else:
                button.hide()

        self.user_list_no_search_results_label.set_visible(not found_one)

    def start_startup_timer(self, restarting=False):
        if self.server_start_timeout_id > 0:
            GLib.source_remove(self.server_start_timeout_id)
            self.server_start_timeout_id = 0

        self.server_restarting = restarting

        timeout = SERVER_RESTART_TIMEOUT if restarting else SERVER_START_TIMEOUT

        self.server_start_timeout_id = GLib.timeout_add_seconds(timeout, self.server_not_started_timeout)
        self.view_stack.set_visible_child_name("startup")

    def server_not_started_timeout(self):
        self.view_stack.set_visible_child_name("server-problem")

        if util.get_preferred_ip() == "0.0.0.0":
            self.something_wrong_label.set_text(_("You don't appear to be connected to a network."))
        else:
            self.something_wrong_label.set_text(_("Startup was unsuccessful, please check your logs."))

        self.server_start_timeout_id = 0
        return False

    def clear_ops_clicked(self, button):
        for op in self.current_selected_remote_machine.transfer_ops:
            if op.status in (OpStatus.CANCELLED_PERMISSION_BY_SENDER,
                             OpStatus.CANCELLED_PERMISSION_BY_RECEIVER,
                             OpStatus.STOPPED_BY_SENDER,
                             OpStatus.STOPPED_BY_RECEIVER,
                             OpStatus.FAILED,
                             OpStatus.FAILED_UNRECOVERABLE,
                             OpStatus.FILE_NOT_FOUND,
                             OpStatus.FINISHED):
                op.remove_transfer()

    def recent_item_selected(self, recent_chooser, data=None):
        uri = self.recent_menu.get_current_uri()

        self.current_selected_remote_machine.send_files([uri])

    def open_file_picker(self, button, data=None):
        dialog = util.create_file_and_folder_picker(self.window)

        res = dialog.run()

        if res == Gtk.ResponseType.ACCEPT:
            uri_list = dialog.get_uris()
            self.current_selected_remote_machine.send_files(uri_list)

        dialog.destroy()

    def on_drag_motion(self, widget, context, x, y, time):
        if self.current_selected_remote_machine.status != RemoteStatus.ONLINE:
            Gdk.drag_status(context, 0, time)
            return

    def on_drag_drop(self, widget, context, x, y, _time, data=None):
        atom =  widget.drag_dest_find_target(context, None)
        self.drop_pending = True
        widget.drag_get_data(context, atom, _time)

    def on_drag_data_received(self, widget, context, x, y, data, info, _time, user_data=None):
        if self.current_selected_remote_machine.status != RemoteStatus.ONLINE:
            Gdk.drag_status(context, 0, _time)
            return

        if not self.drop_pending:
            Gdk.drag_status(context, Gdk.DragAction.COPY, _time)
            return

        if data:
            if context.get_selected_action() == Gdk.DragAction.COPY:
                uris = data.get_uris()
                self.current_selected_remote_machine.send_files(uris)

        Gtk.drag_finish(context, True, False, _time)
        self.drop_pending = False

    def update_local_user_info(self):
        self.app_local_name_label.set_text(util.get_local_name())
        self.app_ip_label.set_text(util.get_preferred_ip())

    def menu_quit(self, widget, data=None):
        self.display_shutdown()
        self.emit("exit")

    def on_open_location_clicked(self, widget, data=None):
        util.open_save_folder()

    def open_preferences(self, menuitem, data=None):
        prefs.Preferences(self.window)

    def report_bad_save_folder(self):
        self.bad_save_folder_label.set_text(prefs.get_save_path())
        self.view_stack.set_visible_child_name("bad-save-folder")

    def add_remote_button(self, remote_machine, simulated=False):
        if self.discovery_time_out_id > 0:
            GLib.source_remove(self.discovery_time_out_id)
            self.discovery_time_out_id = 0

        if self.server_start_timeout_id > 0:
            GLib.source_remove(self.server_start_timeout_id)
            self.server_start_timeout_id = 0

        remote_machine.connect("focus-remote", self.focus_remote_machine)

        button = OverviewButton(remote_machine, simulated)
        button.connect("update-sort", self.sort_buttons)
        button.connect("files-dropped", self.remote_machine_files_dropped)
        button.connect("clicked", self.remote_machine_button_clicked)
        button.connect("need-attention", self._get_user_attention)

        self.user_list_box.add(button.button)

        self.view_stack.set_visible_child_name("overview")
        self.sort_buttons()

    def remove_remote_button(self, remote_machine):
        buttons = self.user_list_box.get_children()

        for child in buttons:
            if child.ident == remote_machine.ident:
                self.user_list_box.remove(child)

        self.back_to_overview()

        if len(self.user_list_box.get_children()) == 0:
            self.start_discovery_timer()

        self.sort_buttons()

    def clear_remotes(self):
        buttons = self.user_list_box.get_children()
        for child in buttons:
            self.user_list_box.remove(child)

    def focus_remote_machine(self, remote_machine, data=None):
        if self.current_selected_remote_machine != None:
            self.cleanup_user_view()

        self.switch_to_user_view(remote_machine)

        if not self.window.is_active():
            self.toggle_visibility()

    def display_shutdown(self):
        self.view_stack.set_visible_child_name("shutdown")

    def notify_server_started(self):
        self.server_restarting = False

        if self.server_start_timeout_id > 0:
            GLib.source_remove(self.server_start_timeout_id)
            self.server_start_timeout_id = 0

        self.start_discovery_timer()

    def start_discovery_timer(self):
        logging.debug("UI: start discovery timer (no remotes)")

        if self.discovery_time_out_id > 0:
            GLib.source_remove(self.discovery_time_out_id)
            self.discovery_time_out_id = 0

        # If the server is restarting, this will get called when the last remote is removed
        # during shutdown, but we want the 'startup' view to remain showing (called in
        # display_shutdown()).
        if self.server_restarting:
            return

        self.discovery_time_out_id = GLib.timeout_add_seconds(DISCOVERY_TIMEOUT, self.discovery_timed_out)
        self.view_stack.set_visible_child_name("discovery")

    def discovery_timed_out(self):
        logging.debug("UI: Discovery timed out (no remotes)")

        self.view_stack.set_visible_child_name("no-remotes")
        self.discovery_time_out_id = 0
        return False

    def remote_machine_button_clicked(self, button):
        self.switch_to_user_view(button.remote_machine)

    def remote_machine_files_dropped(self, button):
        self.switch_to_user_view(button.remote_machine)

    def _get_user_attention(self, button):
        self.sort_buttons()
        self.overview_scrolled_window.get_vadjustment().set_value(0)
        if not self.window.is_active():
            self.window.set_urgency_hint(True)

    def switch_to_user_view(self, remote_machine):
        self.view_stack.set_visible_child_name("user")
        self.current_selected_remote_machine = remote_machine

        self.refresh_remote_machine_view()

    def refresh_remote_machine_view(self):
        if self.view_stack.get_visible_child_name() != "user":
            return

        remote = self.current_selected_remote_machine

        try:
            remote.disconnect_by_func(self.current_selected_remote_status_changed)
        except TypeError:
            pass

        remote.connect("remote-status-changed",
                       self.current_selected_remote_status_changed)

        self.current_selected_remote_status_changed(remote)

        self.user_display_name_label.set_text(remote.display_name)
        self.user_display_name_label.set_visible(remote.display_name != "")

        if remote.user_name != "":
            self.user_hostname_label.set_text("%s@%s" % (remote.user_name,
                                                         remote.display_hostname))
        else:
            self.user_hostname_label.set_text(remote.display_hostname)

        self.user_ip_label.set_text(remote.ip_address)

        if remote.avatar_surface != None:
            self.user_avatar_image.set_from_surface(remote.avatar_surface)
        else:
            self.user_avatar_image.set_from_icon_name("avatar-default-symbolic", Gtk.IconSize.DND)

        self.add_op_items()
        self.sync_favorite()

    def current_selected_remote_status_changed(self, remote_machine):
        if remote_machine.status == RemoteStatus.ONLINE:
            entry = Gtk.TargetEntry.new("text/uri-list",  0, 0)
            self.user_op_list.drag_dest_set(Gtk.DestDefaults.ALL,
                                            (entry,),
                                            Gdk.DragAction.COPY)
            self.user_send_button.set_sensitive(True)
            self.user_online_label.set_text(_("Online"))
            self.user_online_image.set_from_icon_name(ICON_ONLINE, Gtk.IconSize.LARGE_TOOLBAR)
            self.user_online_spinner.hide()
            self.user_online_image.show()
        elif remote_machine.status == RemoteStatus.OFFLINE:
            self.user_op_list.drag_dest_unset()
            self.user_send_button.set_sensitive(False)
            self.user_online_label.set_text(_("Offline"))
            self.user_online_image.set_from_icon_name(ICON_OFFLINE, Gtk.IconSize.LARGE_TOOLBAR)
            self.user_online_spinner.hide()
            self.user_online_image.show()
        elif remote_machine.status == RemoteStatus.UNREACHABLE:
            self.user_op_list.drag_dest_unset()
            self.user_send_button.set_sensitive(False)
            self.user_online_label.set_text(_("Unable to connect"))
            self.user_online_image.set_from_icon_name(ICON_UNREACHABLE, Gtk.IconSize.LARGE_TOOLBAR)
            self.user_online_spinner.hide()
            self.user_online_image.show()
        elif remote_machine.status == RemoteStatus.AWAITING_DUPLEX:
            self.user_op_list.drag_dest_unset()
            self.user_send_button.set_sensitive(False)
            self.user_online_label.set_text(_("Waiting for two-way connection"))
            self.user_online_image.set_from_icon_name(ICON_UNREACHABLE, Gtk.IconSize.LARGE_TOOLBAR)
            self.user_online_spinner.hide()
            self.user_online_image.show()
        else:
            self.user_op_list.drag_dest_unset()
            self.user_send_button.set_sensitive(False)
            self.user_online_label.set_text(_("Connecting"))
            self.user_online_image.hide()
            self.user_online_spinner.show()

        self.sync_buttons_enabled()

    def clear_user_view(self):
        for item in self.selected_op_items.values():
            item.destroy()

        self.selected_op_items = {}

    def add_op_items(self):
        self.clear_user_view()

        if not self.current_selected_remote_machine:
            return

        # In our list box in the window's scrolled view we want most recent
        # at the top.
        ops = self.current_selected_remote_machine.transfer_ops.copy()
        ops.reverse()

        for op in ops:
            op_item = OpItem(op)
            self.selected_op_items[op.start_time] = op_item
            self.user_op_list.add(op_item.item)

        self.user_clear_ops_button.set_sensitive(len(ops) > 0)
        self.sync_buttons_enabled()

    def sync_buttons_enabled(self):
        for op_item in self.selected_op_items.values():
            op_item.restart_button.set_sensitive(self.current_selected_remote_machine.status == RemoteStatus.ONLINE)

    def back_to_overview(self, button=None, data=None):
        if not self.server_restarting:
            self.view_stack.set_visible_child_name("overview")

        self.cleanup_user_view()

    def cleanup_user_view(self):
        # clear new op notification on overview button for the one
        # we just visited.
        buttons = self.user_list_box.get_children()

        if self.current_selected_remote_machine != None:
            self.current_selected_remote_machine.stamp_recent_time()

            for child in buttons:
                if child.ident == self.current_selected_remote_machine.ident:
                    child._delegate.clear_new_op_highlighting()

        self.current_selected_remote_machine = None
        self.clear_user_view()
        self.sort_buttons()

    def user_favorite_clicked(self, widget, data=None):
        prefs.toggle_favorite(self.current_selected_remote_machine.ident)
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
            return util.sort_remote_machines(am, bm)

        def cmp_favorite(a, b):
            ad = a._delegate
            bd = b._delegate
            return -1 if ad.new_ops > bd.new_ops else +1

        children = self.user_list_box.get_children()
        sorted_list = sorted(children, key=functools.cmp_to_key(cmp_buttons))
        ret = sorted(sorted_list, key=functools.cmp_to_key(cmp_favorite))
        return ret

    def sort_buttons(self, button=None, data=None):
        sorted_list = self.get_sorted_button_list()

        for button in sorted_list:
            self.user_list_box.reorder_child(button, -1)

    def update_behavior_from_preferences(self):
        # more..

        self.update_local_user_info()

    def destroy(self):
        self.window.destroy()

class WarpApplication(Gtk.Application):
    def __init__(self, testing=False):
        super(WarpApplication, self).__init__(application_id="org.x.Warpinator", register_session=True)
        self.window = None
        self.status_icon = None
        self.prefs_changed_source_id = 0
        self.server_starting = False

        self.test_mode = testing

        self.bad_folder = False

        self.inhibit_count = 0
        self.inhibit_cookie = 0

        self.netmon = None
        self.server = None

        # This is only so we can check if the port changed when setting preferences
        self.current_port = prefs.get_port()
        self.current_ip = util.get_preferred_ip()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        logging.info("Initializing Warpinator")

        prefs.prefs_settings.connect("changed", self.on_prefs_changed)
        auth.get_singleton().connect("group-code-changed", self.on_group_code_changed)

        vt = GLib.VariantType.new("s")

        action = Gio.SimpleAction.new("notification-response", vt)
        self.add_action(action)

    def do_activate(self):
        Gtk.Application.do_activate(self)

        if self.window != None:
            self.window.show()
            return

        logging.debug("UI: Creating window and status icon")

        if self.status_icon == None:
            self.update_status_icon_from_preferences()

        if self.window == None:
            self.setup_window()

        try:
            self.save_folder_monitor.cancel()
            self.save_folder_monitor = None
        except:
            pass

        if not util.verify_save_folder():
            file = Gio.File.new_for_path(prefs.get_save_path())

            def monitor_change_event(monitor, file, other_file, event_type, data=None):
                logging.debug("UI: State of save folder changed: %s (%s)", str(event_type), file.get_path())
                if not util.verify_save_folder():
                    return

                self.save_folder_monitor.disconnect_by_func(monitor_change_event)
                self.try_activation()

            try:
                self.save_folder_monitor = file.monitor_directory(Gio.FileMonitorFlags.WATCH_MOUNTS, None)
                self.save_folder_monitor.connect("changed", monitor_change_event)
            except GLib.Error as e:
                logging.warn("Could not create a monitor for the save folder: %s"% e.message)

            self.window.report_bad_save_folder()
            self.window.window.present()
            return

        self.try_activation()

    def try_activation(self):
        if self.server_starting:
            return

        self.window.start_startup_timer(restarting=False)

        if self.netmon == None:
            self.netmon = util.NetworkMonitor()
            self.netmon.connect("state-changed", self.network_state_changed)

        self.window.update_local_user_info()
        self.current_port = prefs.get_port()
        self.current_ip = util.get_preferred_ip()

        logging.info("Trying to start server on %s" % self.current_ip)
        self.start_server()

    def add_simulated_widgets(self):
        if self.test_mode:
            import testing
            testing.add_simulated_widgets(self)

    def start_server(self):
        self.window.clear_remotes()

        def try_to_start(srv=None):
            try:
                self.server.disconnect_by_func(try_to_start)
            except:
                pass

            self.server = None

            if util.get_preferred_ip() == "0.0.0.0":
                logging.info("No network access")
                return

            self.server_starting = True
            self.server = server.Server()
            self.server.connect("server-started", self._server_started)
            self.server.connect("remote-machine-added", self._remote_added)
            self.server.connect("remote-machine-removed", self._remote_removed)
            self.server.connect("remote-machine-ops-changed", self._remote_ops_changed)

        if self.server:
            self.window.start_startup_timer(True)
            self.server.connect("shutdown-complete", try_to_start)
            self.server.shutdown()
        else:
            try_to_start();

    def do_shutdown(self):
        logging.debug("Beginning shutdown")

        self.update_status_icon_online_state(online=False)
        self.window.display_shutdown()

        if self.netmon:
            self.netmon.stop()

        if self.server:
            self.setup_kill_as_a_last_resort()
            self.server.shutdown()
            # do_shutdown is called after the main loop is ended, we need to continue
            # the loop while waiting for the server to finish shutting down.  This is the
            # only way we can come close to a clean exit when being killed or shutdown via
            # the session manager.
            while self.server.is_alive():
                GLib.MainContext.default().iteration(may_block=False)

            self.server.join()

        self.window.destroy()

        logging.debug("Shutdown complete")
        Gio.Application.do_shutdown(self)

    def exit_warp(self):
        GLib.idle_add(self.quit)

    @util._async
    def setup_kill_as_a_last_resort(self):
        # There are plenty of opportunities for our threads to hang due to network
        # hangs and grpc errors.  Give 10 seconds and then just end it regardless.
        logging.debug("Setting up kill")
        time.sleep(10)
        os.system("kill -9 %s &" % os.getpid())

    def setup_window(self):
        self.window = WarpWindow()
        self.window.connect("exit", lambda w: self.exit_warp())

        self.add_window(self.window.window)

        if prefs.get_start_with_window() or not prefs.use_tray_icon():
            self.window.window.present()

    def on_prefs_changed(self, settings, pspec=None, data=None):
        self.window.update_behavior_from_preferences()
        self.update_status_icon_from_preferences()

        if prefs.get_port() != self.current_port or \
           util.get_preferred_ip() != self.current_ip:
            self.try_activation()

    def firewall_script_finished(self):
        if self.server == None:
            self.try_activation()
            return

        self.try_activation()

    def on_group_code_changed(self, auth_manager):
        self.try_activation()

    def _remote_added(self, local_machine, remote_machine):
        self.window.add_remote_button(remote_machine)
        remote_machine.connect("machine-info-changed", self.rebuild_status_icon_menu)
        remote_machine.connect("remote-status-changed", self.rebuild_status_icon_menu)
        self.rebuild_status_icon_menu()

    def _remote_removed(self, local_machine, remote_machine):
        if remote_machine.status == RemoteStatus.INIT_CONNECTING:
            self.window.remove_remote_button(remote_machine)

        self.rebuild_status_icon_menu()

    def _remote_ops_changed(self, local_machine, name):
        self.window.refresh_remote_machine_view()
        self.update_inhibitor_state(local_machine)

    def _server_started(self, local_machine):
        self.update_status_icon_online_state(online=True)
        self.server_starting = False

        self.window.notify_server_started()
        self.add_simulated_widgets()

    def network_state_changed(self, netmon, online):
        self.update_status_icon_online_state(online)

        if online:
            self.try_activation()
        else:
            # Lost the network - show that we're doing something, and shut the
            # server down if it's running.
            self.window.start_startup_timer()

            if self.server != None:
                def no_network_shutdown_complete(netmon):
                    self.server.disconnect_by_func(no_network_shutdown_complete)
                    self.server = None

                    # Now reconnect to the network monitor.
                    self.netmon.connect("state-changed", self.network_state_changed)
                    # Now run state-changed again in case we came back online while
                    # the server was shutting down.
                    self.network_state_changed(self.netmon, self.netmon.online)

                self.server.connect("shutdown-complete", no_network_shutdown_complete)

                # Temporarily disconnect so we don't get ahead of ourselves.
                self.netmon.disconnect_by_func(self.network_state_changed)
                self.server.shutdown()

    def update_inhibitor_state(self, local_machine):
        any_active_ops = False

        remotes = self.server.list_remote_machines()

        for remote_machine in remotes:
            for op in remote_machine.transfer_ops:
                if op.status in INHIBIT_STATES:
                    any_active_ops = True
                    break

            if any_active_ops:
                break

        if any_active_ops:
            if self.inhibit_cookie == 0:
                logging.debug("UI: Inhibiting suspend/logout while transfers are active")
                self.inhibit_cookie = self.inhibit(self.window.window,
                                                   Gtk.ApplicationInhibitFlags.LOGOUT | Gtk.ApplicationInhibitFlags.SUSPEND,
                                                   "Warpinator is sending or receiving files, or there is a pending transfer")
        else:
            if self.inhibit_cookie > 0:
                logging.debug("UI: No more active transfers, uninhibiting suspend/logout")
                self.uninhibit(self.inhibit_cookie)
                self.inhibit_cookie = 0

    ####  STATUS ICON ##########################################################################

    def update_status_icon_from_preferences(self):
        if prefs.use_tray_icon():
            if self.status_icon == None:
                self.status_icon = XApp.StatusIcon()
                self.status_icon.connect("activate", self.on_tray_icon_activate)
                self.update_status_icon_online_state(self.server != None)
                self.hold()
            self.rebuild_status_icon_menu()
        else:
            if self.status_icon != None:
                self.status_icon.set_visible(False)
                self.status_icon = None
                self.release()

    def update_status_icon_online_state(self, online=True):
        if self.status_icon == None:
            return

        if online:
            self.status_icon.set_icon_name("org.x.Warpinator-symbolic")
            self.status_icon.set_tooltip_text("Online")
        else:
            self.status_icon.set_icon_name("org.x.Warpinator-offline-symbolic")
            self.status_icon.set_tooltip_text("Offline")

        self.rebuild_status_icon_menu()

    def rebuild_status_icon_menu(self, remote_machine=None):
        if self.status_icon == None:
            return

        menu = Gtk.Menu()

        if self.server != None:
            self.add_favorite_entries(menu)

        item = Gtk.MenuItem(label=_("Open save folder"))
        item.connect("activate", lambda m: util.open_save_folder())
        menu.add(item)
        item = Gtk.MenuItem(label=_("Quit"))
        item.connect("activate", lambda i: self.exit_warp())
        menu.add(item)
        menu.show_all()

        self.status_icon.set_secondary_menu(menu)

    def add_favorite_entries(self, menu):
        remote_list = self.server.list_remote_machines()

        available_favorites = 0

        if remote_list:
            sorted_machines = sorted(remote_list, key=functools.cmp_to_key(util.sort_remote_machines))

            for machine in sorted_machines:
                if machine.favorite:
                    if machine.display_name != "":
                        name = machine.display_name
                    else:
                        name = machine.display_hostname
                    item = Gtk.MenuItem(label=name)
                    if machine.status == RemoteStatus.ONLINE:
                        available_favorites += 1
                    else:
                        item.set_sensitive(False)
                    self.attach_recent_submenu(item, machine)
                    menu.add(item)

        # If there is more than one online remote, add a 'send to all'
        if available_favorites > 1:
            menu.add(Gtk.SeparatorMenuItem())
            item = Gtk.MenuItem(label=_("Send to favorites"))
            self.attach_recent_submenu(item, None)
            menu.add(item)

        if available_favorites > 0:
            menu.add(Gtk.SeparatorMenuItem())

        menu.show_all()

    def attach_recent_submenu(self, menu, machine):
        sub = util.get_recent_chooser_menu()
        sub.connect("item-activated", self.status_icon_recent_item_selected, machine)
        sub.add(Gtk.SeparatorMenuItem(visible=True))

        picker = Gtk.MenuItem(label=_("Browse..."), visible=True)
        picker.connect("activate", self.open_file_picker, machine)
        sub.add(picker)

        menu.set_submenu(sub)

    def status_icon_recent_item_selected(self, chooser, remote_machine=None):
        uri = chooser.get_current_uri()

        self.send_status_icon_selection_to_machine(uri, remote_machine)

    def open_file_picker(self, button, remote_machine=None):
        dialog = util.create_file_and_folder_picker(self.window.window)

        res = dialog.run()

        if res == Gtk.ResponseType.ACCEPT:
            uri_list = dialog.get_uris()
            self.send_status_icon_selection_to_machine(uri_list, remote_machine)

        dialog.destroy()

    def send_status_icon_selection_to_machine(self, uri, remote_machine=None):
        if remote_machine:
            if isinstance(uri, list):
                remote_machine.send_files(uri)
            else:
                remote_machine.send_files([uri])
        else:
            for remote_machine in self.server.list_remote_machines():
                if remote_machine.favorite and remote_machine.status == RemoteStatus.ONLINE:
                    if isinstance(uri, list):
                        remote_machine.send_files(uri)
                    else:
                        remote_machine.send_files([uri])

    def on_tray_icon_activate(self, icon, button, time):
        self.window.toggle_visibility(time)

def main(test=False, debug=False):
    import signal

    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(util.WarpLogFormatter())
    logging.root.addHandler(log_handler)

    if debug:
        logging.root.setLevel(logging.DEBUG)
    else:
        logging.root.setLevel(logging.INFO)

    w = WarpApplication(test)
    signal.signal(signal.SIGINT, lambda s, f: w.exit_warp())
    signal.signal(signal.SIGTERM, lambda s, f: w.exit_warp())

    return w.run(sys.argv)

if __name__ == "__main__":
    main()

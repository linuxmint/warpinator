#!/usr/bin/python3

import gettext
import logging

from gi.repository import GObject, GLib, Gio

import grpc

import transfers
import prefs
import util
import notifications
from util import OpStatus, OpCommand, TransferDirection, ReceiveError

_ = gettext.gettext

class CommonOp(GObject.Object):
    __gsignals__ = {
        "status-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "initial-setup-complete": (GObject.SignalFlags.RUN_LAST, None, ()),
        "op-command": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "progress-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "active": (GObject.SignalFlags.RUN_LAST, None, ()),
        "focus": (GObject.SignalFlags.RUN_LAST, None, ())
    }
    def __init__(self, direction, sender, uris=None):
        super(CommonOp, self).__init__()
        self.uris = uris
        self.sender = sender
        self.direction = direction
        self.status = OpStatus.INIT
        self.start_time = GLib.get_monotonic_time() # for sorting in the op list

        self.total_size = 0
        self.total_count = 0
        self.size_string = ""
        self.description = ""
        self.name_if_single = None
        self.mime_if_single = "application/octet-stream" # unknown
        self.gicon = Gio.content_type_get_symbolic_icon(self.mime_if_single)

        self.error_msg = ""

        self.progress_tracker = None

    def progress_report(self, report):
        self.current_progress_report = report
        report.progress_text = _("%(time_left)s (%(bytes_per_sec)s/s)") \
                                   % ({
                                         "time_left": util.format_time_span(report.time_left_sec),
                                         "bytes_per_sec": GLib.format_size(report.bytes_per_sec)
                                     })

        if report.progress == 1.0:
            self.status = OpStatus.FINISHED
            self.emit_status_changed()
            return

        self.emit("active")
        self.emit("progress-changed")

    def get_progress_text(self):
        try:
            return self.current_progress_report.progress_text
        except AttributeError:
            return ""

    def get_progress(self):
        try:
            return self.current_progress_report.progress
        except AttributeError:
            return 0

    def set_error(self, e=None):
        if e is None:
            self.error_msg = ""
            return

        if isinstance(e, GLib.Error):
            self.error_msg = e.message
        elif isinstance(e, grpc.RpcError):
            self.error_msg = e.details()
        elif isinstance(e, ReceiveError):
            self.error_msg = str(e)
        else:
            self.error_msg = str(e)

    @util._idle
    def emit_initial_setup_complete(self):
        self.emit("initial-setup-complete")

    @util._idle
    def emit_status_changed(self):
        self.emit("status-changed")

    def set_status(self, status):
        pass

    def focus(self):
        self.emit("focus")

class SendOp(CommonOp):
    def __init__(self, sender=None, receiver=None, receiver_name=None, uris=None):
        super(SendOp, self).__init__(TransferDirection.TO_REMOTE_MACHINE, sender, uris)
        self.receiver = receiver
        self.sender_name = GLib.get_real_name()
        self.receiver_name = receiver_name

        self.resolved_files = []
        self.first_missing_file = None

        self.file_send_cancellable = None

        self.current_progress_report = None

        # These are the first-level base names (no path, just the filename) that we'll send to the server
        # to check for pre-existence.  We know that if these files/folders don't exist, none of their children
        # will.  This is a bit simple, but until we need more, it's fine.
        self.top_dir_basenames = []

    def set_status(self, status):
        self.status = status

        if status == OpStatus.FINISHED:
            notifications.TransferCompleteNotification(self, sender=True)
        elif status in (OpStatus.FAILED_UNRECOVERABLE, OpStatus.FAILED):
            notifications.TransferFailedNotification(self, sender=True)
         # We only care if the other remote cancelled.  If we did it, we don't need a notification.
        elif status == OpStatus.STOPPED_BY_RECEIVER:
            notifications.TransferStoppedNotification(self, sender=True)

        self.emit_status_changed()

    def prepare_send_info(self):
        self.status = OpStatus.CALCULATING
        self.emit_status_changed()

        error = transfers.gather_file_info(self)

        self.update_ui_info(error)

    def update_ui_info(self, error):
        if error is None:
            self.size_string = GLib.format_size(self.total_size)
            logging.debug("Op: calculated %d files, with a size of %s" % (self.total_count, self.size_string))

            if self.total_count > 1:
                # Translators: Don't need to translate singular, we show the filename if there's only one
                self.description = gettext.ngettext("%d file-do-not-translate",
                                                    "%d files", self.total_count) % (self.total_count,)
                self.gicon = Gio.ThemedIcon.new("edit-copy-symbolic")
            else:
                self.description = self.resolved_files[0].basename
                self.gicon = Gio.content_type_get_symbolic_icon(self.mime_if_single)

            self.set_status(OpStatus.WAITING_PERMISSION)
        else:
            if isinstance(error, GLib.Error) and error.code == Gio.IOErrorEnum.NOT_FOUND:
                self.status = OpStatus.FILE_NOT_FOUND
                self.description = ""
                self.error_msg = ""
                self.first_missing_file = self.top_dir_basenames[-1]
                self.gicon = Gio.ThemedIcon.new("dialog-error-symbolic")
            else:
                self.status = OpStatus.FAILED_UNRECOVERABLE
                self.description = ""
                self.set_error(error)

        self.emit_initial_setup_complete()
        self.emit_status_changed()

    # Widget handlers

    def cancel_transfer_request(self):
        self.emit("op-command", OpCommand.CANCEL_PERMISSION_BY_SENDER)

    def retry_transfer(self):
        self.emit("op-command", OpCommand.RETRY_TRANSFER)

    def pause_transfer(self):
        pass

    def stop_transfer(self):
        self.emit("op-command", OpCommand.STOP_TRANSFER_BY_SENDER)

    def remove_transfer(self):
        self.emit("op-command", OpCommand.REMOVE_TRANSFER)

# This represents a send or receive 'job', there would be potentially many of these.
class ReceiveOp(CommonOp):
    def __init__(self, sender):
        super(ReceiveOp, self).__init__(TransferDirection.FROM_REMOTE_MACHINE, sender)
        self.sender_name = self.sender
        self.receiver_name = GLib.get_real_name()

         # If there's insufficient disk space, always ask for permission
         # If we're overwriting, there's a preference to check whether we need to ask or not.
        self.have_space = False
        self.existing = False

        # This will be a <_Rendezvous object of in-flight RPC> if no compression is used, and a
        # SteamResponseWrapper (interceptors.py) if it is.
        self.file_iterator = None

        self.current_progress_report = None
        # These are the first-level base names (no path, just the filename) that we'll send to the server
        # to check for pre-existence.  We know that if these files/folders don't exist, none of their children
        # will.  This is a bit simple, but until we need more, it's fine.
        self.top_dir_basenames = []

    def set_status(self, status):
        self.status = status

        if status == OpStatus.FINISHED:
            notifications.TransferCompleteNotification(self, sender=False)
        elif status == OpStatus.FINISHED_WARNING:
            notifications.TransferCompleteNotification(self, sender=False, warn=True)
        elif status in (OpStatus.FAILED_UNRECOVERABLE, OpStatus.FAILED):
            notifications.TransferFailedNotification(self, sender=False)
         # We only care if the other remote cancelled.  If we did it, we don't need a notification.
        elif status == OpStatus.STOPPED_BY_SENDER:
            notifications.TransferStoppedNotification(self, sender=False)

        self.emit_status_changed()

    def prepare_receive_info(self):
        self.size_string = GLib.format_size(self.total_size)
        logging.debug("Op: details: %d files, with a size of %s" % (self.total_count, self.size_string))

        self.have_space = util.have_free_space(self.total_size)
        self.existing = util.files_exist(self.top_dir_basenames)
        self.update_ui_info()

    def update_ui_info(self):
        if self.total_count > 1:
            # Translators: Don't need to translate singular, we show the filename if there's only one
            self.description = gettext.ngettext("%d file",
                                                "%d files", self.total_count) % (self.total_count,)
            self.gicon = Gio.ThemedIcon.new("edit-copy-symbolic")
        else:
            self.description = self.name_if_single
            self.gicon = Gio.content_type_get_symbolic_icon(self.mime_if_single)

        self.status = OpStatus.WAITING_PERMISSION

        notifications.NewOpUserNotification(self)
        self.emit_initial_setup_complete()

    # Widget handlers
    def accept_transfer(self):
        self.emit("op-command", OpCommand.START_TRANSFER)

    def decline_transfer_request(self):
        self.emit("op-command", OpCommand.CANCEL_PERMISSION_BY_RECEIVER)

    def stop_transfer(self):
        self.emit("op-command", OpCommand.STOP_TRANSFER_BY_RECEIVER)

    def remove_transfer(self):
        self.emit("op-command", OpCommand.REMOVE_TRANSFER)


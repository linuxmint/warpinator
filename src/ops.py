import gettext

from gi.repository import GObject, GLib, Gio

import transfers
import util
from util import OpStatus, OpCommand

_ = gettext.gettext

# This represents a send or receive 'job', there would be potentially many of these.
class SendOp(GObject.Object):
    __gsignals__ = {
        "status-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "initial-setup-complete": (GObject.SignalFlags.RUN_LAST, None, ()),
        "op-command": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "progress-changed": (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self, direction, sender=None, receiver=None, receiver_name=None, uris=None):
        super(SendOp, self).__init__()
        self.uris = uris
        self.sender = sender
        self.receiver = receiver
        self.sender_name = util.accounts.get_real_name()
        self.receiver_name = receiver_name
        self.direction = direction
        self.status = OpStatus.INIT

        self.start_time = GLib.get_monotonic_time() # for sorting in the op list

        self.total_size = 0
        self.total_count = 0
        self.size_string = "" # I'd say 'Unknown' but that might be long enough to expand the label
        self.description = ""
        self.mime_if_single = "application/octet-stream" # unknown
        self.gicon = Gio.content_type_get_symbolic_icon(self.mime_if_single)
        self.resolved_files = []

        self.file_send_cancellable = None

        self.current_progress_report = None
        self.progress = 0.0
        self.progress_text = None

        # These are the first-level base names (no path, just the filename) that we'll send to the server
        # to check for pre-existence.  We know that if these files/folders don't exist, none of their children
        # will.  This is a bit simple, but until we need more, it's fine.
        self.top_dir_basenames = []

    def set_status(self, status):
        self.status = status
        self.emit_status_changed()

    def prepare_send_info(self):
        self.status = OpStatus.CALCULATING
        self.emit_status_changed()

        transfers.gather_file_info(self)
        self.size_string = GLib.format_size(self.total_size)
        print("Calculated %d files, with a size of %s" % (self.total_count, self.size_string))

        if self.total_count > 1:
            # Translators: Don't need to translate singular, we show the filename if there's only one
            self.description = gettext.ngettext("%d file",
                                                "%d files", self.total_count) % (self.total_count,)
            self.gicon = Gio.ThemedIcon.new("edit-copy-symbolic")
        else:
            self.description = self.resolved_files[0].basename
            self.gicon = Gio.content_type_get_symbolic_icon(self.mime_if_single)

        self.set_status(OpStatus.WAITING_PERMISSION)
        self.emit_initial_setup_complete()
        self.emit_status_changed()

    def progress_report(self, report):
        self.current_progress_report = report

        self.progress = report.progress
        if self.progress == 1.0:
            self.status = OpStatus.FINISHED
            self.emit_status_changed()
            return
        else:
            self.progress_text = _("%s (%s/s)") % (util.format_time_span(report.time_left_sec), GLib.format_size(report.bytes_per_sec))

        self.emit("progress-changed")
        self.emit("op-command", OpCommand.UPDATE_PROGRESS)

    @util._idle
    def emit_initial_setup_complete(self):
        self.emit("initial-setup-complete")

    @util._idle
    def emit_status_changed(self):
        self.emit("status-changed")

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
class ReceiveOp(GObject.Object):
    __gsignals__ = {
        "status-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "initial-setup-complete": (GObject.SignalFlags.RUN_LAST, None, ()),
        "op-command": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "progress-changed": (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self, direction, sender=None, uris=None):
        super(ReceiveOp, self).__init__()
        self.uris = uris
        self.sender = sender
        self.sender_name = self.sender
        self.receiver_name = util.accounts.get_real_name()
        self.direction = direction
        self.status = OpStatus.INIT

        self.start_time = GLib.get_monotonic_time() # for sorting in the op list

        self.total_size = 0
        self.total_count = 0
        self.size_string = "--" # I'd say 'Unknown' but that might be long enough to expand the label
        self.description = "--"
        self.mime_if_single = "application/octet-stream" # unknown
        self.gicon = Gio.content_type_get_symbolic_icon(self.mime_if_single)

        # This is set when a transfer starts - it's a grpc.Future that we can cancel() if the user
        # wants the transfer to stop.
        self.file_iterator = None

        self.current_progress_report = None
        self.progress = 0.0
        self.progress_text = None
        # These are the first-level base names (no path, just the filename) that we'll send to the server
        # to check for pre-existence.  We know that if these files/folders don't exist, none of their children
        # will.  This is a bit simple, but until we need more, it's fine.
        self.top_dir_basenames = []

    def set_status(self, status):
        self.status = status
        self.emit_status_changed()

    def prepare_receive_info(self):
        self.size_string = GLib.format_size(self.total_size)
        print("Transfer request received for %d files, with a size of %s" % (self.total_count, self.size_string))

        if self.total_count > 1:
            # Translators: Don't need to translate singular, we show the filename if there's only one
            self.description = gettext.ngettext("%d file",
                                                "%d files", self.total_count) % (self.total_count,)
            self.gicon = Gio.ThemedIcon.new("edit-copy-symbolic")
        else:
            self.description = self.name_if_single
            self.gicon = Gio.content_type_get_symbolic_icon(self.mime_if_single)

        self.status = OpStatus.WAITING_PERMISSION
        self.emit_initial_setup_complete()

    def update_progress(self, report):
        self.current_progress_report = report
        self.progress = report.progress
        self.progress_text = _("%s (%s/s)") % (util.format_time_span(report.time_left_sec), GLib.format_size(report.bytes_per_sec))

        self.emit("progress-changed")

    @util._idle
    def emit_initial_setup_complete(self):
        self.emit("initial-setup-complete")

    @util._idle
    def emit_status_changed(self):
        self.emit("status-changed")

    # Widget handlers
    def accept_transfer(self):
        self.emit("op-command", OpCommand.START_TRANSFER)

    def decline_transfer_request(self):
        self.emit("op-command", OpCommand.CANCEL_PERMISSION_BY_RECEIVER)

    def stop_transfer(self):
        self.emit("op-command", OpCommand.STOP_TRANSFER_BY_RECEIVER)

    def remove_transfer(self):
        self.emit("op-command", OpCommand.REMOVE_TRANSFER)


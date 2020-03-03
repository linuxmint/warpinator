import threading
import socket
import gettext
import math
import os

from gi.repository import GLib, Gtk, Gdk, GObject, GdkPixbuf, Gio

import prefs

_ = gettext.gettext

from accountsService import AccountsServiceClient
accounts = AccountsServiceClient()

from enum import IntEnum
TransferDirection = IntEnum('TransferDirection', 'TO_REMOTE_MACHINE \
                                                  FROM_REMOTE_MACHINE')

FileType = IntEnum('FileType', 'REGULAR \
                                DIRECTORY \
                                SYMBOLIC_LINK')


# Online - all ok
# Offline - no presence at all
# Init connecting - we've just discovered you
# Unreachable - we've either tried and failed after initial discovery, or something went wrong during the session

RemoteStatus = IntEnum('RemoteStatus', 'ONLINE \
                                        OFFLINE \
                                        INIT_CONNECTING \
                                        UNREACHABLE')

OpStatus = IntEnum('OpStatus', 'INIT \
                                CALCULATING \
                                WAITING_PERMISSION \
                                CANCELLED_PERMISSION_BY_SENDER \
                                CANCELLED_PERMISSION_BY_RECEIVER \
                                TRANSFERRING \
                                PAUSED \
                                STOPPED_BY_SENDER \
                                STOPPED_BY_RECEIVER \
                                FAILED \
                                FILE_NOT_FOUND \
                                FINISHED')

OpCommand = IntEnum('OpCommand', 'START_TRANSFER \
                                  UPDATE_PROGRESS \
                                  CANCEL_PERMISSION_BY_SENDER \
                                  CANCEL_PERMISSION_BY_RECEIVER \
                                  PAUSE_TRANSFER \
                                  RETRY_TRANSFER \
                                  STOP_TRANSFER_BY_SENDER \
                                  STOP_TRANSFER_BY_RECEIVER \
                                  REMOVE_TRANSFER')

class ProgressCallbackInfo():
    def __init__(self, progress=0, speed_str="", time_left_str="",
                 finished=False, sender_awaiting_approval=False,
                 transfer_refused=False, transfer_starting=False,
                 transfer_exists=False, transfer_cancelled=False,
                 transfer_diskfull=False, error=None, size=0, count=0):
        self.progress = progress
        self.speed = speed_str
        self.time_left = time_left_str
        self.finished = finished
        self.sender_awaiting_approval = sender_awaiting_approval
        self.count = count
        self.size = size
        self.error = error
        self.transfer_starting = transfer_starting
        self.transfer_cancelled = transfer_cancelled
        self.transfer_refused = transfer_refused
        self.transfer_exists = transfer_exists
        self.transfer_diskfull = transfer_diskfull

    def is_informational(self):
        return True in (self.sender_awaiting_approval,
                        self.transfer_refused,
                        self.transfer_starting,
                        self.transfer_cancelled,
                        self.transfer_exists,
                        self.transfer_diskfull)

    def is_fail_state(self):
        return True in (self.transfer_refused,
                        self.transfer_cancelled,
                        self.transfer_exists,
                        self.transfer_diskfull,
                        self.error)

# A normal GtkFileChooserDialog only lets you pick folders OR files, not
# both in the same dialog.  This does.
def create_file_and_folder_picker(parent=None):
    window = Gtk.Dialog(title=_("Select file(s) to send"),
                        parent=None)
    window.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                       _("Send"), Gtk.ResponseType.ACCEPT)

    chooser = Gtk.FileChooserWidget(action=Gtk.FileChooserAction.OPEN,
                                    select_multiple=True)
    chooser.connect("file-activated", lambda chooser: window.response(Gtk.ResponseType.ACCEPT))

    chooser.show_all()
    window.get_content_area().add(chooser)

    window.get_uris = chooser.get_uris
    return window

# Used as a decorator to run things in the background
def _async(func):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread
    return wrapper

# Used as a decorator to run things in the main loop, from another thread
def _idle(func):
    def wrapper(*args, **kwargs):
        GLib.idle_add(func, *args, **kwargs)
    return wrapper

def gfiletype_to_int_enum(gfiletype):
    if gfiletype == Gio.FileType.DIRECTORY:
        return FileType.DIRECTORY
    elif gfiletype == Gio.FileType.SYMBOLIC_LINK:
        return FileType.SYMBOLIC_LINK
    else:
        return FileType.REGULAR

def open_save_folder(widget=None, data=None):
    app = Gio.AppInfo.get_default_for_type("inode/directory", True)
    try:
        file = Gio.File.new_for_uri(prefs.get_save_path())
        app.launch((file,), None)
    except GLib.Error as e:
        print("Could not open received files location: %s" % e.message)

def verify_save_folder(transient_for=None):
    if not os.access(prefs.get_save_path(), os.R_OK | os.W_OK):
        dialog = Gtk.MessageDialog(title=_("Invalid save folder"),
                                   parent=transient_for,
                                   destroy_with_parent=True,
                                   message_type=Gtk.MessageType.ERROR,
                                   use_markup=True,
                                   modal=True,
                                   text=_("""The current save location '%s' is not currently accessible. \
                                             You will not be able to receive files until this is resolved""") % prefs.get_save_path())
        dialog.add_buttons(_("Close"), Gtk.ResponseType.CLOSE)

        res = dialog.run()
        dialog.destroy()

def have_free_space(size):
    save_file = Gio.File.new_for_path(prefs.get_save_path())

    try:
        info = save_file.query_filesystem_info(Gio.FILE_ATTRIBUTE_FILESYSTEM_FREE, None)
    except GLib.Error as e:
        print("Unable to check free space in save location (%s), but proceeding anyhow" % self.save_location)
        return True

    free = info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_FILESYSTEM_FREE)

    # I guess we could have exactly 0 bytes free, but I think you'd have larger problems.  I want to make sure
    # here that we don't fail because we didn't get a valid number.
    if free == 0:
        return True
    print("Need: %s, have %s" % (GLib.format_size(size), GLib.format_size(free)))
    return size < free

def files_exist(base_names):
    for name in base_names:
        path = os.path.join(prefs.get_save_path(), name)
        print("(server side) Checking if file or folder %s already exists." % (path,))
        if GLib.file_test(path, GLib.FileTest.EXISTS):
            return True

    return False

def check_ml(fid):
    on_ml = threading.current_thread() == threading.main_thread()
    print("%s on mainloop: " % fid, on_ml)

def get_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        ans = s.getsockname()[0]
        return ans

def get_hostname():
    return GLib.get_host_name()

def relpath_from_uri(child_uri, base_uri):
    child_uri = GLib.uri_unescape_string(child_uri)
    base_uri = GLib.uri_unescape_string(base_uri)

    if child_uri.startswith(base_uri):
        return child_uri.replace(base_uri + "/", "")
    else:
        return None

def sort_remote_machines(am, bm):
    if am.favorite and not bm.favorite:
        return -1
    elif bm.favorite and not am.favorite:
        return +1
    elif am.recent_time > bm.recent_time:
        return -1
    elif bm.recent_time > bm.recent_time:
        return +1
    elif am.display_name and not bm.display_name:
        return -1
    elif bm.display_name and not am.display_name:
        return +1

    return -1 if am.display_name < bm.display_name else +1

# adapted from nemo-file-operations.c: format_time()
def format_time_span(seconds):
    if seconds < 0:
        seconds = 0

    if (seconds < 10):
        return _("A few seconds remaining")

    if (seconds < 60):
        return _("%d seconds remaining") % seconds

    if (seconds < 60 * 60):
        minutes = int(seconds / 60)
        return gettext.ngettext("%d minute", "%d minutes", minutes) % minutes

    hours = seconds / (60 * 60)

    if seconds < (60 * 60 * 4):
        minutes = int((seconds - hours * 60 * 60) / 60)

        h = gettext.ngettext ("%d hour", "%d hours", hours) % hours
        m = gettext.ngettext ("%d minute", "%d minutes", minutes) % minutes
        res = "%s, %s" % (h, m)
        return res;

    return gettext.ngettext("approximately %d hour", "approximately %d hours", hours) % hours


# adapted from nemo-file-operations.c: format_time()
def precise_format_time_span(micro):
    sdec, total_seconds = math.modf(micro / 1000 / 1000)
    seconds = total_seconds % 60
    mdec, total_minutes = math.modf(total_seconds / 60)
    minutes = total_minutes % 60
    hdec, total_hours = math.modf(total_minutes / 60)
    hours = total_hours % 60
    return ("%02d:%02d:%02d.%s" % (hours, minutes, seconds, str(sdec)[2:5]))

def get_global_scale_factor():
    screen = Gdk.Screen.get_default()

    v = GObject.Value(int)

    if screen.get_setting("gdk-window-scaling-factor", v):
        return v.get_value()

    return 1

class CairoSurfaceLoader(GObject.Object):
    __gsignals__ = {
        # 'surface-ready': (GObject.SignalFlags.RUN_LAST, None, (cairo.Surface,))
        'error': (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self, icon_size=Gtk.IconSize.DND):
        self.loader =GdkPixbuf.PixbufLoader()
        self.loader.connect("size-prepared", self.on_loader_size_prepared)

        s, w, h = Gtk.IconSize.lookup(icon_size)

        self.surface_size = w
        self.pixbuf_size = w * get_global_scale_factor()

    def on_loader_size_prepared(self, loader, width, height, data=None):
        new_width = self.pixbuf_size
        new_height = self.pixbuf_size

        if width != height:
            if width > height:
                aspect_ratio = height / width

                new_width = self.target_size
                new_height = new_width * aspect_ratio
            else:
                aspect_ratio = width / height

                new_height = self.target_size
                new_width = new_height * aspect_ratio

        self.loader.set_size(new_width, new_height)

    def add_bytes(self, _bytes):
        try:
            self.loader.write_bytes(GLib.Bytes(_bytes))
        except GLib.Error:
            try:
                self.loader.close()
            except:
                pass

            self.emit("error")

    def get_surface(self):
        try:
            self.loader.close()
            pixbuf = self.loader.get_pixbuf()

            if pixbuf:
                surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf,
                                                               get_global_scale_factor(),
                                                               None)
                return surface
        except:
            self.emit("error")

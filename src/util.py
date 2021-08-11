#!/usr/bin/python3

import threading
import gettext
import math
import logging
import os
import socket
import traceback
from concurrent.futures import ThreadPoolExecutor

from gi.repository import GLib, Gtk, Gdk, GObject, GdkPixbuf, Gio

import prefs
import config

_ = gettext.gettext

# Not sure what the ideal count is, too few and there will be waits if a lot of
# transfers are happening.  The server runs on its own thread, and has its own thread
# pool to service incoming rpcs. Each remote uses one thread for its connection loop,
# and all remotes share this thread pool for outgoing calls. It could be we may need
# to limit the number of simultaneous ops in the gui.
#
# Both server and remote thread pool sizes can be adjusted in dconf.
global_rpc_threadpool = None

# Initializing in thie function avoids a circular import due to prefs.get_thread_count()
def initialize_rpc_threadpool():
    global global_rpc_threadpool
    global_rpc_threadpool = ThreadPoolExecutor(max_workers=prefs.get_remote_pool_max_threads())

from enum import IntEnum
TransferDirection = IntEnum('TransferDirection', 'TO_REMOTE_MACHINE \
                                                  FROM_REMOTE_MACHINE')

# Using Gio enums fails for some unknown reason when collecting file info sometimes.
# Avoid introspection.
FileType = IntEnum('FileType', (('REGULAR', Gio.FileType.REGULAR),
                                ('DIRECTORY', Gio.FileType.DIRECTORY),
                                ('SYMBOLIC_LINK', Gio.FileType.SYMBOLIC_LINK)))

# Online - all ok
# Offline - no presence at all
# Init connecting - we've just discovered you
# Unreachable - we've either tried and failed after initial discovery, or something went wrong during the session

RemoteStatus = IntEnum('RemoteStatus', 'ONLINE \
                                        OFFLINE \
                                        INIT_CONNECTING \
                                        UNREACHABLE \
                                        AWAITING_DUPLEX')

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
                                FAILED_UNRECOVERABLE \
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

class InterfaceInfo():
    def __init__(self, ip4, ip6, iface=None):
        self.iface = iface
        # netifaces AF_INET and AF_INET6 dicts
        self.ip4 = ip4
        self.ip4_address = self.ip4["addr"]

        try:
            self.ip6 = ip6
            self.ip6_address = self.ip6["addr"]
        except:
            self.ip6 = None
            self.ip6_address = None

    def __eq__(self, other):
        if other == None:
            return False

        return self.ip4_address == other.ip4_address

    def as_binary_list(self):
        blist = []

        if self.ip4:
            try:
                blist.append(socket.inet_pton(GLib.SYSDEF_AF_INET, self.ip4_address))
            except:
                pass
        if self.ip6:
            try:
                blist.append(socket.inet_pton(GLib.SYSDEF_AF_INET6, self.ip6_address))
            except:
                pass

        return blist

class RemoteInterfaceInfo():
    def __init__(self, blist):
        ip4 = None
        ip6 = None

        for item in blist:
            try:
                ip4 = socket.inet_ntop(socket.AF_INET, item)
            except ValueError:
                ip6 = socket.inet_ntop(socket.AF_INET6, item)

        if ip4:
            self.ip4_address = ip4
        if ip6:
            self.ip6_address = ip6

    def __eq__(self, other):
        if other == None:
            return False

        return self.ip4_address == other.ip4_address

last_location = Gio.File.new_for_path(GLib.get_home_dir())
# A normal GtkFileChooserDialog only lets you pick folders OR files, not
# both in the same dialog.  This does.

class FolderFileChooserDialog(Gtk.Dialog):
    def __init__(self, window_title, transient_parent, starting_location):
        super(FolderFileChooserDialog, self).__init__(title=window_title,
                                                      parent=transient_parent,
                                                      default_width=750,
                                                      default_height=500)

        self.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                         _("Add"), Gtk.ResponseType.OK)

        self.chooser = Gtk.FileChooserWidget(action=Gtk.FileChooserAction.OPEN, select_multiple=True)
        self.chooser.set_current_folder_file(starting_location)
        self.chooser.connect("file-activated", lambda chooser: self.response(Gtk.ResponseType.OK))
        self.chooser.show_all()

        self.get_content_area().add(self.chooser)
        self.get_content_area().set_border_width(0)
        self.get_uris = self.chooser.get_uris
        self.get_current_folder_file = self.chooser.get_current_folder_file
        self.connect("key-press-event", self.on_button_press)

    def on_button_press(self, widget, event, data=None):
        multi = len(self.chooser.get_uris()) != 1
        if event.keyval in (Gdk.KEY_KP_Enter, Gdk.KEY_Return) and multi:
            self.response(Gtk.ResponseType.OK)
            return Gdk.EVENT_STOP

        return Gdk.EVENT_PROPAGATE

def create_file_and_folder_picker(dialog_parent=None):
    chooser = FolderFileChooserDialog(_("Select file(s) to send"), dialog_parent, last_location)

    def update_last_location(dialog, response_id, data=None):
        if response_id != Gtk.ResponseType.OK:
            return

        global last_location
        last_location = chooser.get_current_folder_file()

    chooser.connect("response", update_last_location)
    return chooser

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

def print_stack():
    traceback.print_stack()

def open_save_folder(filename=None):
    bus = Gio.Application.get_default().get_dbus_connection()

    if filename != None:
        abs_path = os.path.join(prefs.get_save_path(), filename)

        if os.path.isfile(abs_path):
            file = Gio.File.new_for_path(abs_path)

            startup_id = str(os.getpid())

            try:
                bus.call_sync("org.freedesktop.FileManager1",
                              "/org/freedesktop/FileManager1",
                              "org.freedesktop.FileManager1",
                              "ShowItems",
                              GLib.Variant("(ass)",
                                           ([file.get_uri()], startup_id)),
                              None,
                              Gio.DBusCallFlags.NONE,
                              1000,
                              None)
                logging.debug("Opening save folder using dbus")
                return
            except GLib.Error as e:
                pass

    app = Gio.AppInfo.get_default_for_type("inode/directory", True)

    try:
        logging.debug("Opening save folder using Gio (mimetype)")
        Gio.AppInfo.launch_default_for_uri(prefs.get_save_uri(), None)
    except GLib.Error as e:
        logging.critical("Could not open received files location: %s" % e.message)

def verify_save_folder(transient_for=None):
    return os.access(prefs.get_save_path(), os.R_OK | os.W_OK)

def save_folder_is_native_fs():
    return True

def have_free_space(size):
    save_file = Gio.File.new_for_path(prefs.get_save_path())

    try:
        info = save_file.query_filesystem_info(Gio.FILE_ATTRIBUTE_FILESYSTEM_FREE, None)
    except GLib.Error:
        logging.warning("Unable to check free space in save location (%s), but proceeding anyhow" % prefs.get_save_path())
        return True

    free = info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_FILESYSTEM_FREE)

    # I guess we could have exactly 0 bytes free, but I think you'd have larger problems.  I want to make sure
    # here that we don't fail because we didn't get a valid number.
    if free == 0:
        return True

    logging.debug("need: %s, have %s" % (GLib.format_size(size), GLib.format_size(free)))

    return size < free

def files_exist(base_names):
    for name in base_names:
        path = os.path.join(prefs.get_save_path(), name)
        logging.debug("(server side) Checking if file or folder %s already exists." % (path,))
        if GLib.file_test(path, GLib.FileTest.EXISTS):
            return True

    return False

def check_ml(fid):
    on_ml = threading.current_thread() == threading.main_thread()
    print("%s on mainloop: " % fid, on_ml)

def get_hostname():
    return GLib.get_host_name()

def get_local_name(hostname=get_hostname()):
    local_name = "%s@%s" % (GLib.get_user_name(), hostname)
    real_name = GLib.get_real_name()
    if real_name is not None and real_name != "" and real_name != "Unknown":
        # according to glib's doc, it can actually return "Unknown"
        local_name = "%s - %s" % (real_name, local_name)
    return local_name

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
    elif bm.recent_time > am.recent_time:
        return +1
    elif am.display_name and not bm.display_name:
        return -1
    elif bm.display_name and not am.display_name:
        return +1
    elif not am.display_name and not bm.display_name:
        return -1 if am.hostname < bm.hostname else +1

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
        minutes = round(seconds / 60)
        return gettext.ngettext("%d minute", "%d minutes", minutes) % minutes

    hours = math.floor(seconds / (60 * 60))

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

                new_width = self.pixbuf_size
                new_height = new_width * aspect_ratio
            else:
                aspect_ratio = width / height

                new_height = self.pixbuf_size
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

class AboutDialog():
    def __init__(self, parent):
        # Maybe this can be configured during the build? But this works.
        if config.FLATPAK_BUILD:
            name = "Warpinator (Flatpak)"
        else:
            name = "Warpinator"

        dialog = Gtk.AboutDialog(parent=parent,
                                 title=_("About"),
                                 program_name=name,
                                 icon_name="org.x.Warpinator",
                                 logo_icon_name="org.x.Warpinator",
                                 comments=_("Send and Receive Files across the Network"),
                                 version=config.VERSION,
                                 license_type=Gtk.License.GPL_3_0)

        dialog.run()
        dialog.destroy()

class WarpLogFormatter(logging.Formatter):
    dbg_crit_format = "%(asctime)-15s::warpinator::%(levelname)s: %(message)s -- %(filename)s (line %(lineno)d)"
    info_format = "%(asctime)-15s::warpinator: %(message)s"

    def __init__(self):
        super().__init__()

    def format(self, record):
        if record.levelno in (logging.DEBUG, logging.ERROR):
            self._style._fmt = WarpLogFormatter.dbg_crit_format

        elif record.levelno == logging.INFO:
            self._style._fmt = WarpLogFormatter.info_format

        result = logging.Formatter.format(self, record)

        return result


recent_manager = Gtk.RecentManager()

def add_to_recents_if_single_selection(uri_list):
    if len(uri_list) == 1:
        try:
            recent_manager.add_item(uri_list[0])
        except Exception as e:
            logging.warning("Could not add '%s' single item to recent files: %s" % e)

def get_recent_chooser_menu():
    chooser = Gtk.RecentChooserMenu(show_tips=True,
                                    sort_type=Gtk.RecentSortType.MRU,
                                    show_not_found=False)

    return chooser

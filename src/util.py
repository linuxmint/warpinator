#!/usr/bin/python3

import threading
import gettext
import math
import logging
import os
from pathlib import Path
import queue
import sys
import socket
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from gi.repository import GLib, Gtk, Gdk, GObject, GdkPixbuf, Gio

import prefs
import config

try:
    import landlock
except Exception:
    pass

_ = gettext.gettext

# Not sure what the ideal count is, too few and there will be waits if a lot of
# transfers are happening.  The server runs on its own thread, and has its own thread
# pool to service incoming rpcs. Each remote uses one thread for its connection loop,
# and all remotes share this thread pool for outgoing calls. It could be we may need
# to limit the number of simultaneous ops in the gui.
#
# Both server and remote thread pool sizes can be adjusted in dconf.
global_rpc_threadpool = None

LANDLOCK_METHODS = [
    "start_transfer_op"
]

# Initializing in thie function avoids a circular import due to prefs.get_thread_count()
def initialize_rpc_threadpool():
    global global_rpc_threadpool

    if config.sandbox_mode == "landlock":
        logging.debug("Using NewThreadExecutor")
        global_rpc_threadpool = NewThreadExecutor()
    else:
        logging.debug("Using ThreadPoolExecutor")
        global_rpc_threadpool = ThreadPoolExecutor(max_workers=prefs.get_remote_pool_max_threads())

class NewThreadExecutor():
    def __init__(self):
        self.max_workers = prefs.get_remote_pool_max_threads()
        self.transfer_queue = queue.SimpleQueue()

        self._threads = {}
        self.count = 0
        self._shutdown = False
        self._wait_condition = threading.Condition()
        self._thread_store_lock = threading.Lock()

        self._factory_thread = threading.Thread(target=self.factory_thread_func, name="NewThreadExecutor-factory-thread")
        self._factory_thread.start()

    def factory_thread_func(self):
        while True:
            with self._wait_condition:
                if self.transfer_queue.empty() and not self._shutdown:
                    logging.debug("NewThreadExecutor: Waiting on an op")
                    self._wait_condition.wait()

            if self._shutdown:
                logging.debug("NewThreadExecutor: Factory shutting down")
                break

            try:
                opinfo = self.transfer_queue.get_nowait()
                self.spawn_thread(opinfo)
            except queue.Empty:
                logging.debug("NewThreadExecutor: factory thread woke but nothing to do.")

        logging.debug("NewThreadExecutor: Shutting down - waiting on workers")
        while True:
            with self._thread_store_lock:
                if self.count == 0:
                    break
            logging.debug("sleep")
            sleep(.1)
        logging.debug("NewThreadExecutor: done waiting for workers, end factory thread")

    def submit(self, func, *args, **kargs):
        # self._shutdown will only ever be set to True once, no need to lock
        if self._shutdown:
            raise RuntimeError("Cannot start new transfer threads, shutting down.")

        logging.debug("NewThreadExecutor: Adding op to queue (%s)" % func.__name__)
        self.transfer_queue.put((func, args, kargs))

        # Poke the factory thread.
        with self._wait_condition:
            logging.debug("NewThreadExecutor: Poking the factory.")
            self._wait_condition.notify()

    def spawn_thread(self, opinfo):
        tname = "op-thread-%d" % GLib.get_monotonic_time()
        t = threading.Thread(target=self._transfer_thread_func, name=tname, args=(opinfo,))

        with self._thread_store_lock:
            self.count += 1
            self._threads[tname] = t
            logging.debug("NewThreadExecutor: Starting thread for op: %s, thread count UP: %s" % (tname, self.count))
        t.start()

    def _transfer_thread_func(self, opinfo):
        if opinfo[0].__name__ in LANDLOCK_METHODS:
            logging.debug("NewThreadExecutor: Applying landlock to new op")
            rs = landlock.Ruleset()
            rs.allow(prefs.get_save_path())
            rs.apply()

        opinfo[0](*opinfo[1], **opinfo[2])

        with self._thread_store_lock:
            self.count -= 1
            del self._threads[threading.current_thread().name]
            logging.debug("NewThreadExecutor: Finished op call, thread count DOWN: %d" % self.count)
        # Poke the factory thread in case there were ops waiting on an available thread.
        with self._wait_condition:
            self._wait_condition.notify()

    def shutdown(self, wait=True):
        logging.debug("NewThreadExecutor: Shutting down")
        self._shutdown = True

        with self._wait_condition:
            self._wait_condition.notify()

        logging.debug("NewThreadExecutor: Shutting down - waiting on factory thread")
        self._factory_thread.join()
        logging.debug("NewThreadExecutor: Shutdown complete")

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
                                FINISHED \
                                FINISHED_WARNING')

OpCommand = IntEnum('OpCommand', 'START_TRANSFER \
                                  UPDATE_PROGRESS \
                                  CANCEL_PERMISSION_BY_SENDER \
                                  CANCEL_PERMISSION_BY_RECEIVER \
                                  PAUSE_TRANSFER \
                                  RETRY_TRANSFER \
                                  STOP_TRANSFER_BY_SENDER \
                                  STOP_TRANSFER_BY_RECEIVER \
                                  REMOVE_TRANSFER')

class ReceiveError(Exception):
    def __init__(self, message, fatal=True):
        self.fatal = fatal
        logging.debug("ReceiveError: (fatal: %d): %s" % (self.fatal, message))
        super().__init__(message)

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
        if other is None:
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
        if other is None:
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

def open_save_folder(filename=None):
    # Using the fdo FileManager1 interface is the best choice if it's available,
    # as it won't be restricted to the bubblewrapped read-only environment.
    #
    # The only possible downside to this is you can't necessarily be sure which
    # file manager might answer, if more than one is installed:
    # https://github.com/linuxmint/nemo/commit/c9cbba6a2f08be69bf02ffcaf9b0faf4a03ace8b

    bus = Gio.Application.get_default().get_dbus_connection()

    if filename is not None:
        method = "ShowItems"
        abs_path = os.path.join(prefs.get_save_path(), filename)
    else:
        method = "ShowFolders"
        abs_path = prefs.get_save_path()

    file = Gio.File.new_for_path(abs_path)
    startup_id = str(os.getpid())

    try:
        bus.call_sync("org.freedesktop.FileManager1",
                      "/org/freedesktop/FileManager1",
                      "org.freedesktop.FileManager1",
                      method,
                      GLib.Variant("(ass)",
                                   ([file.get_uri()], startup_id)),
                      None,
                      Gio.DBusCallFlags.NONE,
                      1000,
                      None)
        logging.debug("Opening save folder using dbus")
        return
    except GLib.Error as e:
        logging.debug("Could not use dbus interface to launch file manager: %s" % e.message)

    # If dbus doesn't work, use xdg mimetype handlers.
    app = Gio.AppInfo.get_default_for_type("inode/directory", True)

    try:
        logging.debug("Opening save folder using Gio (mimetype)")
        Gio.AppInfo.launch_default_for_uri(prefs.get_save_uri(), None)
    except GLib.Error as e:
        logging.critical("Could not open received files location: %s" % e.message)

def verify_save_folder(transient_for=None):
    # Forbidden locations for incoming files, relative to home.
    forbidden_folders = [
        ".config",
        ".cache",
        ".local",
        ".dbus",
        ".ssh",
        ".mozilla",
        ".thunderbird",
        ".Trash-"
    ]

    save_path = Path(prefs.get_save_path()).resolve()
    home = Path.home()

    if not save_path.exists():
        return False

    if save_path.samefile(home):
        return False

    for folder in forbidden_folders:
        test_path = home.joinpath(folder)
        try:
            if save_path.relative_to(test_path):
                return False
        except ValueError:
            pass

    return os.access(save_path, os.R_OK | os.W_OK)

def test_resolved_path_safety(relative_path):
    # Check for valid path (pathlib.Path resolves both relative and symbolically-linked paths)
    base = Path(prefs.get_save_path())
    unresolved = base.joinpath(relative_path)

    try:
        resolved = unresolved.resolve()

        # Not outside the base folder (raises ValueError)
        relative = resolved.relative_to(base)

        # Not the base folder (../Warpinator.. )
        try:
            if resolved.samefile(base):
                raise ValueError()
        except OSError:
            # resolved doesn't exist, so it can't be the same
            pass
    except RuntimeError as e:
        raise ReceiveError("Could not resolve path '%s': %s" % str(e))
    except ValueError:
        raise ReceiveError("Resolved path is not valid child of the save folder: %s -> %s" % (unresolved, str(resolved)), fatal=True)

def save_folder_is_native_fs():
    file = Gio.File.new_for_path(prefs.get_save_path())
    return file.is_native()

def trash_uri_supported():
    vfs = Gio.Vfs.get_default()
    return "trash" in vfs.get_supported_uri_schemes()

def open_trash():
    Gio.AppInfo.launch_default_for_uri("trash:///", None)

def disk_usage_available():
    return GLib.find_program_in_path("baobab")

def open_disk_usage():
    if GLib.find_program_in_path("baobab"):
        GLib.spawn_async(["baobab", GLib.get_home_dir()], flags=GLib.SpawnFlags.SEARCH_PATH_FROM_ENVP)

free_space_monitor = None
MB_TO_B = 1024 * 1024

def initialize_free_space_monitor():
    global free_space_monitor
    free_space_monitor  = FreeSpaceMonitor()

class FreeSpaceMonitor(GObject.Object):
    __gsignals__ = {
        "low-space": (GObject.SignalFlags.RUN_LAST, None, ()),
        "folder-changed": (GObject.SignalFlags.RUN_LAST, None, ())
    }

    poll_levels = [
        [ 250 * MB_TO_B,     0.05 ],
        [ 1000 * MB_TO_B,    0.50 ],
        [ 10000 * MB_TO_B,   5.00 ],
        [ 100000 * MB_TO_B, 30.00 ]
    ]

    def __init__(self):
        GObject.Object.__init__(self)
        logging.debug("FreeSpaceMonitor new")

        self._monitor_thread = None

        # Shutdown thread when warpinator is exiting
        self._cancellable = Gio.Cancellable()
        # Pause/resume thread
        self._monitor_enable = threading.Event()

        self._available_bytes_lock = threading.Lock()
        self.sleep_time = 0
        self.available_bytes = 0
        self.min_free = prefs.get_min_free_space()
        self.save_folder = Gio.File.new_for_path(prefs.get_save_path())

        prefs.prefs_settings.connect("changed::receiving-folder", self._folder_setting_changed)
        prefs.prefs_settings.connect("changed::minimum-free-space", self._folder_setting_changed)

    def _folder_setting_changed(self, settings, key, data=None):
        new_folder = Gio.File.new_for_path(prefs.get_save_path())
        new_min_free = prefs.get_min_free_space()

        if not self.save_folder.equal(new_folder):
            self.save_folder = new_folder
            self.emit("folder-changed")

        if self.min_free != new_min_free:
            self.have_enough_free(0)

    def get_free(self):
        with self._available_bytes_lock:
            return self.available_bytes

    def have_enough_free(self, size, top_dir_basenames=[]):
        self.save_folder = Gio.File.new_for_path(prefs.get_save_path())
        self.min_free = prefs.get_min_free_space()

        # Existing files haven't been removed yet, so their contents' size needs to be
        # taken into account.
        existing_allocation = 0

        for basename in top_dir_basenames:
            path = os.path.join(prefs.get_save_path(), basename)
            if not os.path.exists(path):
                continue
            folder_file = Gio.File.new_for_path(path)

            def get_contents_size(file):
                if file.query_file_type(Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None) != FileType.DIRECTORY:
                    info = file.query_info("standard::allocated-size",
                                           Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                                           None)
                    if info:
                        return info.get_attribute_uint64("standard::allocated-size")
                    else:
                        return 0

                size = 0
                enumerator = file.enumerate_children("standard::allocated-size",
                                                     Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                                                     None)
                info = enumerator.next_file(None)
                while info:
                    child = enumerator.get_child(info)
                    child_uri = child.get_uri()
                    child_basename = child.get_basename()

                    file_type = info.get_file_type()

                    if file_type == FileType.DIRECTORY:
                        size += get_contents_size(child)
                    else:
                        size += info.get_attribute_uint64("standard::allocated-size")

                    info = enumerator.next_file(None)

                return size
            existing_allocation += get_contents_size(folder_file)

        # Only do an explicit refresh if the monitor thread is *not* running. If it is running,
        # refresh_available is already being called regularly.
        if not self._monitor_enable.is_set():
            self._refresh_available(self._cancellable)

        with self._available_bytes_lock:
            total = self.available_bytes + existing_allocation
            logging.debug("FreeSpaceMonitor - op needs %s, %s available (%s of which is being overwritten)" % \
                (GLib.format_size(size), GLib.format_size(total), GLib.format_size(existing_allocation)))
            return size < total

    def start(self):
        self.save_folder = Gio.File.new_for_path(prefs.get_save_path())
        self.min_free = prefs.get_min_free_space()
        logging.debug("FreeSpaceMonitor start (monitoring %s,  keeping a %s reserve" % (self.save_folder.get_path(), GLib.format_size(self.min_free * MB_TO_B)))

        if self._monitor_thread is None:
            self._monitor_thread = threading.Thread(target=self._monitor_thread_func, args=(self._cancellable,), name="FreeSpaceMonitor-thread")
            self._monitor_thread.start()

        self._monitor_enable.set()

    def pause(self):
        logging.debug("FreeSpaceMonitor pause")
        self._monitor_enable.clear()

    def shutdown(self):
        logging.debug("FreeSpaceMonitor shutdown")
        self._cancellable.cancel()
        self._monitor_enable.set()
        if self._monitor_thread is not None:
            self._monitor_thread.join(5)

    def _sleep(self):
        duration = 30.0

        for level in self.poll_levels:
            if self.available_bytes <= level[0]:
                duration = level[1]
                break
        logging.debug("FreeSpaceMonitor - sleep duration %.2fs" % duration)
        time.sleep(duration)

    def _monitor_thread_func(self, cancellable):
        while not cancellable.is_cancelled():
            self._refresh_available(cancellable)
            self._sleep()
            self._monitor_enable.wait()
            continue

    def _refresh_available(self, cancellable):
        available_bytes = 0
        try:
            info = self.save_folder.query_filesystem_info(Gio.FILE_ATTRIBUTE_FILESYSTEM_FREE, cancellable)
            available_bytes = info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_FILESYSTEM_FREE)
            if available_bytes == 0:
                raise GLib.Error(code=GLib.FileError.FAILED, message="Save directory's filesystem doesn't report useful available space info.")
        except GLib.Error as e:
            logging.critical("Could not query available disk space for the save directory, allowing all transfers: %s" % e.message)
            available_bytes = 0

        with self._available_bytes_lock:
            adjusted = available_bytes - (self.min_free * 1024 * 1024)
            logging.debug("FreeSpaceMonitor - %d available (%s)" % (adjusted, GLib.format_size(adjusted if adjusted >= 0 else 0)))
            self.available_bytes = adjusted if adjusted > 0 else 0
            if self.available_bytes == 0:
                self._notify_low_space()

    def _notify_low_space(self):
        self.pause()
        GLib.idle_add(priority=GLib.PRIORITY_HIGH, function=self._notify_idle_cb)

    def _notify_idle_cb(self):
        logging.critical("FreeSpaceMonitor - out of space!")
        self.emit("low-space")

def files_exist(base_names):
    for name in base_names:
        path = os.path.join(prefs.get_save_path(), name)
        logging.debug("(server side) Checking if file or folder %s already exists." % (path,))
        file = Gio.File.new_for_path(path)
        if file.query_exists(None):
            return True

    return False

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
                                 website="https://github.com/linuxmint/warpinator",
                                 version=config.VERSION,
                                 license_type=Gtk.License.GPL_3_0)

        dialog.run()
        dialog.destroy()

#### Logging
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

log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(WarpLogFormatter())
logging.root.addHandler(log_handler)

try:
    debug = os.environ["WARPINATOR_DEBUG"]
except:
    debug = False

if debug:
    logging.root.setLevel(logging.DEBUG)
else:
    logging.root.setLevel(logging.INFO)

#### /Logging

recent_manager = Gtk.RecentManager()

def add_to_recents_if_single_selection(uri_list):
    if not os.access(GLib.get_user_data_dir(), os.W_OK):
        logging.debug("Recents storage not writable")
        return

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

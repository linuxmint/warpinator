import os
import threading
import xmlrpc
import queue
import gettext
import time

from gi.repository import GLib, Gio

import util
import prefs

_ = gettext.gettext

FILE_INFOS = "standard::size,standard::name,standard::type,standard::symlink-target"

class Aborted(Exception):
    pass

class NeverStarted(Exception):
    pass

def relpath_from_uris(child_uri, base_uri):
    child_uri = GLib.uri_unescape_string(child_uri)
    base_uri = GLib.uri_unescape_string(base_uri)

    if child_uri.startswith(base_uri):
        return child_uri.replace(base_uri + "/", "")
    else:
        return None

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

class QueuedFile:
    def __init__(self, uri, rel_uri, size, folder, symlink_target_path):
        self.uri = uri
        self.relative_uri = rel_uri
        self.size = size
        self.is_folder = folder
        self.symlink_target_path = symlink_target_path

class TransferRequest:
    def __init__(self):
        # (absolute uri, relative uri) tuples
        self.files = []
        self.transfer_file_to_size_map = {}

        self.transfer_size = 0
        self.transfer_count = 0

    def add_file(self, basename, uri, base_uri, info):
        file_type = info.get_file_type()

        is_dir = is_link = False
        size = info.get_size()
        relative_symlink_path = None

        if file_type == Gio.FileType.DIRECTORY:
            is_dir = True
            size = 0
        elif file_type == Gio.FileType.SYMBOLIC_LINK:
            symlink_target = info.get_symlink_target()
            if symlink_target:
                if symlink_target[0] == "/":
                    symlink_file = Gio.File.new_for_path(symlink_target)
                    relative_symlink_path = relpath_from_uris(symlink_file.get_uri(), base_uri)
                    if not relative_symlink_path:
                        relative_symlink_path = symlink_target
                else:
                    relative_symlink_path = symlink_target
            size = 0

        if base_uri:
            relative_uri = relpath_from_uris(uri, base_uri)
        else:
            relative_uri = basename

        qf = QueuedFile(uri, relative_uri, size, is_dir, relative_symlink_path)
        self.files.append(qf)

        self.transfer_file_to_size_map[uri] = size
        self.transfer_size += size
        self.transfer_count += 1

class FileSender:
    CHUNK_UNIT = 1024 * 1024 # Starting at 1 mb
    CHUNK_MAX = 10 * 1024 * 1024 # Increase by 1mb each iteration to max 10mb (this resets for every file)
    PROGRESS_INTERVAL = 2 * 1000 * 1000

    def __init__(self, my_name, peer_name, peer_nick, peer_proxy, progress_callback):
        self.my_name = my_name
        self.peer_proxy = peer_proxy
        self.peer_name = peer_name
        self.peer_nick = peer_nick
        self.progress_callback = progress_callback

        self.cancellable = None
        self.queue = queue.Queue()
        self.send_thread = threading.Thread(target=self._send_file_thread)
        self.send_thread.start()

        self.start_time = 0
        self.speed_calc_start_bytes = 0

        self.total_transfer_size = 0
        self.current_transfer_size = 0
        self.file_to_size_map = {}
        self.interval_start_time = 0

    def send_files(self, uri_list):
        self._process_files(uri_list)

    @util._async
    def _process_files(self, uri_list):
        # expanded uri list will be (full_uri, relative_uri)
        request = TransferRequest()
        top_dir_parent_uri = None
        top_dir_basenames = []

        def process_folder(folder_uri, top_dir):
            folder_file = Gio.File.new_for_uri(folder_uri)

            enumerator = folder_file.enumerate_children(FILE_INFOS, Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None)
            info = enumerator.next_file(None)

            while info:
                child = enumerator.get_child(info)
                child_uri = child.get_uri()
                child_basename = child.get_basename()

                file_type = info.get_file_type()

                if file_type == Gio.FileType.DIRECTORY:
                    if uri not in self.file_to_size_map.keys():
                        request.add_file(child_basename, child_uri, top_dir, info)
                    process_folder(child_uri, top_dir)
                else:
                    if child_uri not in self.file_to_size_map.keys():
                        size = info.get_size()
                        request.add_file(child_basename, child_uri, top_dir, info)

                info = enumerator.next_file(None)

        for uri in uri_list:
            file = Gio.File.new_for_uri(uri)
            top_dir_basenames.append(file.get_basename())

            info = file.query_info(FILE_INFOS, Gio.FileQueryInfoFlags.NONE, None)
            basename = file.get_basename()

            if info and info.get_file_type() == Gio.FileType.DIRECTORY:
                top_dir = file.get_parent().get_uri()
                if uri not in self.file_to_size_map.keys():
                    request.add_file(basename, uri, None, info)
                process_folder(uri, top_dir)
                continue
            else:
                size = info.get_size()
                if uri not in self.file_to_size_map.keys():
                    request.add_file(basename, uri, None, info)

        if request.transfer_count == 0:
            #what?
            exit()

        if prefs.prevent_overwriting:
            if self.peer_proxy.files_exist(top_dir_basenames):
                print("can't overwrite!!!")
                exit()

        permission = False

        if self.peer_proxy.check_needs_permission():
            #ask_permission
            self._update_progress(sender_awaiting_approval=True, count=request.transfer_count)
            stamp = str(GLib.get_monotonic_time())
            while True:
                response = self.peer_proxy.get_permission(self.my_name,
                                                          self.peer_nick,
                                                          request.transfer_size,
                                                          request.transfer_count,
                                                          stamp) # this is stupid

                if response == util.TRANSFER_REQUEST_PENDING:
                    time.sleep(1)
                    continue
                else:
                    permission = response == util.TRANSFER_REQUEST_GRANTED
                    break
        else:
            permission = True

        if permission:
            new_total = 0
            self.file_to_size_map.update(request.transfer_file_to_size_map)

            for size in self.file_to_size_map.values():
                new_total += size

            self.total_transfer_size = new_total

            self._update_progress(transfer_starting=True)

            print("Starting send: %d files (%s)" % (request.transfer_count, GLib.format_size(request.transfer_size)))
            GLib.idle_add(self.queue_files, request, priority=GLib.PRIORITY_DEFAULT)
        else:
            self._update_progress(transfer_cancelled=True)
        exit()

    def queue_files(self, request):
        self.start_time = GLib.get_monotonic_time()
        self.interval_start_time = self.start_time
        self.current_transfer_size = 0

        for queued_file in request.files:
            self.queue.put(queued_file)

    def _send_file_thread(self):
        while True:
            queued_file = self.queue.get()

            if queued_file is None:
                break

            self._real_send(queued_file)
            self.queue.task_done()

            if self.queue.empty():
                self.current_transfer_size = 0
                self._update_progress(finished=True)

    def _real_send(self, queued_file):
        serial = 0

        try:
            self.cancellable = Gio.Cancellable()

            if queued_file.is_folder or queued_file.symlink_target_path:
                if not self.peer_proxy.receive(self.my_name,
                                               queued_file.relative_uri,
                                               queued_file.is_folder,
                                               queued_file.symlink_target_path,
                                               serial,
                                               None):
                    raise Aborted(_("Something went wrong with transfer of %s") % file.get_uri())
            else:
                gfile = Gio.File.new_for_uri(queued_file.uri)
                stream = gfile.read(self.cancellable)

                if self.cancellable.is_cancelled():
                    stream.close()
                    raise Aborted(_("Cancelled while opening file"));

                chunk_size = self.CHUNK_UNIT

                while True:
                    try:
                        bytes = stream.read_bytes(chunk_size, self.cancellable)
                    except GLib.Error as e:
                        if self.cancellable.is_cancelled():
                            stream.close()
                            raise Aborted("Cancelled while reading file contents");

                    serial += 1

                    if not self.peer_proxy.receive(self.my_name,
                                                   queued_file.relative_uri,
                                                   False,
                                                   None,
                                                   serial,
                                                   xmlrpc.client.Binary(bytes.get_data())):
                        raise Aborted(_("Something went wrong with the transfer of %s") % queued_file.uri)

                    if (bytes.get_size() > 0):
                        self.current_transfer_size += bytes.get_size()
                        self._update_progress(finished=False)
                    else:
                        stream.close()
                        break

                    if chunk_size < self.CHUNK_MAX:
                        chunk_size += self.CHUNK_UNIT

            del self.file_to_size_map[queued_file.uri]
        except Aborted as e:
            print("An error occurred during the transfer (our side): %s" % str(e))
            self.peer_proxy.abort_transfer(self.my_name)
            self._update_progress(finished=True)

            self.clear_queue()
            self.send_abort_ml(e)

    def _update_progress(self, finished=False, sender_awaiting_approval=False, transfer_starting=False, transfer_cancelled=False, count=0):
        if finished:
            self.peer_proxy.update_progress(self.my_name, 0, "", "", finished)
            GLib.idle_add(self.progress_callback,
                          util.ProgressCallbackInfo(finished=True),
                          priority=GLib.PRIORITY_DEFAULT)

            print("finished: %s" % format_time_span((GLib.get_monotonic_time() - self.start_time) / 1000/1000))
            return

        if sender_awaiting_approval:
            GLib.idle_add(self.progress_callback,
                          util.ProgressCallbackInfo(sender_awaiting_approval=True, count=count),
                          priority=GLib.PRIORITY_DEFAULT)
            return

        if transfer_starting:
            GLib.idle_add(self.progress_callback,
                          util.ProgressCallbackInfo(transfer_starting=True),
                          priority=GLib.PRIORITY_DEFAULT)
            return

        if transfer_cancelled:
            GLib.idle_add(self.progress_callback,
                          util.ProgressCallbackInfo(transfer_cancelled=True),
                          priority=GLib.PRIORITY_DEFAULT)
            return

        progress = self.current_transfer_size / self.total_transfer_size

        cur_time = GLib.get_monotonic_time()
        total_elapsed = cur_time - self.start_time

        if (cur_time - self.interval_start_time) > self.PROGRESS_INTERVAL:
            self.interval_start_time = cur_time
            bytes_per_micro = self.current_transfer_size / total_elapsed
            bytes_per_sec = int(bytes_per_micro * 1000 * 1000)

            speed_str = _("%s/s") % GLib.format_size(bytes_per_sec)

            bytes_left = self.total_transfer_size - self.current_transfer_size
            time_left_sec = bytes_left / bytes_per_sec
            time_left_str = format_time_span(time_left_sec)

            self.peer_proxy.update_progress(self.my_name, progress, speed_str, time_left_str, finished)
            GLib.idle_add(self.progress_callback,
                          util.ProgressCallbackInfo(progress=progress, speed=speed_str, time_left=time_left_str),
                          priority=GLib.PRIORITY_DEFAULT)

    @util._idle
    def send_abort_ml(self, error):
        #what else - notify?
        print("Transfer cancelled:", str(error))
        return False

    def clear_queue(self):
        with self.queue.mutex:
            self.queue.queue.clear()

    def stop(self):
        if self.cancellable:
            self.cancellable.cancel()
        self.queue.put(None)
        self.send_thread.join()

class Chunk():
    def __init__(self, basename, folder, symlink_target_path, serial, data):
        self.basename = basename
        self.folder = folder
        self.symlink_target_path = symlink_target_path
        self.serial = serial
        self.data = data

class OpenFile():
    def __init__(self, path, cancellable):
        self.path = path
        self.file = Gio.File.new_for_path(self.path)
        self.stream = self.file.create(Gio.FileCreateFlags.NONE,
                                       cancellable)
        self.serial = 0

class FileReceiver:
    def __init__(self, save_path):
        self.save_path = save_path
        self.cancellable = None

        # Packets from any source
        self.request_queue = queue.Queue(maxsize=1)

        # OpenFiles
        self.open_files = {}

        self.error_state = False

        self.thread = threading.Thread(target=self._receive_file_thread)
        self.thread.start()

    def receive(self, basename, folder, symlink_target, serial, data=None):
        if self.error_state:
            return util.TRANSFER_RECEIVE_STATUS_ERROR

        chunk = Chunk(basename, folder, symlink_target, serial, data)
        self.request_queue.put(chunk)

        return util.TRANSFER_RECEIVE_STATUS_OK

    def _receive_file_thread(self):
        while True:
            chunk = self.request_queue.get()
            if chunk == None:
                break

            self._real_receive(chunk)

            self.request_queue.task_done()

    def _real_receive(self, chunk):
        self.cancellable = Gio.Cancellable()

        path = os.path.join(self.save_path, chunk.basename)
        # folder
        if chunk.folder:
            try:
                os.makedirs(path, exist_ok=False)
            except Exception as e:
                print("Could not create folder %s: %s" % (path, str(e)))
                self.error_state = True
            return
        elif chunk.symlink_target_path:
            absolute_symlink_target_path = os.path.join(self.save_path, chunk.symlink_target_path)

            try:
                file = Gio.File.new_for_path(path)
                file.make_symbolic_link(absolute_symlink_target_path, None)
            except GLib.Error as e:
                print("Could not create symbolic link %s: %s" % (path, e.message))
                self.error_state = True
            return
        # not folder
        try:
            open_file =self.open_files[path]
        except KeyError as e:
            try:
                open_file = self.open_files[path] = OpenFile(path, self.cancellable)
            except GLib.Error as e:
                print("Could not open file %s for writing: %s" % (path, e.message))
                self.error_state = True
                return

        if len(chunk.data.data) > 0:
            try:
                open_file.stream.write(chunk.data.data, self.cancellable)
                open_file.serial += 1
            except GLib.Error as e:
                self.error_state = True
                print("Could not write data to file %s: %s" % (path, e.message))
                try:
                    open_file.stream.close()
                    open_file.file.delete(self.cancellable)
                except GLib.Error as e:
                    print("Could not abort after write error: %s" % e.message)
                return
        else:
            try:
                open_file.stream.close()
            except GLib.Error as e:
                print("Could not close file %s from writing: %s" % (path, e.message))
                self.error_state = True

            del self.open_files[path]

    def stop(self):
        if self.cancellable:
            self.cancellable.cancel()
        self.request_queue.put(None)
        self.thread.join()

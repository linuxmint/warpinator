import os
import threading
import xmlrpc
import queue
import gettext

from gi.repository import GLib, Gio

import util
import prefs

_ = gettext.gettext

FILE_INFOS = "standard::size,standard::name,standard::type"

class Aborted(Exception):
    pass

class NeverStarted(Exception):
    pass

def relpath_from_uris(child_uri, base_uri):
    child_uri = GLib.uri_unescape_string(child_uri)
    base_uri = GLib.uri_unescape_string(base_uri)

    ret = child_uri.replace(base_uri + "/", "")
    return ret

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

    return getttext.ngettext("approximately %d hour", "approximately %d hours", hours) % hours

class FileSender:
    CHUNK_SIZE = 1024 * 1024 + 16
    SPEED_CALC_SPAN = 4 * 1000 * 1000

    def __init__(self, name, proxy, progress_callback):
        self.proxy = proxy
        self.name = name
        self.progress_callback = progress_callback

        self.cancellable = None
        self.queue = queue.Queue()
        self.send_thread = threading.Thread(target=self._send_file_thread)
        self.send_thread.start()

        self.speed_calc_start_time = 0
        self.speed_calc_start_bytes = 0

        self.total_transfer_size = 0
        self.current_transfer_size = 0
        self.file_to_size_map = {}

    def send_files(self, uri_list):
        self._process_files(uri_list)

    @util._async
    def _process_files(self, uri_list):
        # expanded uri list will be (full_uri, relative_uri)
        expanded_uri_list = []

        def process_folder(top_dir):
            top_dir_parent_uri = top_dir.get_parent().get_uri()

            def process_subfolders_recursively(rec_dir):
                rec_enumerator = rec_dir.enumerate_children(FILE_INFOS, Gio.FileQueryInfoFlags.NONE, None)
                rec_info = rec_enumerator.next_file(None)

                while rec_info:
                    rec_child = rec_enumerator.get_child(rec_info)
                    rec_child_uri = rec_child.get_uri()

                    if rec_info.get_file_type() == Gio.FileType.DIRECTORY:
                        sub_pair = (rec_child_uri, relpath_from_uris(rec_child_uri, top_dir_parent_uri))
                        expanded_uri_list.append(sub_pair)

                        process_subfolders_recursively(rec_child)
                    else:
                        size = rec_info.get_size()
                        self.file_to_size_map[rec_child_uri] = size
                        rec_pair = (rec_child_uri, relpath_from_uris(rec_child_uri, top_dir_parent_uri))
                        expanded_uri_list.append(rec_pair)

                    rec_info = rec_enumerator.next_file(None)

            enumerator = top_dir.enumerate_children(FILE_INFOS, Gio.FileQueryInfoFlags.NONE, None)
            info = enumerator.next_file(None)

            while info:
                child = enumerator.get_child(info)
                child_uri = child.get_uri()

                if info.get_file_type() == Gio.FileType.DIRECTORY:
                    sub_pair = (child_uri, relpath_from_uris(child_uri, top_dir_parent_uri))
                    expanded_uri_list.append(sub_pair)

                    process_subfolders_recursively(child)
                else:
                    size = info.get_size()
                    self.file_to_size_map[child_uri] = size
                    sub_pair = (child_uri, relpath_from_uris(child_uri, top_dir_parent_uri))
                    expanded_uri_list.append(sub_pair)

                info = enumerator.next_file(None)

        for uri in uri_list:
            file = Gio.File.new_for_uri(uri)
            info = file.query_info(FILE_INFOS, Gio.FileQueryInfoFlags.NONE, None)

            if info and info.get_file_type() == Gio.FileType.DIRECTORY:
                expanded_uri_list.append((uri, None))
                process_folder(file)
                continue
            else:
                size = info.get_size()
                self.file_to_size_map[uri] = size
                expanded_uri_list.append((uri, None))

        new_total = 0
        for size in self.file_to_size_map.values():
            new_total += size

        self.total_transfer_size = new_total

        GLib.idle_add(self.queue_files, expanded_uri_list)
        exit()

    def queue_files(self, uri_list):
        self.speed_calc_start_time = GLib.get_monotonic_time()
        self.speed_calc_start_bytes = self.current_transfer_size

        for pair in uri_list:
            self.queue.put(pair)

    def _send_file_thread(self):
        while True:
            pair = self.queue.get()
            if pair is None:
                break
            self._real_send(pair)
            self.queue.task_done()
            if self.queue.empty():
                self.current_transfer_size = 0
                self._update_progress(True)

    def _real_send(self, pair):
        uri, relative_uri = pair

        file = Gio.File.new_for_uri(uri)
        dest_path = relative_uri if relative_uri else file.get_basename()

        self.cancellable = Gio.Cancellable()

        try:
            info = file.query_info(FILE_INFOS, Gio.FileQueryInfoFlags.NONE, None)

            if info and info.get_file_type() == Gio.FileType.DIRECTORY:
                response = self.proxy.receive(self.name,
                                              dest_path,
                                              util.TRANSFER_FOLDER,
                                              None)
                if response == util.RESPONSE_EXISTS:
                    raise NeverStarted("Folder %s exists at remote location" % relative_uri)

                return
            else:
                stream = file.read(self.cancellable)

                if self.cancellable.is_cancelled():
                    stream.close()
                    raise NeverStarted("Cancelled while opening file");

                response = self.proxy.receive(self.name,
                                              dest_path,
                                              util.TRANSFER_START,
                                              None)

                if response == util.RESPONSE_EXISTS:
                    raise NeverStarted("File %s exists at remote location" % relative_uri)

            while True:
                bytes = stream.read_bytes(self.CHUNK_SIZE, self.cancellable)

                if self.cancellable.is_cancelled():
                    stream.close()
                    raise Aborted("Cancelled while reading file contents");

                if (bytes.get_size() > 0):
                    self.proxy.receive(self.name,
                                       dest_path,
                                       util.TRANSFER_DATA,
                                       xmlrpc.client.Binary(bytes.get_data()))
                    self.current_transfer_size += bytes.get_size()

                    self._update_progress(False)
                else:
                    break

            self.proxy.receive(self.name,
                               dest_path,
                               util.TRANSFER_COMPLETE,
                               None)

            del self.file_to_size_map[file.get_uri()]

            stream.close()
        except Aborted as e:
            self.proxy.receive(self.name,
                               dest_path,
                               util.TRANSFER_ABORT,
                               None)
        except NeverStarted as e:
            print("File %s already exists, skipping: %s" % (file.get_path(), str(e)))

    def _update_progress(self, finished):
        if finished:
            GLib.idle_add(self.progress_callback, 0, "", "", finished)

        progress =self.current_transfer_size / self.total_transfer_size

        cur_time = GLib.get_monotonic_time()
        elapsed = cur_time - self.speed_calc_start_time

        if elapsed > self.SPEED_CALC_SPAN:
            span_bytes = self.current_transfer_size - self.speed_calc_start_bytes
            bytes_per_micro = span_bytes / elapsed
            bytes_per_sec = int(bytes_per_micro * 1000 * 1000)

            speed_str = _("%s/s") % GLib.format_size(bytes_per_sec)

            bytes_left = self.total_transfer_size - self.current_transfer_size
            time_left_sec = bytes_left / bytes_per_sec
            time_left_str = format_time_span(time_left_sec)

            self.speed_calc_start_bytes = self.current_transfer_size
            self.speed_calc_start_time = cur_time

            GLib.idle_add(self.progress_callback, progress, speed_str, time_left_str, finished)
        else:
            GLib.idle_add(self.progress_callback, progress, None, None, finished)

    def stop(self):
        if self.cancellable:
            self.cancellable.cancel()
        self.queue.put(None)
        self.send_thread.join()







class FileReceiver:
    CHUNK_SIZE = 1024 * 1024
    def __init__(self, save_path):
        self.save_path = save_path
        self.cancellable = None

        # Packets from any source
        self.request_queue = queue.Queue(maxsize=100)
        self.open_files = {}

        self.thread = threading.Thread(target=self._receive_file_thread)
        self.thread.start()

    def receive(self, basename, status, data=None):

        path = os.path.join(self.save_path, basename)

        if status in (util.TRANSFER_DATA, util.TRANSFER_COMPLETE, util.TRANSFER_ABORT) and not self.open_files[path]:
            return util.RESPONSE_ERROR

        self.request_queue.put((basename, status, data))

        return util.RESPONSE_OK

    def _receive_file_thread(self):
        while True:
            packet = self.request_queue.get()
            if packet == None:
                break

            self._real_receive(packet)

            self.request_queue.task_done()

    def _real_receive(self, packet):
        (basename, status, data) = packet
        self.cancellable = Gio.Cancellable()

        path = os.path.join(self.save_path, basename)

        if status == util.TRANSFER_FOLDER:
            new_file = Gio.File.new_for_path(path)

            try:
                os.makedirs(path, exist_ok=False)
            except GLib.Error as e:
                print("Could not create folder: %s" % (path, e.message))

            return

        if status == util.TRANSFER_START:
            new_file = Gio.File.new_for_path(path)

            try:
                os.makedirs(new_file.get_parent().get_path(), exist_ok=True)
                self.open_files[path] = new_file.create(Gio.FileCreateFlags.NONE,
                                                        self.cancellable)
            except GLib.Error as e:
                print("Could not open file %s for writing: %s" % (path, e.message))

            if self.cancellable.is_cancelled():
                del self.open_files[path]

            return

        if status == util.TRANSFER_COMPLETE:
            try:
                self.open_files[path].close(self.cancellable)
            except GLib.Error as e:
                print("Could not close file %s from writing: %s" % (path, e.message))

            del self.open_files[path]
            return

        if status == util.TRANSFER_ABORT:
            aborted_file = Gio.File.new_for_path(path)

            try:
                self.open_files[path].close(self.cancellable)
                aborted_file.delete(self.cancellable)
            except GLib.Error as e:
                print("Could not cleanly abort file %s from writing: %s" % (path, e.message))

            del self.open_files[path]
            return

        if status == util.TRANSFER_DATA:
            stream = self.open_files[path]

            try:
                stream.write(data.data, self.cancellable)
            except GLib.Error as e:
                print("Could not write data to file %s: %s" % (path, e.message))
                try:
                    stream.close()
                    aborted_file = Gio.File.new_for_path(path)
                    aborted_file.delete(self.cancellable)
                except GLib.Error as e:
                    print("Could not abort after write error: %s" % e.message)

            return

    def stop(self):
        if self.cancellable:
            self.cancellable.cancel()
        self.request_queue.put(None)
        self.thread.join()

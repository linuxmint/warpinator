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

FILE_INFOS = "standard::size,standard::allocated-size,standard::name,standard::type,standard::symlink-target"

class Aborted(Exception):
    pass

class Cancelled(Exception):
    pass

class NeverStartedSending(Exception):
    pass

# This represents a file to be transferred (this is used by the sender)
class QueuedFile:
    def __init__(self, uri, rel_uri, size, folder, symlink_target_path):
        self.uri = uri
        self.relative_uri = rel_uri
        self.size = size
        self.is_folder = folder
        self.symlink_target_path = symlink_target_path

# This represents the entirety of a single transfer 'task' - it contains info
# on the task - size, file count, etc... as well as a list of QueuedFiles that make
# up the task.
class TransferRequest:
    def __init__(self):
        # (absolute uri, relative uri) tuples
        self.files = []
        self.transfer_file_to_size_map = {}

        self.transfer_size = 0
        self.transfer_count = 0

        self.stamp = 0

    def add_file(self, basename, uri, base_uri, info):
        file_type = info.get_file_type()

        is_dir = is_link = False

        # Normal files usually take more disk space than their actual size, so we want that
        # for checking free disk space on the target computer.  However, sparse files can
        # report a smaller allocated size on disk than their 'actual' size. For now we can
        # only copy files in their full state, and at the other end they'll no longer be
        # sparse, so we use the largest of the two sizes for our purposes.
        alloc_size = info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_STANDARD_ALLOCATED_SIZE)
        file_size = info.get_size()
        size = file_size if file_size > alloc_size else alloc_size

        relative_symlink_path = None

        if file_type == Gio.FileType.DIRECTORY:
            is_dir = True
            size = 0
        elif file_type == Gio.FileType.SYMBOLIC_LINK:
            symlink_target = info.get_symlink_target()
            if symlink_target:
                if symlink_target[0] == "/":
                    symlink_file = Gio.File.new_for_path(symlink_target)
                    relative_symlink_path = util.relpath_from_uris(symlink_file.get_uri(), base_uri)
                    if not relative_symlink_path:
                        relative_symlink_path = symlink_target
                else:
                    relative_symlink_path = symlink_target
            size = 0

        if base_uri:
            relative_uri = util.relpath_from_uris(uri, base_uri)
        else:
            relative_uri = basename

        qf = QueuedFile(uri, relative_uri, size, is_dir, relative_symlink_path)
        self.files.append(qf)

        self.transfer_file_to_size_map[uri] = size
        self.transfer_size += size
        self.transfer_count += 1

# This handles sending files, there is one for every proxy we discover on the network
# It accepts a list of files from the ProxyItem, counts, gets their size, calculates their
# relative paths, then 1) Checks with the remote to see if they exist already, 2) Asks permission to send,
# and 3) Actually send the files and report progress to both its owner (The local ProxyItem) and the remote
# server, whom the ProxyItem represents.
class FileSender:
    CHUNK_UNIT = 1024 * 1024 # Starting at 1 mb
    CHUNK_MAX = 20 * 1024 * 1024 # Increase by 1mb each iteration to max 10mb (this resets for every file)
    PROGRESS_INTERVAL = 4 * 1000 * 1000 # How often to report progress
    MAX_RETRIES = 3 # How many re-sends if a chunk fails during transfer before aborting the whole thing

    def __init__(self, app_name, proxy_name, proxy_nick, proxy, progress_callback):
        self.app_name = app_name
        self.proxy = proxy
        self.proxy_name = proxy_name
        self.proxy_nick = proxy_nick

        # This is ProxyItem:send_progress_callback, used to update the local widget's state.
        self.progress_callback = progress_callback

        self.cancellable = None
        self.queue = queue.Queue()
        self.send_thread = threading.Thread(target=self._send_file_thread)
        self.send_thread.start()

        self.start_time = 0

        self.total_transfer_size = 0
        self.current_transfer_size = 0
        self.interval_start_time = 0

        # All files are added here, and removed as their send is completed. We keep track in this manner,
        # so if more files are added while there's already a transfer in process, we can have a new, accurate
        # total size for the transfer (so our progress can adjust accordingly).
        self.file_to_size_map = {}
        self.current_send_request = None

    def get_active(self):
        return not (self.current_send_request == None and self.queue.empty())

    # Entry point from the ProxyItem class - the list of uri's dragged onto the widget are sent here
    def send_files(self, uri_list):
        self._process_files(uri_list)

    @util._async
    def cancel_send_request(self):
        # handle return?
        with self.proxy.lock:
            self.proxy.abort_request(self.app_name, str(self.current_send_request.stamp))
        self.current_send_request = None

    # This function creates a new TransferRequest, and begins crawling the files and adding them to the list.
    # It will then communicate with the server, checking for existing files, as well as permission to send.
    @util._async
    def _process_files(self, uri_list):
        self.current_send_request = request = TransferRequest()

        # These are the first-level base names (no path, just the filename) that we'll send to the server
        # to check for pre-existence.  We know that if these files/folders don't exist, none of their children
        # will.  This is a bit simple, but until we need more, it's fine.
        top_dir_basenames = []

        # Recursive function for processing folders and their contents.
        def process_folder(folder_uri, top_dir):
            folder_file = Gio.File.new_for_uri(folder_uri)

            try:
                enumerator = folder_file.enumerate_children(FILE_INFOS, Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None)
                info = enumerator.next_file(None)
            except GLib.Error as e:
                raise NeverStartedSending(e.message)

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

                try:
                    info = enumerator.next_file(None)
                except GLib.Error as e:
                    raise NeverStartedSending(e.message)

        try:
            # Process the initial list.
            for uri in uri_list:
                file = Gio.File.new_for_uri(uri)
                top_dir_basenames.append(file.get_basename())

                try:
                    info = file.query_info(FILE_INFOS, Gio.FileQueryInfoFlags.NONE, None)
                except GLib.Error as e:
                    raise NeverStartedSending(e.message)

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
        except NeverStartedSending as e:
            self._update_progress(util.ProgressCallbackInfo(transfer_cancelled=True, error=e))
            exit()

        with self.proxy.lock:
            if self.proxy.prevent_overwriting() and self.proxy.files_exist(top_dir_basenames):
                self._update_progress(util.ProgressCallbackInfo(transfer_exists=True, count=request.transfer_count))
                exit()

        permission = False

        with self.proxy.lock:
            need = self.proxy.permission_needed()

        if need:
            self._update_progress(util.ProgressCallbackInfo(sender_awaiting_approval=True, count=request.transfer_count))
            request.stamp = GLib.get_monotonic_time()

            while True:
                with self.proxy.lock:
                    response = self.proxy.get_permission(self.app_name,
                                                         self.proxy_nick,
                                                         str(request.transfer_size), # XML RPC can't handle longs
                                                         str(request.transfer_count),
                                                         str(request.stamp))

                if response == util.TRANSFER_REQUEST_PENDING:
                    time.sleep(1)
                    continue
                elif response == util.TRANSFER_REQUEST_CANCELLED:
                    break
                elif response == util.TRANSFER_REQUEST_REFUSED:
                    self._update_progress(util.ProgressCallbackInfo(transfer_refused=True))
                    break
                elif response == util.TRANSFER_REQUEST_DISKFULL:
                    self._update_progress(util.ProgressCallbackInfo(transfer_diskfull=True, size=request.transfer_size))
                    break
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

            self._update_progress(util.ProgressCallbackInfo(transfer_starting=True))

            print("Starting send: %d files (%s)" % (request.transfer_count, GLib.format_size(request.transfer_size)))
            GLib.idle_add(self._queue_files, request, priority=GLib.PRIORITY_DEFAULT)
        else:
            self._update_progress(util.ProgressCallbackInfo(transfer_cancelled=True))
        exit()

    # Ready to start the transfer, all approved.  Mark down when we start, zero out the transmitted count, and
    # add all the files to the queue.
    def _queue_files(self, request):
        self.start_time = GLib.get_monotonic_time()
        self.interval_start_time = self.start_time
        self.current_transfer_size = 0

        for queued_file in request.files:
            self.queue.put(queued_file)

    # Send the files.
    def _send_file_thread(self):
        while True:
            queued_file = self.queue.get()

            if queued_file is None:
                break

            self._real_send(queued_file)
            self.queue.task_done()

            if self.queue.empty():
                self.current_transfer_size = 0
                self._update_progress(util.ProgressCallbackInfo(finished=True))

    def _real_send(self, queued_file):
        serial = 0

        try:
            self.cancellable = Gio.Cancellable()

            # For folders and symlinks, we don't actually transfer any data, we just
            # send a block that has its filename, relative path, and what type of file it is.
            if queued_file.is_folder or queued_file.symlink_target_path:
                with self.proxy.lock:
                    if not self.proxy.receive(self.app_name,
                                                   queued_file.relative_uri,
                                                   queued_file.is_folder,
                                                   queued_file.symlink_target_path,
                                                   0,
                                                   None):
                        raise Aborted(_("Could not copy symlink or folder: %s") % file.get_uri())
            else:
                # Any other file, we open a stream, and read/transfer in chunks.
                gfile = Gio.File.new_for_uri(queued_file.uri)
                stream = gfile.read(self.cancellable)

                if self.cancellable.is_cancelled():
                    stream.close()
                    raise Cancelled("Cancelled while opening file")

                # Start with a small chunk size.  We increase it by one CHUNK_UNIT each iteration until
                # we've reached our max.
                chunk_size = self.CHUNK_UNIT

                while True:
                    try:
                        bytes = stream.read_bytes(chunk_size, self.cancellable)
                    except GLib.Error as e:
                        if self.cancellable.is_cancelled():
                            stream.close()
                            raise Cancelled("Cancelled while reading file contents")

                    serial += 1

                    if bytes.get_size() > 0:
                        md5 = GLib.compute_checksum_for_bytes(GLib.ChecksumType.MD5, bytes)
                    else:
                        md5 = None

                    retry_count = 0

                    while True:
                        with self.proxy.lock:
                            ret = self.proxy.receive(self.app_name,
                                                     queued_file.relative_uri,
                                                     False,
                                                     None,
                                                     serial,
                                                     md5,
                                                     xmlrpc.client.Binary(bytes.get_data()))
                        if ret == util.TRANSFER_RECEIVE_STATUS_RESEND:
                            if retry_count < self.MAX_RETRIES:
                                retry_count += 1
                                print("Block of data for file %s - serial %d - failed md5, re-sending" % (queued_file.uri, serial))
                                continue
                            else:
                                ret = util.TRANSFER_RECEIVE_STATUS_ERROR
                                break
                        else:
                            break

                    if ret == util.TRANSFER_RECEIVE_STATUS_ERROR:
                        raise Aborted(_("Retry count was exceeded attempting to copy %s") % queued_file.uri)

                    # As long as we read more than 0 bytes we keep repeating.
                    # If we've just read (and sent) 0 bytes, that means the file is done, and the server
                    # knows also, so break and return so we can get another file from the queue.
                    if (bytes.get_size() > 0):
                        self.current_transfer_size += bytes.get_size()
                        self._update_progress(util.ProgressCallbackInfo(finished=False))
                    else:
                        stream.close()
                        break

                    if chunk_size < self.CHUNK_MAX:
                        chunk_size += self.CHUNK_UNIT

            # Remove our size mapping for this file.  If more files are added to the queue while this one
            # is in process, we don't want to include completed files in the speed/time remaining calculations.
            del self.file_to_size_map[queued_file.uri]
        except Aborted as e:
            print("An error occurred during the transfer (sender): %s" % str(e))
            with self.proxy.lock:
                self.proxy.abort_transfer(self.app_name)
            self._update_progress(util.ProgressCallbackInfo(finished=True, error=e))

            self.clear_queue()
            self.send_abort_ml(e)

    # This handles all communication with regard to state changes and progress.  It sends to both the local ProxyItem,
    # as well as the remote server so receive progress can be updated for that user also.
    def _update_progress(self, cb_info):
        if cb_info.finished:
            with self.proxy.lock:
                # Don't send NeverStartedSending errors to the other end.
                if cb_info.error and isinstance(cb_info.error, Aborted):
                    e_str = str(cb_info.error)
                else:
                    e_str = None
                self.proxy.update_progress(self.app_name, 0, "", "", cb_info.finished, e_str)
            GLib.idle_add(self.progress_callback, cb_info, priority=GLib.PRIORITY_DEFAULT)
            print("finished: %s" % util.precise_format_time_span(GLib.get_monotonic_time() - self.start_time))
            return

        if cb_info.is_informational():
            GLib.idle_add(self.progress_callback, cb_info, priority=GLib.PRIORITY_DEFAULT)
            return

        cb_info.progress = self.current_transfer_size / self.total_transfer_size

        cur_time = GLib.get_monotonic_time()
        total_elapsed = cur_time - self.start_time

        if (cur_time - self.interval_start_time) > self.PROGRESS_INTERVAL:
            self.interval_start_time = cur_time
            bytes_per_micro = self.current_transfer_size / total_elapsed
            bytes_per_sec = int(bytes_per_micro * 1000 * 1000)

            bytes_left = self.total_transfer_size - self.current_transfer_size
            time_left_sec = bytes_left / bytes_per_sec

            cb_info.speed = _("%s/s") % GLib.format_size(bytes_per_sec)
            cb_info.time_left = util.format_time_span(time_left_sec)
            with self.proxy.lock:
                self.proxy.update_progress(self.app_name,
                                           cb_info.progress,
                                           cb_info.speed,
                                           cb_info.time_left,
                                           cb_info.finished,
                                           None)

            GLib.idle_add(self.progress_callback, cb_info, priority=GLib.PRIORITY_DEFAULT)

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

# A block of file data received by the server
class Chunk():
    def __init__(self, basename, folder, symlink_target_path, serial, data):
        self.basename = basename
        self.folder = folder

        # This is the path a symlink once pointed to.  If this is not None, that means it's a symlink
        self.symlink_target_path = symlink_target_path

        self.serial = serial
        self.data = data

# This is a file currently being written - there will usually be just one at a time, unless
# more than one remote is sending files to you.
class OpenFile():
    def __init__(self, path, cancellable):
        self.path = path
        self.file = Gio.File.new_for_path(self.path)

        if prefs.prevent_overwriting():
            flags = Gio.FileCreateFlags.NONE
        else:
            flags = Gio.FileCreateFlags.REPLACE_DESTINATION

        self.stream = self.file.replace(None, False, flags, cancellable)
        self.serial = 0

# This handles receiving files, there is just one, attached to the local server.
# It accepts Chunks of data and writes them, or creates folders and symlinks.
class FileReceiver:
    def __init__(self, save_path):
        self.save_path = save_path
        self.cancellable = None

        # Packets from any source
        self.request_queue = queue.Queue(maxsize=1)

        # OpenFiles
        self.open_files = {}

        # The chunks are received here asynchronously. So if an error occurs here,
        # we set a state so our server can respond to senders when they send their
        # next chunk of data.
        self.error_state = False

        self.thread = threading.Thread(target=self._receive_file_thread)
        self.thread.start()

    def receive(self, basename, folder, symlink_target, serial, checksum, data=None):
        if self.error_state:
            self.error_state = False
            return util.TRANSFER_RECEIVE_STATUS_ERROR

        if checksum and GLib.compute_checksum_for_data(GLib.ChecksumType.MD5, data.data) != checksum:
            return util.TRANSFER_RECEIVE_STATUS_RESEND

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

        # Info was for a folder
        if chunk.folder:
            try:
                os.makedirs(path, exist_ok=(not prefs.prevent_overwriting()))
            except Exception as e:
                print("Could not create folder %s: %s" % (path, str(e)))
                self.error_state = True
            return
        elif chunk.symlink_target_path:
            # Info was for a symlink. This path might be relative or absolute.  Likely broken, if it
            # pointed to something outside the tree we're copying.  Do we want to follow symbolic links
            # and transfer the files they point to rather than the links themselves?
            absolute_symlink_target_path = os.path.join(self.save_path, chunk.symlink_target_path)

            try:
                file = Gio.File.new_for_path(path)
                file.make_symbolic_link(absolute_symlink_target_path, None)
            except GLib.Error as e:
                print("Could not create symbolic link %s: %s" % (path, e.message))
                self.error_state = True
            return

        # Normal files
        try:
            open_file =self.open_files[path]
        except KeyError as e:
            try:
                open_file = self.open_files[path] = OpenFile(path, self.cancellable)
            except GLib.Error as e:
                print("Could not open file %s for writing: %s" % (path, e.message))
                self.error_state = True
                return

        # As long as we have data, keep writing.  Receiving 0 length means the file is done
        # and we can close it.
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

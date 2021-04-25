#!/usr/bin/python3

import os
import logging
import stat
import shutil

from gi.repository import GLib, Gio, GObject

import util
from util import FileType
import prefs
import warp_pb2

FILE_INFOS = ",".join([
    "standard::size",
    "standard::allocated-size",
    "standard::name",
    "standard::type",
    "standard::symlink-target",
    "unix::mode"
])

FILE_INFOS_SINGLE_FILE = ",".join([
    "standard::size",
    "standard::allocated-size",
    "standard::name",
    "standard::type",
    "standard::symlink-target",
    "standard::content-type",
    "unix::mode"
])

MODE_MASK = (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

CHUNK_SIZE = 1024 * 1024
PROGRESS_UPDATE_FREQ = 2 * 1000 * 1000

def load_file_in_chunks(path):
    gfile = Gio.File.new_for_path(path)

    try:
        stream = gfile.read(None)
    except GLib.Error:
        return

    while True:
        bytes = stream.read_bytes(CHUNK_SIZE, None)
        if bytes.get_size() == 0:
            break

        response = warp_pb2.RemoteMachineAvatar(avatar_chunk=bytes.get_data())
        yield response

    stream.close()

def make_symbolic_link(op, path, target):
    tmppath = os.path.join(os.path.dirname(path), "%s-%d-%d.tmp" % (op.sender, op.start_time, GLib.get_monotonic_time()))
    tmpfile = Gio.File.new_for_path(tmppath)

    tmpfile.make_symbolic_link(target, None)
    os.replace(tmpfile.get_path(), path)

# This represents a file to be transferred (this is used by the sender)
class File:
    def __init__(self, uri, basename, rel_path, size, file_type, symlink_target=None, file_mode=0):
        self.uri = uri
        self.basename = basename
        self.relative_path = rel_path
        self.size = size
        self.file_type = file_type
        self.symlink_target = symlink_target
        self.file_mode = file_mode

class FileSender(GObject.Object):
    def __init__(self, op, timestamp, cancellable):
        super(FileSender, self).__init__()
        self.op = op
        self.timestamp = timestamp
        self.cancellable = cancellable

        self.error = None

    def read_chunks(self):
        for file in self.op.resolved_files:
            if self.cancellable.is_set():
                return # StopIteration as different behaviors between 3.5 and 3.7, this works as well.

            if file.file_type == FileType.DIRECTORY:
                yield warp_pb2.FileChunk(relative_path=file.relative_path,
                                         file_type=file.file_type,
                                         file_mode=file.file_mode)
            elif file.file_type == FileType.SYMBOLIC_LINK:
                yield warp_pb2.FileChunk(relative_path=file.relative_path,
                                         file_type=file.file_type,
                                         symlink_target=file.symlink_target,
                                         file_mode=file.file_mode)
            else:
                stream = None

                try:
                    gfile = Gio.File.new_for_uri(file.uri)
                    stream = gfile.read(None)

                    last_size_read = 1

                    while True:
                        if last_size_read == 0:
                            break

                        if self.cancellable.is_set():
                            return

                        b = stream.read_bytes(CHUNK_SIZE, None)
                        last_size_read = b.get_size()
                        self.op.progress_tracker.update_progress(last_size_read)

                        yield warp_pb2.FileChunk(relative_path=file.relative_path,
                                                 file_type=file.file_type,
                                                 chunk=b.get_data(),
                                                 file_mode=file.file_mode)

                    stream.close()
                    continue
                except Exception as e:
                    try:
                        # If we leave an io stream open, it locks the location.  For instance,
                        # if this was a mounted location, we wouldn't be able to terminate until
                        # we closed warp.
                        stream.close()
                    except:
                        pass

                    self.error = e
                    return

        self.op.progress_tracker.finished()


class FileReceiver(GObject.Object):
    def __init__(self, op):
        super(FileReceiver, self).__init__()
        self.save_path = prefs.get_save_path()
        self.op = op
        self.preserve_perms = prefs.preserve_permissions() and util.save_folder_is_native_fs()

        self.current_path = None
        self.current_gfile = None
        self.current_stream = None
        self.current_mode = 0

        if op.existing:
            for name in op.top_dir_basenames:
                try:
                    path = os.path.join(self.save_path, name)
                    if os.path.isdir(path): # file not found is ok
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                except FileNotFoundError:
                    pass
                except Exception as e:
                    logging.warning("Problem removing existing files.  Transfer may not succeed: %s" % e)

        # We write files top-down.  If we're preserving permissions and we receive
        # a folder in some hierarchy that is not writable, we won't be able to create
        # anything inside it.
        self.folder_permission_change_list = []

    def receive_data(self, s):
        save_path = prefs.get_save_path()

        path = os.path.join(save_path, s.relative_path)
        if path != self.current_path:
            self.close_current_file()
            self.current_path = path
            self.current_mode = s.file_mode

        if s.file_type == FileType.DIRECTORY:
            os.makedirs(path, mode=s.file_mode if (s.file_mode > 0) else 0o777, exist_ok=True)
        elif s.file_type == FileType.SYMBOLIC_LINK:
            make_symbolic_link(self.op, path, s.symlink_target)
        else:
            if not self.current_gfile:
                self.current_gfile = Gio.File.new_for_path(path)

                flags = Gio.FileCreateFlags.REPLACE_DESTINATION
                self.current_stream = self.current_gfile.replace(None, False, flags, None)

            length = len(s.chunk)
            if length == 0:
                return

            self.current_stream.write_bytes(GLib.Bytes(s.chunk), None)
            self.op.progress_tracker.update_progress(length)

    def close_current_file(self):
        if self.current_stream:
            self.current_stream.close()
            self.current_stream = None
            self.current_gfile = None
            if self.preserve_perms and self.current_mode > 0:
                os.chmod(self.current_path, mode=self.current_mode)

    def apply_folder_permissions(self):
        if self.preserve_perms:
            while self.folder_permission_change_list:
                # We added folders from parent->children, this will apply permissions
                # from child to parent.
                os.chmod(*self.folder_permission_change_list.pop())

    def receive_finished(self):
        # We left the last (or only) file open
        self.close_current_file()
        self.apply_folder_permissions()
        self.op.progress_tracker.finished()


def add_file(op, basename, uri, base_uri, info):
    symlink_target = None

    # Normal files usually take more disk space than their actual size, so we want that
    # for checking free disk space on the target computer.  However, sparse files can
    # report a smaller allocated size on disk than their 'actual' size. For now we can
    # only copy files in their full state, and at the other end they'll no longer be
    # sparse, so we use the largest of the two sizes for our purposes.
    alloc_size = info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_STANDARD_ALLOCATED_SIZE)
    file_size = info.get_size()
    size = file_size if file_size > alloc_size else alloc_size

    file_type = info.get_file_type()

    if file_type == FileType.SYMBOLIC_LINK:
        symlink_target = info.get_symlink_target()

    st_mode = info.get_attribute_uint32("unix::mode")
    file_mode = (st_mode & MODE_MASK) if (st_mode > 0) else 0

    if base_uri:
        relative_path = util.relpath_from_uri(uri, base_uri)
    else:
        relative_path = basename

    file = File(uri, basename, relative_path, size, file_type, symlink_target, file_mode)

    op.resolved_files.append(file)
    op.total_size += size
    op.total_count += 1

def gather_file_info(op):
        top_dir_basenames = []
        uri_list = op.uris

        error = None

        if len(uri_list) == 1:
            infos = FILE_INFOS_SINGLE_FILE
        else:
            infos = FILE_INFOS

        # Recursive function for processing folders and their contents.
        def process_folder(folder_uri, top_dir):
            folder_file = Gio.File.new_for_uri(folder_uri)

            enumerator = folder_file.enumerate_children(infos,
                                                        Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
                                                        None)
            info = enumerator.next_file(None)

            while info:
                child = enumerator.get_child(info)
                child_uri = child.get_uri()
                child_basename = child.get_basename()

                file_type = info.get_file_type()

                if file_type == FileType.DIRECTORY:
                    add_file(op, child_basename, child_uri, top_dir, info)
                    process_folder(child_uri, top_dir)
                else:
                    add_file(op, child_basename, child_uri, top_dir, info)

                info = enumerator.next_file(None)

        # Process the initial list.
        try:
            for uri in uri_list:
                file = Gio.File.new_for_uri(uri)
                top_dir_basenames.append(file.get_basename())

                info = file.query_info(infos, Gio.FileQueryInfoFlags.NONE, None)
                basename = file.get_basename()
                if len(uri_list) == 1:
                    op.mime_if_single = info.get_content_type()

                if info and info.get_file_type() == FileType.DIRECTORY:
                    top_dir = file.get_parent().get_uri()
                    add_file(op, basename, uri, None, info)
                    process_folder(uri, top_dir)
                    continue
                else:
                    add_file(op, basename, uri, None, info)
            op.top_dir_basenames = top_dir_basenames
        except Exception as e:
            error = e

        return error

class Progress():
    def __init__(self, progress, time_left_sec, bytes_per_sec):
        self.progress = progress
        self.time_left_sec = time_left_sec
        self.bytes_per_sec = bytes_per_sec
        self.progress_text = ""

class OpProgressTracker():
    def __init__(self, op):
        self.op = op
        self.total_size = op.total_size
        self.total_transferred = 0
        self.transfer_start_time = GLib.get_monotonic_time()
        self.last_update_time = self.transfer_start_time

    @util._idle
    def update_progress(self, size_read):
        self.total_transferred += size_read

        now = GLib.get_monotonic_time()

        if ((now - self.last_update_time) > PROGRESS_UPDATE_FREQ):
            self.last_update_time = now

            progress = self.total_transferred / self.total_size
            elapsed = now - self.transfer_start_time

            bytes_per_micro = self.total_transferred / elapsed
            bytes_per_sec = int(bytes_per_micro * 1000 * 1000)

            if bytes_per_sec == 0:
                bytes_per_sec = 1 # no a/0

            time_left_sec = (self.total_size - self.total_transferred) / bytes_per_sec

            logging.debug("Progress: %s time left, %s/s" % (util.format_time_span(time_left_sec), GLib.format_size(bytes_per_sec)))

            progress_report = Progress(progress, time_left_sec, bytes_per_sec)
            self.op.progress_report(progress_report)

    def finished(self):
        self.op.progress_report(Progress(1.0, 0, 0))

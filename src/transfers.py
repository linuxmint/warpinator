import os
import gettext

from gi.repository import GLib, Gio, GObject

import util
from util import FileType
import prefs
import warp_pb2

_ = gettext.gettext

FILE_INFOS = \
    "standard::size,standard::allocated-size,standard::name,standard::type,standard::symlink-target"
FILE_INFOS_SINGLE_FILE = \
    "standard::size,standard::allocated-size,standard::name,standard::type,standard::symlink-target,standard::content-type"

CHUNK_SIZE = 1024 * 1024
UPDATE_FREQ = 4 * 1000 * 1000

def load_file_in_chunks(path, display_name):
    gfile = Gio.File.new_for_path(path)
    stream = gfile.read(None)

    while True:
        bytes = stream.read_bytes(CHUNK_SIZE, None)
        if bytes.get_size() == 0:
            break

        response = warp_pb2.RemoteMachineInfo(avatar_chunk=bytes.get_data(), display_name=display_name)
        yield response

    stream.close()

# This represents a file to be transferred (this is used by the sender)
class File:
    def __init__(self, uri, basename, rel_path, size, file_type, symlink_target_path=None):
        self.uri = uri
        self.basename = basename
        self.relative_path = rel_path
        self.size = size
        self.file_type = file_type
        self.symlink_target_path = symlink_target_path

class FileSender(GObject.Object):
    def __init__(self, op, connect_name, timestamp, cancellable):
        super(FileSender, self).__init__()
        self.op = op
        self.connect_name = connect_name
        self.timestamp = timestamp
        self.cancellable = cancellable

        op.progress = 0.0
        op.current_progress_report = None
        op.progress_text = None

        self.transfer_start_time = GLib.get_monotonic_time()
        self.last_update_time = self.transfer_start_time
        self.current_bytes_read = 0

    def read_chunks(self):
        for file in self.op.resolved_files:
            if self.cancellable.is_set():
                return # StopIteration as different behaviors between 3.5 and 3.7, this works as well.

            if file.file_type == FileType.DIRECTORY:
                yield warp_pb2.FileChunk(relative_path=file.relative_path,
                                         file_type=file.file_type)
            elif file.file_type == FileType.SYMBOLIC_LINK:
                yield warp_pb2.FileChunk(relative_path=file.relative_path,
                                         file_type=file.file_type,
                                         symlink_target=file.symlink_target_path)
            else:
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
                    self.update_progress(size_read=last_size_read)

                    yield warp_pb2.FileChunk(relative_path=file.relative_path,
                                             file_type=file.file_type,
                                             chunk=b.get_data())

                stream.close()
                continue

        self.update_progress(size_read=0, finished=True)

    def update_progress(self, size_read=0, finished=False):
        self.current_bytes_read += size_read

        now = GLib.get_monotonic_time()
        if ((now - self.last_update_time) > UPDATE_FREQ) or finished:
            self.last_update_time = now

            progress = self.current_bytes_read / self.op.total_size
            elapsed = now - self.transfer_start_time
            bytes_per_micro = self.current_bytes_read / elapsed
            bytes_per_sec = int(bytes_per_micro * 1000 * 1000)
            time_left_sec = (self.op.total_size - self.current_bytes_read) / bytes_per_sec
            print("%s time left, %s/s" % (util.format_time_span(time_left_sec), GLib.format_size(bytes_per_sec)))
            report = warp_pb2.ProgressReport(info=warp_pb2.OpInfo(connect_name=self.connect_name, timestamp=self.timestamp),
                                             progress=1.0 if finished else progress,
                                             bytes_per_sec=bytes_per_sec,
                                             time_left_sec=int(time_left_sec))

            GLib.idle_add(self.op.progress_report, report, priority=GLib.PRIORITY_DEFAULT)

class FileReceiver(GObject.Object):
    def __init__(self, op):
        super(FileReceiver, self).__init__()
        self.save_path = prefs.get_save_path()
        self.op = op

        op.current_progress_report = None
        op.progress = 0.0
        op.progress_text = None

        self.current_path = None
        self.current_gfile = None
        self.current_stream = None

    def receive_data(self, s):
        save_path = prefs.get_save_path()

        path = os.path.join(save_path, s.relative_path)
        if path != self.current_path:
            if self.current_stream:
                self.current_stream.close()
                self.current_stream = None
                self.current_gfile = None

            self.current_path = path

        if s.file_type == FileType.DIRECTORY:
            os.makedirs(path, exist_ok=(not prefs.prevent_overwriting()))
        elif s.file_type == FileType.SYMBOLIC_LINK:
            absolute_symlink_target_path = os.path.join(save_path, s.symlink_target)

            file = Gio.File.new_for_path(path)
            file.make_symbolic_link(absolute_symlink_target_path, None)
        else:
            if not self.current_gfile:
                self.current_gfile = Gio.File.new_for_path(path)

                if prefs.prevent_overwriting():
                    flags = Gio.FileCreateFlags.NONE
                else:
                    flags = Gio.FileCreateFlags.REPLACE_DESTINATION

                self.current_stream = self.current_gfile.replace(None, False, flags, None)

            if len(s.chunk) == 0:
                return

            self.current_stream.write_bytes(GLib.Bytes(s.chunk), None)


def add_file(op, basename, uri, base_uri, info):
    relative_symlink_path = None

    # Normal files usually take more disk space than their actual size, so we want that
    # for checking free disk space on the target computer.  However, sparse files can
    # report a smaller allocated size on disk than their 'actual' size. For now we can
    # only copy files in their full state, and at the other end they'll no longer be
    # sparse, so we use the largest of the two sizes for our purposes.
    alloc_size = info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_STANDARD_ALLOCATED_SIZE)
    file_size = info.get_size()
    size = file_size if file_size > alloc_size else alloc_size

    file_type = info.get_file_type()

    if file_type == Gio.FileType.SYMBOLIC_LINK:
        symlink_target = info.get_symlink_target()
        if symlink_target:
            if symlink_target[0] == "/":
                symlink_file = Gio.File.new_for_path(symlink_target)
                relative_symlink_path = util.relpath_from_uri(symlink_file.get_uri(), base_uri)
                if not relative_symlink_path:
                    relative_symlink_path = symlink_target
            else:
                relative_symlink_path = symlink_target

    if base_uri:
        relative_path = util.relpath_from_uri(uri, base_uri)
    else:
        relative_path = basename

    file = File(uri, basename, relative_path, size, util.gfiletype_to_int_enum(file_type), relative_symlink_path)

    op.resolved_files.append(file)
    op.total_size += size
    op.total_count += 1

def gather_file_info(op):
        top_dir_basenames = []
        uri_list = op.uris

        if len(uri_list) == 1:
            infos = FILE_INFOS_SINGLE_FILE
        else:
            infos = FILE_INFOS

        # Recursive function for processing folders and their contents.
        def process_folder(folder_uri, top_dir):
            folder_file = Gio.File.new_for_uri(folder_uri)

            enumerator = folder_file.enumerate_children(infos, Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None)
            info = enumerator.next_file(None)

            while info:
                child = enumerator.get_child(info)
                child_uri = child.get_uri()
                child_basename = child.get_basename()

                file_type = info.get_file_type()

                if file_type == Gio.FileType.DIRECTORY:
                    add_file(op, child_basename, child_uri, top_dir, info)
                    process_folder(child_uri, top_dir)
                else:
                    add_file(op, child_basename, child_uri, top_dir, info)

                info = enumerator.next_file(None)

        # Process the initial list.
        for uri in uri_list:
            file = Gio.File.new_for_uri(uri)
            top_dir_basenames.append(file.get_basename())

            info = file.query_info(infos, Gio.FileQueryInfoFlags.NONE, None)
            basename = file.get_basename()
            if len(uri_list) == 1:
                op.mime_if_single = info.get_content_type()

            if info and info.get_file_type() == Gio.FileType.DIRECTORY:
                top_dir = file.get_parent().get_uri()
                add_file(op, basename, uri, None, info)
                process_folder(uri, top_dir)
                continue
            else:
                add_file(op, basename, uri, None, info)

        op.top_dir_basenames = top_dir_basenames

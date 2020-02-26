import socket
import time
import os
import threading
import gettext
from concurrent import futures

from gi.repository import GObject, GLib, Gio
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser

import grpc
import warp_pb2
import warp_pb2_grpc

import prefs
import util
import transfers
from util import TransferDirection, OpStatus, OpCommand

_ = gettext.gettext

#typedef
void = warp_pb2.VoidType()

if os.environ.get('https_proxy'):
    del os.environ['https_proxy']
if os.environ.get('http_proxy'):
    del os.environ['http_proxy']

#base
class Machine(GObject.Object):
    __gsignals__ = {
        'machine-info-changed': (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self, name, ip, port):
        super(Machine, self).__init__()

        self.ip_address = ip
        self.port = port
        self.connect_name = name

        self.avatar_surface = None
        self.display_name = name
        self.hostname = None
        self.starred = False
        self.transfer_ops = []

    def add_job(self, job):
        self.jobs.insert(job)

    def delete_job(self, job):
        try:
            self.jobs.remove(job)
        except ValueError as e:
            print("Can't delete unknown job")

# client
class RemoteMachine(Machine):
    __gsignals__ = {
        'ops-changed': (GObject.SignalFlags.RUN_LAST, None, ()),
        'new-incoming-op': (GObject.SignalFlags.RUN_LAST, None, (object,))
    }

    def __init__(self, *args, local_service_name=None):
        super(RemoteMachine, self).__init__(*args)
        self.recent_time = 0 # Keep monotonic time when visited on the user page
        self.favorite = False
        self.changed_source_id = 0
        self.sort_key = self.connect_name
        self.local_service_name = local_service_name

        prefs.prefs_settings.connect("changed::favorites", self.update_favorite_status)

    @util._idle
    def start(self):
        print("Connecting to %s" % self.connect_name)
        self.channel = grpc.insecure_channel("%s:%d" % (self.ip_address, self.port))
        future = grpc.channel_ready_future(self.channel)
        future.add_done_callback(self.channel_ready_cb)

    def channel_ready_cb(self, future):
        time.sleep(1)
        self.stub = warp_pb2_grpc.WarpStub(self.channel)
        self.get_remote_info()

    @util._idle
    def get_remote_info(self):
        self.update_machine_name_info()
        self.get_machine_user_avatar()

    def update_machine_name_info(self):
        def finished_cb(future):
            res = future.result()

            self.display_name = res.display_name
            self.hostname = res.hostname
            self.favorite = prefs.get_is_favorite(self.hostname)

            valid = GLib.utf8_make_valid(self.display_name, -1)
            self.sort_key = GLib.utf8_collate_key(valid.lower(), -1)

            self.emit_machine_info_changed()

        future_info = self.stub.GetRemoteMachineNames.future(void)
        future_info.add_done_callback(finished_cb)

    def get_machine_user_avatar(self):
        loader = util.CairoSurfaceLoader()

        iterator = self.stub.GetRemoteMachineAvatar(void)
        for chunk in iterator:
            loader.add_bytes(chunk.chunk)

        self.get_finished_avatar_surface(loader)

    @util._idle
    def get_finished_avatar_surface(self, loader):
        self.avatar_surface = loader.get_surface()
        self.emit_machine_info_changed()

    def send_transfer_op_request(self, op):
        def finished_cb(future):
            res = future.result()
            pass

        transfer_op = warp_pb2.TransferOpRequest(sender=op.sender,
                                                 sender_name=op.sender_name,
                                                 receiver=self.connect_name,
                                                 timestamp=op.start_time,
                                                 size=op.total_size,
                                                 count=op.total_count,
                                                 name_if_single=op.description,
                                                 mime_if_single=op.mime_if_single,
                                                 top_dir_basenames=op.top_dir_basenames)

        future_response = self.stub.ProcessTransferOpRequest.future(transfer_op)
        future_response.add_done_callback(finished_cb)

    def cancel_transfer_op_request(self, op, by_sender=False):
        if op.direction == TransferDirection.TO_REMOTE_MACHINE:
            name = op.sender
        else:
            name = self.local_service_name
        cancel_op = self.stub.CancelTransferOpRequest(warp_pb2.OpInfo(timestamp=op.start_time,
                                                                      connect_name=name))

        op.set_status(OpStatus.CANCELLED_PERMISSION_BY_SENDER if by_sender else OpStatus.CANCELLED_PERMISSION_BY_RECEIVER)

    @util._async
    def update_op_progress(self, op):
        progress_op = self.stub.ReportProgress(op.current_progress_report)

    # def pause_transfer_op(self, op):
        # stop_op = warp_pb2.PauseTransferOp(warp_pb2.OpInfo(timestamp=op.start_time))
        # self.emit("ops-changed")

    #### RECEIVER COMMANDS ####
    @util._async
    def start_transfer_op(self, op):
        receiver = transfers.FileReceiver(op)
        op.set_status(OpStatus.TRANSFERRING)

        op.file_iterator = self.stub.StartTransfer(warp_pb2.OpInfo(timestamp=op.start_time,
                                                                   connect_name=self.local_service_name))
        try:
            for data in op.file_iterator:
                receiver.receive_data(data)
        except grpc.RpcError as e:
            if op.file_iterator.code() == grpc.StatusCode.CANCELLED:
                return
            else:
                print("An error occurred receiving data from %s: %s" % (op.sender, op.file_iterator.details()))

        op.file_iterator = None
        op.set_status(OpStatus.FINISHED)

    def stop_transfer_op(self, op, by_sender=False):
        if op.direction == TransferDirection.TO_REMOTE_MACHINE:
            name = op.sender
        else:
            name = self.local_service_name

        if by_sender:
            print("stop transfer initiated by sender")
            op.file_send_cancellable.set()
            op.set_status(OpStatus.STOPPED_BY_SENDER)
        else:
            print("stop transfer initiated by receiver")
            op.file_iterator.cancel()
            op.set_status(OpStatus.STOPPED_BY_RECEIVER)

        stop_op = self.stub.StopTransfer(warp_pb2.OpInfo(timestamp=op.start_time,
                                                         connect_name=name))

    @util._async
    def send_files(self, uri_list):
        self.recent_time = GLib.get_monotonic_time()
        self.emit_machine_info_changed()

        op = SendOp(TransferDirection.TO_REMOTE_MACHINE,
                    self.local_service_name,
                    self.connect_name,
                    self.display_name,
                    uri_list)
        self.add_op(op)
        op.prepare_send_info()

    def update_favorite_status(self, pspec, data=None):
        self.favorite = prefs.get_is_favorite(self.hostname)
        self.emit_machine_info_changed()

    @util._idle
    def notify_remote_machine_of_new_op(self, op):
        if op.direction == TransferDirection.TO_REMOTE_MACHINE:
            self.send_transfer_op_request(op)

    @util._idle
    def add_op(self, op):
        if op not in self.transfer_ops:
            self.transfer_ops.append(op)
            op.connect("status-changed", self.emit_ops_changed)
            op.connect("op-command", self.op_command_issued)
            if isinstance(op, SendOp):
                op.connect("initial-setup-complete", self.notify_remote_machine_of_new_op)
            if isinstance(op, ReceiveOp):
                self.emit("new-incoming-op", op)
        self.emit_ops_changed()
        self.check_for_autostart(op)

    @util._idle
    def check_for_autostart(self, op):
        if op.status == OpStatus.WAITING_PERMISSION:
            if isinstance(op, ReceiveOp) and (not prefs.require_permission_for_transfer()):
                op.accept_transfer()

    @util._idle
    def remove_op(self, op):
        self.transfer_ops.remove(op)
        self.emit_ops_changed()

    @util._idle
    def emit_ops_changed(self, op=None):
        self.emit("ops-changed")

    @util._idle
    def op_command_issued(self, op, command):
        # send
        if command == OpCommand.UPDATE_PROGRESS:
            self.update_op_progress(op)
        elif command == OpCommand.CANCEL_PERMISSION_BY_SENDER:
            self.cancel_transfer_op_request(op, by_sender=True)
        elif command == OpCommand.PAUSE_TRANSFER:
            self.pause_transfer_op(op)
        elif command == OpCommand.STOP_TRANSFER_BY_SENDER:
            self.stop_transfer_op(op, by_sender=True)
        elif command == OpCommand.RETRY_TRANSFER:
            op.set_status(OpStatus.WAITING_PERMISSION)
            self.send_transfer_op_request(op)
        elif command == OpCommand.REMOVE_TRANSFER:
            self.remove_op(op)
        # receive
        elif command == OpCommand.START_TRANSFER:
            self.start_transfer_op(op)
        elif command == OpCommand.CANCEL_PERMISSION_BY_RECEIVER:
            self.cancel_transfer_op_request(op, by_sender=False)
        elif command == OpCommand.STOP_TRANSFER_BY_RECEIVER:
            self.stop_transfer_op(op, by_sender=False)
        elif command == OpCommand.REMOVE_TRANSFER:
            self.remove_transfer_op(op)

    def emit_machine_info_changed(self):
        if self.changed_source_id > 0:
            GLib.source_remove(self.changed_source_id)

        self.changed_source_id = GLib.idle_add(self.emit_machine_info_changed_cb)

    def emit_machine_info_changed_cb(self):
        self.emit("machine-info-changed")
        self.changed_source_id = 0
        return False

    def lookup_op(self, timestamp):
        for op in self.transfer_ops:
            if op.start_time == timestamp:
                return op

    def shutdown(self):
        print("Shutdown - closing connection to remote machine '%s'" % self.connect_name)
        # self.channel.close()

# server
class LocalMachine(warp_pb2_grpc.WarpServicer, Machine):
    __gsignals__ = {
        "remote-machine-added": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "remote-machine-removed": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "remote-machine-ops-changed": (GObject.SignalFlags.RUN_LAST, None, (str,)),

        "shutdown-complete": (GObject.SignalFlags.RUN_LAST, None, ())
    }
    def __init__(self, *args):
        self.service_name = "warp.%s._http._tcp.local." % util.get_ip()
        super(LocalMachine, self).__init__(self.service_name, util.get_ip(), prefs.get_server_port())

        self.remote_machines = {}

        self.server_runlock = threading.Condition()

        util.accounts.connect("account-loaded", self.user_account_loaded)

        self.start_zeroconf()
        self.start_server()
        self.start_remote_lookout()

    def user_account_loaded(self, client):
        self.display_name = util.accounts.get_real_name()

    def start_zeroconf(self):
        self.zc_srv = Zeroconf()
        self.info = ServiceInfo("_http._tcp.local.",
                                self.service_name,
                                socket.inet_aton(util.get_ip()), prefs.get_server_port(), 0, 0,
                                {}, "somehost.local.")
        self.zc_srv.register_service(self.info)

    def start_remote_lookout(self):
        print("Searching for others...")
        self.zc_cli = Zeroconf()
        self.browser = ServiceBrowser(self.zc_cli, "_http._tcp.local.", self)

    def remove_service(self, zeroconf, _type, name):
        if name == self.service_name or not name.count("warp"):
            return

        print("Service %s removed" % (name,))

        try:
            self.emit("remote-machine-removed", self.remote_machines[name])
            del self.remote_machines[name]
            print("Removing remote machine '%s'" % name)
        except KeyError:
            print("Removed client we never knew: %s" % name)

    @util._idle
    def add_service(self, zeroconf, _type, name):
        info = zeroconf.get_service_info(_type, name)

        if info and name.count("warp"):
            if name == self.service_name:
                return

            # zeroconf service info might have multiple ip addresses, extract it from their 'name'
            remote_ip = name.replace("warp.", "").replace("._http._tcp.local.", "")

            print("Client %s added at %s" % (name, remote_ip))

            try:
                machine = self.remote_machines[name]
            except KeyError:
                machine = RemoteMachine(name, remote_ip, info.port, local_service_name=self.service_name)
                machine.start()

            machine.connect("ops-changed", self.remote_ops_changed)
            self.remote_machines[name] = machine
            self.emit("remote-machine-added", machine)

    @util._idle
    def remote_ops_changed(self, remote_machine):
        self.emit("remote-machine-ops-changed", remote_machine.connect_name)

    @util._async
    def start_server(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        warp_pb2_grpc.add_WarpServicer_to_server(self, self.server)

        self.server.add_insecure_port('[::]:%d' % prefs.get_server_port())
        self.server.start()

        with self.server_runlock:
            print("Server running")
            self.server_runlock.wait()
            print("Server stopping")
            self.server.stop(grace=2).wait()
            self.emit_shutdown_complete()

    def shutdown(self):
        for machine in self.remote_machines.values():
            machine.start()

        self.zc_srv.unregister_service(self.info)
        self.zc_cli.close()
        self.zc_srv.close()

        with self.server_runlock:
            self.server_runlock.notify()

    @util._idle
    def emit_shutdown_complete(self):
        self.emit("shutdown-complete")

    # Sender server responders
    def GetRemoteMachineNames(self, request, context):
        while True:
            if not util.accounts.is_loaded:
                time.sleep(1)
            else:
                break

        return warp_pb2.RemoteMachineNames(display_name=util.accounts.get_real_name(),
                                           hostname=util.get_hostname())

    def GetRemoteMachineAvatar(self, request, context):
        while True:
            if not util.accounts.is_loaded:
                time.sleep(1)
            else:
                break

        path = util.accounts.get_face_path()
        return transfers.load_file_in_chunks(path)

    def ProcessTransferOpRequest(self, request, context):
        remote_machine = self.remote_machines[request.sender]
        for existing_op in remote_machine.transfer_ops:
            if existing_op.start_time == request.timestamp:
                existing_op.set_status(OpStatus.WAITING_PERMISSION)
                self.add_receive_op_to_remote_machine(existing_op)
                return void

        op = ReceiveOp(TransferDirection.FROM_REMOTE_MACHINE, request.sender)

        op.sender_name = request.sender_name
        op.receiver = request.receiver
        op.receiver_name = request.receiver_name
        op.status = OpStatus.WAITING_PERMISSION
        op.start_time = request.timestamp
        op.total_size = request.size
        op.total_count = request.count
        op.mime_if_single = request.mime_if_single
        op.name_if_single = request.name_if_single
        op.top_dir_basenames = request.top_dir_basenames

        op.connect("initial-setup-complete", self.add_receive_op_to_remote_machine)
        op.prepare_receive_info()

        return void

    def CancelTransferOpRequest(self, request, context):### good
        op = self.remote_machines[request.connect_name].lookup_op(request.timestamp)
        print("received cancel request at server")

        # If we receive this call, this means the op was cancelled remotely.  So,
        # our op with TO_REMOTE_MACHINE (we initiated it) was cancelled by the recipient.
        if op.direction == TransferDirection.TO_REMOTE_MACHINE:
            op.set_status(OpStatus.CANCELLED_PERMISSION_BY_RECEIVER)
        else:
            op.set_status(OpStatus.CANCELLED_PERMISSION_BY_SENDER)

        return void

    def RetryTransferOp(self, request, context):
        op = self.remote_machines[request.connect_name].lookup_op(request.timestamp)

        # initiate transfer again
        return void

    def PauseTransferOp(self, request, context):
        op = self.remote_machines[request.connect_name].lookup_op(request.timestamp)

        # pause how?
        return void

    def ReportProgress(self, request, context):
        op = self.remote_machines[request.info.connect_name].lookup_op(request.info.timestamp)
        op.update_progress(request)

        return void

    # receiver server responders
    def StartTransfer(self, request, context):
        op = self.remote_machines[request.connect_name].lookup_op(request.timestamp)
        cancellable = threading.Event()
        op.file_send_cancellable = cancellable

        start_time = GLib.get_monotonic_time()

        def transfer_done():
            print("Transfer of %s files (%s) finished in %s" % \
                (op.total_count, GLib.format_size(op.total_size),\
                 util.precise_format_time_span(GLib.get_monotonic_time() - start_time)))

            if op.file_send_cancellable.is_set():
                print("File send cancelled")
            op.file_send_cancellable = None

        context.add_callback(transfer_done)
        op.set_status(OpStatus.TRANSFERRING)

        sender = transfers.FileSender(op, self.service_name, request.timestamp, cancellable)
        return sender.read_chunks()

    def StopTransfer(self, request, context):### good
        op = self.remote_machines[request.connect_name].lookup_op(request.timestamp)

        # If we receive this call, this means the op was stopped remotely.  So,
        # our op with TO_REMOTE_MACHINE (we initiated it) was cancelled by the recipient.
        if op.direction == TransferDirection.TO_REMOTE_MACHINE:
            op.file_send_cancellable.set()
            print("Sender received stop transfer by receiver")
            op.set_status(OpStatus.STOPPED_BY_RECEIVER)
        else:
            op.file_iterator.cancel()
            print("Receiver received stop transfer by sender")
            op.set_status(OpStatus.STOPPED_BY_SENDER)

        return void

    def add_receive_op_to_remote_machine(self, op):
        self.remote_machines[op.sender].add_op(op)

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


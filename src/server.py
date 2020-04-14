import socket
import os
import threading
import gettext
from concurrent import futures

from gi.repository import GObject, GLib
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser

import grpc
import warp_pb2
import warp_pb2_grpc

import auth
import remote
import prefs
import util
import transfers
from ops import ReceiveOp
from util import TransferDirection, OpStatus

_ = gettext.gettext

#typedef
void = warp_pb2.VoidType()

MAX_CONNECT_RETRIES = 2
PING_TIME = 5
SERVICE_TYPE = "_warpinator._tcp.local."

# server
class Server(warp_pb2_grpc.WarpServicer, GObject.Object):
    __gsignals__ = {
        "remote-machine-added": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "remote-machine-removed": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "remote-machine-ops-changed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "server-started": (GObject.SignalFlags.RUN_LAST, None, ()),
        "shutdown-complete": (GObject.SignalFlags.RUN_LAST, None, ())
    }
    def __init__(self):
        self.service_name = "%s.%s" % (util.get_hostname(), SERVICE_TYPE)
        super(Server, self).__init__()
        GObject.Object.__init__(self)

        self.ip_address = util.get_ip()
        self.port = prefs.get_port()

        self.remote_machines = {}
        self.server_runlock = threading.Condition()

        self.browser = None
        self.zeroconf = None
        self.zeroconf = None
        self.info = None

        self.display_name = GLib.get_real_name()

        self.start_server()

    def start_zeroconf(self):
        self.zeroconf = Zeroconf()
        box_as_props = auth.get_singleton().get_server_cert_b64_dict()

        self.info = ServiceInfo(SERVICE_TYPE,
                                self.service_name,
                                socket.inet_aton(util.get_ip()),
                                prefs.get_port(),
                                properties=box_as_props)

        self.zeroconf.register_service(self.info)

    def start_remote_lookout(self):
        self.browser = ServiceBrowser(self.zeroconf, SERVICE_TYPE, self)

    @util._async
    def remove_service(self, zeroconf, _type, name):
        if name == self.service_name:
            return

        try:
            self.emit_remote_machine_removed(self.remote_machines[name])
            self.remote_machines[name].shutdown()

            print("Removing remote machine '%s'" % name)
        except KeyError:
            print("Removed client we never knew: %s" % name)

    @util._async
    def add_service(self, zeroconf, _type, name):
        info = zeroconf.get_service_info(_type, name)

        if info:
            if name == self.service_name:
                return

            remote_hostname = name.split(".")[0]
            remote_ip = socket.inet_ntoa(info.address)

            if not auth.get_singleton().process_remote_cert_b64_dict(remote_hostname, info.properties):
                print("Unable to authenticate with %s (%s)" % (remote_hostname, remote_ip))
                return

            # print("Client %s added at %s" % (name, remote_ip))

            try:
                machine = self.remote_machines[name]
                machine.port = info.port
            except KeyError:
                machine = remote.RemoteMachine(name,
                                               remote_hostname,
                                               remote_ip,
                                               info.port,
                                               self.service_name)

                self.remote_machines[name] = machine
                machine.connect("ops-changed", self.remote_ops_changed)
                self.emit_remote_machine_added(machine)

            machine.start()

    @util._idle
    def emit_remote_machine_added(self, remote_machine):
        self.emit("remote-machine-added", remote_machine)

    @util._idle
    def emit_remote_machine_removed(self, remote_machine):
        self.emit("remote-machine-removed", remote_machine)

    @util._idle
    def remote_ops_changed(self, remote_machine):
        self.emit("remote-machine-ops-changed", remote_machine.connect_name)

    @util._async
    def start_server(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10), options=None)
        warp_pb2_grpc.add_WarpServicer_to_server(self, self.server)

        pair = auth.get_singleton().get_server_creds()
        server_credentials = grpc.ssl_server_credentials((pair,))

        self.server.add_secure_port('[::]:%d' % prefs.get_port(), server_credentials)
        self.server.start()

        self.emit_server_started()
        self.start_discovery_services()

        with self.server_runlock:
            print("Server running")
            self.server_runlock.wait()
            print("Server stopping")
            self.server.stop(grace=2).wait()
            self.emit_shutdown_complete()
            self.server = None

    @util._idle
    def emit_server_started(self):
        self.emit("server-started")

    @util._idle
    def start_discovery_services(self):
        self.start_zeroconf()
        self.start_remote_lookout()

    @util._async
    def shutdown(self):
        remote_machines = list(self.remote_machines.values())
        for machine in remote_machines:
            self.emit_remote_machine_removed(machine)
            machine.shutdown()

        remote_machines = None

        try:
            self.browser.cancel()
            self.zeroconf.unregister_service(self.info)
            self.zeroconf.close()
        except AttributeError as e:
            print(e)
            pass # zeroconf never started if the server never started

        with self.server_runlock:
            self.server_runlock.notify()

    @util._idle
    def emit_shutdown_complete(self):
        self.emit("shutdown-complete")

    def Ping(self, request, context):
        return void

    def GetRemoteMachineInfo(self, request, context):
        return warp_pb2.RemoteMachineInfo(display_name=GLib.get_real_name(),
                                          user_name=GLib.get_user_name())

    def GetRemoteMachineAvatar(self, request, context):
        path = os.path.join(GLib.get_home_dir(), ".face")
        if os.path.exists(path):
            return transfers.load_file_in_chunks(path)
        else:
            context.abort(code=grpc.StatusCode.NOT_FOUND, details='.face file not found!')

    def ProcessTransferOpRequest(self, request, context):
        remote_machine = self.remote_machines[request.info.connect_name]
        for existing_op in remote_machine.transfer_ops:
            if existing_op.start_time == request.info.timestamp:
                existing_op.set_status(OpStatus.WAITING_PERMISSION)
                self.add_receive_op_to_remote_machine(existing_op)
                return void

        op = ReceiveOp(request.info.connect_name)

        op.start_time = request.info.timestamp

        op.sender_name = request.sender_name
        op.receiver = request.receiver
        op.receiver_name = request.receiver_name
        op.status = OpStatus.WAITING_PERMISSION
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

    # def PauseTransferOp(self, request, context):
    #     op = self.remote_machines[request.connect_name].lookup_op(request.timestamp)

    #     # pause how?
    #     return void

    # receiver server responders
    def StartTransfer(self, request, context):
        start_time = GLib.get_monotonic_time()

        op = self.remote_machines[request.connect_name].lookup_op(request.timestamp)
        cancellable = threading.Event()
        op.file_send_cancellable = cancellable

        op.set_status(OpStatus.TRANSFERRING)

        op.progress_tracker = transfers.OpProgressTracker(op)
        op.current_progress_report = None
        sender = transfers.FileSender(op, self.service_name, request.timestamp, cancellable)

        def transfer_done():
            if sender.error != None:
                op.set_error(sender.error)
                op.stop_transfer()
                op.set_status(OpStatus.FAILED_UNRECOVERABLE)
            elif op.file_send_cancellable.is_set():
                print("File send cancelled")
            else:
                print("Transfer of %s files (%s) finished in %s" % \
                    (op.total_count, GLib.format_size(op.total_size),\
                     util.precise_format_time_span(GLib.get_monotonic_time() - start_time)))

        context.add_callback(transfer_done)
        return sender.read_chunks()

    def StopTransfer(self, request, context):
        op = self.remote_machines[request.info.connect_name].lookup_op(request.info.timestamp)

        # If we receive this call, this means the op was stopped remotely.  So,
        # our op with TO_REMOTE_MACHINE (we initiated it) was cancelled by the recipient.

        if request.error:
            op.error_msg = _("An error occurred on the remote machine")

        if op.direction == TransferDirection.TO_REMOTE_MACHINE:
            op.file_send_cancellable.set()
            print("Sender received stop transfer by receiver")
            if op.error_msg == "":
                op.set_status(OpStatus.STOPPED_BY_RECEIVER)
            else:
                op.set_status(OpStatus.FAILED)
        else:
            try:
                op.file_iterator.cancel()
            except AttributeError:
                # we may not have this yet if the transfer fails upon the initial response
                # (meaning we haven't returned the generator)
                pass
            print("Receiver received stop transfer by sender")
            if op.error_msg == "":
                op.set_status(OpStatus.STOPPED_BY_SENDER)
            else:
                op.set_status(OpStatus.FAILED)

        return void

    def add_receive_op_to_remote_machine(self, op):
        self.remote_machines[op.sender].add_op(op)

    def list_remote_machines(self):
        return self.remote_machines.values()

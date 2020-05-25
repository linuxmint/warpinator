import socket
import os
import threading
import gettext
import logging
import time
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
from util import TransferDirection, OpStatus, RemoteStatus

_ = gettext.gettext

void = warp_pb2.VoidType()

SERVICE_TYPE = "_warpinator._tcp.local."

# server
class Server(threading.Thread, warp_pb2_grpc.WarpServicer, GObject.Object):
    __gsignals__ = {
        "remote-machine-added": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "remote-machine-removed": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "remote-machine-ops-changed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "local-info-changed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "server-started": (GObject.SignalFlags.RUN_LAST, None, ()),
        "shutdown-complete": (GObject.SignalFlags.RUN_LAST, None, ())
    }
    def __init__(self):
        threading.Thread.__init__(self, name="server-thread")
        super(Server, self).__init__()
        GObject.Object.__init__(self)

        self.service_name = None
        self.service_ident = None

        self.ip_address = util.get_ip()
        self.port = prefs.get_port()

        self.remote_machines = {}

        self.server_thread_keepalive = threading.Event()

        self.server = None
        self.browser = None
        self.zeroconf = None
        self.zeroconf = None
        self.info = None

        self.display_name = GLib.get_real_name()
        self.start()

    def start_zeroconf(self):
        self.zeroconf = Zeroconf()

        self.service_ident = auth.get_singleton().get_ident()
        self.service_name = "%s.%s" % (self.service_ident, SERVICE_TYPE)

        # If this process is killed (either kill ot logout), the service
        # never gets unregistered, which will prevent remotes from seeing us
        # when we come back.  Our first service info is to get us back on
        # momentarily, and the unregister properly, so remotes get notified.
        # Then we'll do it again without the flush property for the real
        # connection.
        init_info = ServiceInfo(SERVICE_TYPE,
                                self.service_name,
                                socket.inet_aton(util.get_ip()),
                                prefs.get_port(),
                                properties={ 'hostname': util.get_hostname(),
                                             'type': 'flush' })

        self.zeroconf.register_service(init_info)
        time.sleep(1)
        self.zeroconf.unregister_service(init_info)
        time.sleep(1)

        self.info = ServiceInfo(SERVICE_TYPE,
                                self.service_name,
                                socket.inet_aton(util.get_ip()),
                                prefs.get_port(),
                                properties={ 'hostname': util.get_hostname(),
                                             'type': 'real' })

        self.zeroconf.register_service(self.info)
        self.browser = ServiceBrowser(self.zeroconf, SERVICE_TYPE, self)

        return False

    @util._async
    def remove_service(self, zeroconf, _type, name):
        if name == self.service_name:
            return

        ident = name.partition(".")[0]
        auth.get_singleton().cancel_request_loop(ident)

        try:
            self.idle_emit("remote-machine-removed", self.remote_machines[ident])
            self.remote_machines[ident].shutdown()
        except KeyError:
            logging.debug("Removed client we never knew: %s" % name)

    @util._async
    def add_service(self, zeroconf, _type, name):
        info = zeroconf.get_service_info(_type, name)

        if info:
            # logging.debug("New service info: %s", info)

            ident = name.partition(".")[0]

            try:
                remote_hostname = info.properties[b"hostname"].decode()
            except KeyError:
                logging.critical("No hostname in service info properties.  Is this an old version?")
                return

            try:
                # Check if this is a flush registration to reset the remote servier's presence.
                if info.properties[b"type"].decode() == "flush":
                    logging.debug("Received flush service info (ignoring): %s (%s)" % (remote_hostname, ident))
                    return
            except KeyError:
                logging.warning("No type in service info properties, assuming this is a real connect attempt")

            remote_ip = socket.inet_ntoa(info.address)

            if ident == self.service_ident:
                return

            # This will block if the remote's warp udp port is closed, until either the port is unblocked
            # or we tell the auth object to shutdown, in which case the request timer will cancel and return
            # here immediately (with None)
            got_cert = auth.get_singleton().retrieve_remote_cert(ident, remote_hostname, remote_ip, info.port)

            if not got_cert:
                logging.critical("Unable to authenticate with %s (%s)" % (remote_hostname, remote_ip))
                return

            try:
                logging.debug("Found existing remote: %s" % ident)
                machine = self.remote_machines[ident]
                # Update our connect info if it changed.
                machine.hostname = remote_hostname
                machine.ip_address = remote_ip
                machine.port = info.port
            except KeyError:
                display_hostname = remote_hostname
                i = 1

                while True:
                    found = False

                    for key in self.remote_machines.keys():
                        remote_machine = self.remote_machines[key]

                        if remote_machine.display_hostname == display_hostname:
                            display_hostname = "%s[%d]" % (remote_hostname, i)
                            found = True
                            break

                    i += 1

                    if not found:
                        break

                logging.debug("New remote: %s, hostname: %s, ip: %s:%d" % (ident, display_hostname, remote_ip, info.port))
                machine = remote.RemoteMachine(ident,
                                               remote_hostname,
                                               display_hostname,
                                               remote_ip,
                                               info.port,
                                               self.service_ident)

                self.remote_machines[ident] = machine
                machine.connect("ops-changed", self.remote_ops_changed)
                self.idle_emit("remote-machine-added", machine)

            machine.start()

    def run(self):
        logging.debug("Starting server")

        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=4), options=None)
        warp_pb2_grpc.add_WarpServicer_to_server(self, self.server)

        pair = auth.get_singleton().get_server_creds()
        server_credentials = grpc.ssl_server_credentials((pair,))

        self.server.add_secure_port('[::]:%d' % prefs.get_port(), server_credentials)
        self.server.start()

        auth.get_singleton().restart_cert_server()

        self.idle_emit("server-started")
        self.start_zeroconf()

        self.server_thread_keepalive.clear()

        # **** RUNNING ****
        while not self.server_thread_keepalive.is_set():
            self.server_thread_keepalive.wait(.5)
        # **** STOPPING ****

        logging.debug("Stopping server")

        remote_machines = list(self.remote_machines.values())
        for machine in remote_machines:
            self.idle_emit("remote-machine-removed", machine)
            machine.shutdown()

        remote_machines = None

        logging.debug("Stopping authentication server")
        auth.get_singleton().shutdown()

        logging.debug("Stopping discovery and advertisement")
        self.zeroconf.close()

        logging.debug("Terminating server")
        self.server.stop(grace=2).wait()

        self.idle_emit("shutdown-complete")
        self.server = None

        logging.debug("Server stopped")

    def shutdown(self):
        self.server_thread_keepalive.set()

    def add_receive_op_to_remote_machine(self, op):
        self.remote_machines[op.sender].add_op(op)

    @util._idle
    def remote_ops_changed(self, remote_machine):
        self.emit("remote-machine-ops-changed", remote_machine.ident)

    def list_remote_machines(self):
        return self.remote_machines.values()

    @util._idle
    def idle_emit(self, signal, *callback_data):
        self.emit(signal, *callback_data)

    def Ping(self, request, context):
        logging.debug("Ping from '%s'" % request.readable_name)

        try:
            remote = self.remote_machines[request.id]
        except KeyError as e:
            logging.debug("Received ping from unknown remote (or not fully online yet) '%s': %s"
                              % (request.readable_name, e))

        return void

    def CheckDuplexConnection(self, request, context):
        logging.debug("CheckDuplexConnection from '%s'" % request.readable_name)
        response = False

        try:
            remote = self.remote_machines[request.id]
            response = (remote.status in (RemoteStatus.AWAITING_DUPLEX, RemoteStatus.ONLINE))
        except KeyError:
            pass

        return warp_pb2.HaveDuplex(response=response)

    def GetRemoteMachineInfo(self, request, context):
        logging.debug("GetRemoteMachineInfo from '%s'" % request.readable_name)

        return warp_pb2.RemoteMachineInfo(display_name=GLib.get_real_name(),
                                          user_name=GLib.get_user_name())

    def GetRemoteMachineAvatar(self, request, context):
        logging.debug("GetRemoteMachineAvatar from '%s'" % request.readable_name)

        path = os.path.join(GLib.get_home_dir(), ".face")
        if os.path.exists(path):
            return transfers.load_file_in_chunks(path)
        else:
            context.abort(code=grpc.StatusCode.NOT_FOUND, details='.face file not found!')

    def ProcessTransferOpRequest(self, request, context):
        logging.debug("ProcessTransferOpRequest from '%s'" % request.info.readable_name)

        remote_machine = self.remote_machines[request.info.ident]

        try:
            remote_machine = self.remote_machines[request.info.ident]
        except KeyError as e:
            logging.warning("Received transfer op request for unknown op: %s" % e)
            return

        for existing_op in remote_machine.transfer_ops:
            if existing_op.start_time == request.info.timestamp:
                existing_op.set_status(OpStatus.WAITING_PERMISSION)
                self.add_receive_op_to_remote_machine(existing_op)
                return void

        op = ReceiveOp(request.info.ident)

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
        logging.debug("CancelTransferOpRequest from '%s'" % request.readable_name)

        try:
            op = self.remote_machines[request.ident].lookup_op(request.timestamp)
        except KeyError as e:
            logging.warning("Received cancel transfer op request for unknown op: %s" % e)
            return

        logging.debug("received cancel request at server")

        # If we receive this call, this means the op was cancelled remotely.  So,
        # our op with TO_REMOTE_MACHINE (we initiated it) was cancelled by the recipient.
        if op.direction == TransferDirection.TO_REMOTE_MACHINE:
            op.set_status(OpStatus.CANCELLED_PERMISSION_BY_RECEIVER)
        else:
            op.set_status(OpStatus.CANCELLED_PERMISSION_BY_SENDER)

        return void

    # receiver server responders
    def StartTransfer(self, request, context):
        logging.debug("StartTransfer from '%s'" % request.readable_name)

        start_time = GLib.get_monotonic_time()

        try:
            remote = self.remote_machines[request.ident]
        except KeyError as e:
            logging.warning("Received start transfer from unknown remote '%s': %s" % (request.readable_name, e))
            return

        try:
            op = self.remote_machines[request.ident].lookup_op(request.timestamp)
        except KeyError as e:
            logging.warning("Received start transfer for unknown op: %s" % e)
            return

        cancellable = threading.Event()
        op.file_send_cancellable = cancellable

        op.set_status(OpStatus.TRANSFERRING)

        op.progress_tracker = transfers.OpProgressTracker(op)
        op.current_progress_report = None
        sender = transfers.FileSender(op, request.timestamp, cancellable)

        def transfer_done():
            if sender.error != None:
                op.set_error(sender.error)
                op.stop_transfer()
                op.set_status(OpStatus.FAILED_UNRECOVERABLE)
            elif op.file_send_cancellable.is_set():
                logging.debug("File send cancelled")
            else:
                logging.debug("Transfer of %s files (%s) finished in %s" % \
                    (op.total_count, GLib.format_size(op.total_size),\
                     util.precise_format_time_span(GLib.get_monotonic_time() - start_time)))

        context.add_callback(transfer_done)
        return sender.read_chunks()

    def StopTransfer(self, request, context):
        logging.debug("StopTransfer from '%s'" % request.info.readable_name)

        try:
            op = self.remote_machines[request.info.ident].lookup_op(request.info.timestamp)
        except KeyError as e:
            logging.warning("Received stop transfer for unknown op: %s" % e)
            return

        # If we receive this call, this means the op was stopped remotely.  So,
        # our op with TO_REMOTE_MACHINE (we initiated it) was cancelled by the recipient.

        if request.error:
            op.error_msg = _("An error occurred on the remote machine")

        if op.direction == TransferDirection.TO_REMOTE_MACHINE:
            op.file_send_cancellable.set()
            logging.debug("Sender received stop transfer by receiver: %s" % op.error_msg)
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
            logging.debug("Receiver received stop transfer by sender: %s" % op.error_msg)
            if op.error_msg == "":
                op.set_status(OpStatus.STOPPED_BY_SENDER)
            else:
                op.set_status(OpStatus.FAILED)

        return void

#!/usr/bin/python3

import os
import threading
import gettext
import logging
import time
import pkg_resources
from concurrent import futures

from gi.repository import GObject, GLib

import grpc
import warp_pb2
import warp_pb2_grpc

import config
import auth
import interceptors
import networkmonitor
import remote
import remote_registration
import prefs
import util
import transfers
from ops import ReceiveOp
from util import TransferDirection, OpStatus, RemoteStatus

try:
    import zeroconf_
    from zeroconf_ import ServiceInfo, Zeroconf, ServiceBrowser
except:
    import zeroconf

    zc_version = pkg_resources.parse_version(zeroconf.__version__)
    zc_min_version = pkg_resources.parse_version("0.27.0")

    if zc_version < zc_min_version:
        print("Python3 zeroconf must be >= %s" % zc_min_version)
        exit(1)

    from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser

_ = gettext.gettext

void = warp_pb2.VoidType()

SERVICE_TYPE = "_warpinator._tcp.local."

# server (this is on a separate thread from the ui, grpc isn't compatible with
# gmainloop)
class Server(threading.Thread, warp_pb2_grpc.WarpServicer, GObject.Object):
    __gsignals__ = {
        "remote-machine-added": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "remote-machine-removed": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "remote-machine-ops-changed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "local-info-changed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "server-started": (GObject.SignalFlags.RUN_LAST, None, ()),
        "shutdown-complete": (GObject.SignalFlags.RUN_LAST, None, ())
    }
    def __init__(self, ip_info, port, auth_port):
        threading.Thread.__init__(self, name="server-thread")
        super(Server, self).__init__()
        GObject.Object.__init__(self)

        self.service_name = None
        self.service_ident = None

        self.ip_info = ip_info
        self.port = port
        self.auth_port = auth_port

        self.untrusted_remote_machines = {}
        self.remote_machines = {}
        self.remote_registrar = None

        self.server_thread_keepalive = threading.Event()

        self.netmon = networkmonitor.get_network_monitor()

        self.server = None
        self.browser = None
        self.zeroconf = None
        self.info = None

        self.display_name = GLib.get_real_name()
        self.start()

    def start_zeroconf(self):
        try:
            logging.info("Using bundled zeroconf v%s" % zeroconf_.__version__)
        except:
            logging.info("Using system zeroconf v%s" % zeroconf.__version__)

        self.zeroconf = Zeroconf(interfaces=[self.ip_info.ip4_address])

        self.service_ident = auth.get_singleton().get_ident()
        self.service_name = "%s.%s" % (self.service_ident, SERVICE_TYPE)

        # If this process is killed (either kill or network issue), the service
        # never gets unregistered, which will prevent remotes from seeing us
        # when we come back.  Our first service info is to get us back on
        # momentarily, and the unregister properly, so remotes get notified.
        # Then we'll do it again without the flush property for the real
        # connection.

        init_info = ServiceInfo(SERVICE_TYPE,
                                self.service_name,
                                port=self.port,
                                addresses=self.ip_info.as_binary_list(),
                                properties={ 'hostname': util.get_hostname(),
                                             'type': 'flush' })

        self.zeroconf.register_service(init_info)
        time.sleep(3)
        self.zeroconf.unregister_service(init_info)
        time.sleep(3)

        self.info = ServiceInfo(SERVICE_TYPE,
                                self.service_name,
                                port=self.port,
                                addresses=self.ip_info.as_binary_list(),
                                properties={ 'hostname': util.get_hostname(),
                                             'api-version': config.RPC_API_VERSION,
                                             'auth-port': str(prefs.get_auth_port()),
                                             'type': 'real' })

        self.zeroconf.register_service(self.info)
        self.browser = ServiceBrowser(self.zeroconf, SERVICE_TYPE, self, addr=self.ip_info.ip4_address)

        return False

    # Will be mandatory eventually, this will have to be here even if we don't care about it.
    def update_service(self, zeroconf, _type, name):
        pass

    # Zeroconf worker thread
    def remove_service(self, zeroconf, _type, name):
        if name == self.service_name:
            return

        ident = name.partition(".%s" % SERVICE_TYPE)[0]

        try:
            remote = self.remote_machines[ident]
        except KeyError:
            logging.debug(">>> Discovery: unknown service ident (%s) reported as gone by zc." % ident)
            return

        logging.debug(">>> Discovery: service %s (%s:%d) has disappeared."
                          % (remote.display_hostname, remote.ip_info.ip4_address, remote.port))

        remote.has_zc_presence = False

    # Zeroconf worker thread
    def add_service(self, zeroconf, _type, name):
        info = zeroconf.get_service_info(_type, name)

        if info:
            ident = name.partition(".%s" % SERVICE_TYPE)[0]

            try:
                remote_hostname = info.properties[b"hostname"].decode()
            except KeyError:
                logging.critical(">>> Discovery: no hostname in service info properties.  Is this an old version?")
                return

            remote_ip_info = util.RemoteInterfaceInfo(info.addresses)

            if remote_ip_info == self.ip_info:
                return

            try:
                # Check if this is a flush registration to reset the remote server's presence.
                if info.properties[b"type"].decode() == "flush":
                    logging.debug(">>> Discovery: received flush service info (ignoring): %s (%s:%d)"
                                      % (remote_hostname, remote_ip_info.ip4_address, info.port))
                    return
            except KeyError:
                logging.warning("No type in service info properties, assuming this is a real connect attempt")

            if ident == self.service_ident:
                return

            try:
                api_version = info.properties[b"api-version"].decode()
                auth_port = int(info.properties[b"auth-port"].decode())
            except KeyError:
                api_version = "1"
                auth_port = 0

            # FIXME: I'm not sure why we still get discovered by other networks in some cases -
            # The Zeroconf object has a specific ip it is set to, what more do I need to do?
            if not self.netmon.same_subnet(remote_ip_info):
                logging.debug(">>> Discovery: service is not on this subnet, ignoring: %s (%s)" % (remote_hostname, remote_ip_info.ip4_address))
                return

            try:
                machine = self.remote_machines[ident]
                machine.has_zc_presence = True
                logging.debug(">>> Discovery: existing remote: %s (%s:%d)"
                                  % (machine.display_hostname, remote_ip_info.ip4_address, info.port))

                # If the remote truly is the same one (our service info just dropped out
                # momentarily), this will end up just retrieving the current cert again.
                # If this was a real disconnect we didn't notice, we'll have the new cert
                # which we'll need when our supposedly existing connection tries to continue
                # pinging. It will fail out and restart the connection loop, and will need
                # this updated one.

                # This blocks the zeroconf thread.
                if not self.remote_registrar.register(ident, remote_hostname, remote_ip_info, info.port, auth_port, api_version) or self.server_thread_keepalive.is_set():
                    logging.warning("Register failed, or the server was shutting down during registration, ignoring remote %s (%s:%d) auth port: %d"
                                     % (remote_hostname, remote_ip_info.ip4_address, info.port, auth_port))
                    return

                if machine.status == RemoteStatus.ONLINE:
                    logging.debug(">>> Discovery: rejoining existing connect with %s (%s:%d)"
                                  % (machine.display_hostname, remote_ip_info.ip4_address, info.port))
                    return

                # Update our connect info if it changed.
                machine.hostname = remote_hostname
                machine.ip_info = remote_ip_info
                machine.port = info.port
                machine.api_version = api_version
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

                logging.debug(">>> Discovery: new remote: %s (%s:%d)"
                                  % (display_hostname, remote_ip_info.ip4_address, info.port))

                machine = remote.RemoteMachine(ident,
                                               remote_hostname,
                                               display_hostname,
                                               remote_ip_info,
                                               info.port,
                                               self.service_ident,
                                               api_version)

                # This blocks the zeroconf thread. Registration will timeout
                if not self.remote_registrar.register(ident, remote_hostname, remote_ip_info, info.port, auth_port, api_version) or self.server_thread_keepalive.is_set():
                    logging.warning("Register failed, or the server was shutting down during registration, ignoring remote %s (%s:%d) auth port: %d"
                                     % (remote_hostname, remote_ip_info.ip4_address, info.port, auth_port))
                    return

                self.remote_machines[ident] = machine
                machine.connect("ops-changed", self.remote_ops_changed)
                machine.connect("remote-status-changed", self.remote_status_changed)
                self.idle_emit("remote-machine-added", machine)

            machine.has_zc_presence = True

            machine.shutdown() # This does nothing if run more than once.  It's here to make sure
                               # the previous start thread is complete before starting a new one.
                               # This is needed in the corner case where the remote has gone offline,
                               # and returns before our Ping loop times out and closes the thread
                               # itself.

            machine.start_remote_thread()

    def run(self):
        logging.debug("Server: starting server on %s (%s)" % (self.ip_info.ip4_address, self.ip_info.iface))
        logging.info("Using api version %s" % config.RPC_API_VERSION)
        logging.info("Our uuid: %s" % auth.get_singleton().get_ident())


        self.remote_registrar = remote_registration.Registrar(self.ip_info, self.port, self.auth_port)
        util.initialize_rpc_threadpool()

        options=(
            ('grpc.keepalive_time_ms', 10 * 1000),
            ('grpc.keepalive_timeout_ms', 5 * 1000),
            ('grpc.keepalive_permit_without_calls', True),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.http2.min_time_between_pings_ms', 10 * 1000),
            ('grpc.http2.min_ping_interval_without_data_ms',  5 * 1000)
        )

        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=prefs.get_server_pool_max_threads()),
                                  options=options,
                                  interceptors=[interceptors.ChunkCompressor()])
        warp_pb2_grpc.add_WarpServicer_to_server(self, self.server)

        pair = auth.get_singleton().get_server_creds()
        server_credentials = grpc.ssl_server_credentials((pair,))

        if self.ip_info.ip4_address:
            self.server.add_secure_port('%s:%d' % (self.ip_info.ip4_address, self.port),
                                        server_credentials)
        # if self.ip_info.ip6_address:
        #     self.server.add_secure_port('%s:%d' % (self.ip_info.ip6_address, self.port),
        #                                 server_credentials)
        self.server.start()

        self.server_thread_keepalive.clear()

        try:
            self.start_zeroconf()
        except Exception as e:
            logging.critical("Zeroconf failed to start, server will terminate: %s" % e)
            self.server_thread_keepalive.set()

        self.idle_emit("server-started")

        logging.info("Server: ACTIVE")

        # **** RUNNING ****
        while not self.server_thread_keepalive.is_set():
            self.server_thread_keepalive.wait(10)
        # **** STOPPING ****

        self.remote_registrar.shutdown_registration_servers()
        self.remote_registrar = None

        logging.debug("Server: stopping discovery and advertisement")

        # If the network is down, this will probably print an exception - it's ok,
        # zeroconf catches it.
        try:
            self.zeroconf.close()
        except:
            logging.critical("Can't close Zeroconf - maybe it failed to start")
            pass

        remote_machines = list(self.remote_machines.values())
        for remote in remote_machines:
            self.idle_emit("remote-machine-removed", remote)
            logging.debug("Server: Closing connection to remote machine %s (%s:%d)"
                              % (remote.display_hostname, remote.ip_info.ip4_address, remote.port))

            remote.shutdown()

        remote_machines = None

        logging.debug("Server: terminating server")
        self.server.stop(grace=2).wait()

        self.idle_emit("shutdown-complete")
        self.server = None

        util.global_rpc_threadpool.shutdown(wait=True)
        logging.debug("Server: server stopped")

    def shutdown(self):
        self.server_thread_keepalive.set()

    def remote_status_changed(self, remote):
        if remote.status == RemoteStatus.OFFLINE:
            self.emit("remote-machine-removed", remote)

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
        logging.debug("Server Ping: from %s" % request.readable_name)

        try:
            remote = self.remote_machines[request.id]
        except KeyError as e:
            logging.debug("Server Ping: ping is from unknown remote (or not fully online yet)")

        return void

    def CheckDuplexConnection(self, request, context):
        logging.debug("Server RPC: CheckDuplexConnection from '%s'" % request.readable_name)
        response = False

        try:
            remote = self.remote_machines[request.id]
            response = (remote.status in (RemoteStatus.AWAITING_DUPLEX, RemoteStatus.ONLINE))
        except KeyError:
            pass

        return warp_pb2.HaveDuplex(response=response)

    def WaitingForDuplex(self, request, context):
        logging.debug("Server RPC: WaitingForDuplex from '%s' (api v2)" % request.readable_name)

        max_tries = 20
        i = 0

        # try for ~5 seconds (the caller aborts at 4)
        while i < max_tries:
            response = False

            try:
                remote = self.remote_machines[request.id]
                response = (remote.status in (RemoteStatus.AWAITING_DUPLEX, RemoteStatus.ONLINE))
            except KeyError:
                pass

            if response:
                break
            else:
                i += 1
                if i == max_tries:
                    context.abort(code=grpc.StatusCode.DEADLINE_EXCEEDED,
                                  details='Server timed out while waiting for his corresponding remote to connect back to you.')
                    return
                time.sleep(.25)

        return warp_pb2.HaveDuplex(response=response)

    def GetRemoteMachineInfo(self, request, context):
        logging.debug("Server RPC: GetRemoteMachineInfo from '%s'" % request.readable_name)

        return warp_pb2.RemoteMachineInfo(display_name=GLib.get_real_name(),
                                          user_name=GLib.get_user_name())

    def GetRemoteMachineAvatar(self, request, context):
        logging.debug("Server RPC: GetRemoteMachineAvatar from '%s'" % request.readable_name)

        path = os.path.join(GLib.get_home_dir(), ".face")
        if os.path.exists(path):
            return transfers.load_file_in_chunks(path)
        else:
            context.abort(code=grpc.StatusCode.NOT_FOUND, details='.face file not found!')

    def ProcessTransferOpRequest(self, request, context):
        logging.debug("Server RPC: ProcessTransferOpRequest from '%s'" % request.info.readable_name)

        remote_machine = self.remote_machines[request.info.ident]

        try:
            remote_machine = self.remote_machines[request.info.ident]
        except KeyError as e:
            logging.warning("Received transfer op request for unknown op: %s" % e)
            return

        for existing_op in remote_machine.transfer_ops:
            if existing_op.start_time == request.info.timestamp:
                # Compression could have changed for a restart, as it's not tied to the op.
                try:
                    existing_op.use_compression = request.info.use_compression
                except AttributeError:
                    existing_op.use_compression = False
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

        # If request.info (grpc_pb2.OpInfo) doesn't have a use_compression field,
        # If doesn't support compression (older version of warp).
        try:
            op.use_compression = request.info.use_compression
        except AttributeError:
            op.use_compression = False

        op.connect("initial-setup-complete", self.add_receive_op_to_remote_machine)
        op.prepare_receive_info()

        return void

    def CancelTransferOpRequest(self, request, context):### good
        logging.debug("Server RPC: CancelTransferOpRequest from '%s'" % request.readable_name)

        try:
            op = self.remote_machines[request.ident].lookup_op(request.timestamp)
        except KeyError as e:
            logging.warning("Received cancel transfer op request for unknown op: %s" % e)
            return

        # If we receive this call, this means the op was cancelled remotely.  So,
        # our op with TO_REMOTE_MACHINE (we initiated it) was cancelled by the recipient.
        if op.direction == TransferDirection.TO_REMOTE_MACHINE:
            op.set_status(OpStatus.CANCELLED_PERMISSION_BY_RECEIVER)
        else:
            op.set_status(OpStatus.CANCELLED_PERMISSION_BY_SENDER)

        return void

    # receiver server responders
    def StartTransfer(self, request, context):
        logging.debug("Server RPC: StartTransfer from '%s'" % request.readable_name)

        start_time = GLib.get_monotonic_time()

        try:
            remote = self.remote_machines[request.ident]
        except KeyError as e:
            logging.warning("Server: start transfer is from unknown remote: %s" % e)
            return

        try:
            op = self.remote_machines[request.ident].lookup_op(request.timestamp)
        except KeyError as e:
            logging.warning("Server: start transfer for unknowns op: %s" % e)
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
                op.set_status(OpStatus.FAILED_UNRECOVERABLE)
            elif op.file_send_cancellable.is_set():
                logging.debug("Server: file send cancelled")
            else:
                logging.debug("Server: transfer of %s files (%s) finished in %s" % \
                    (op.total_count, GLib.format_size(op.total_size),\
                     util.precise_format_time_span(GLib.get_monotonic_time() - start_time)))

        context.add_callback(transfer_done)
        return sender.read_chunks()

    def StopTransfer(self, request, context):
        logging.debug("Server RPC: StopTransfer from '%s'" % request.info.readable_name)

        try:
            op = self.remote_machines[request.info.ident].lookup_op(request.info.timestamp)
        except KeyError as e:
            logging.warning("Server: stop transfer was for unknown op: %s" % e)
            return

        # If we receive this call, this means the op was stopped remotely.  So,
        # our op with TO_REMOTE_MACHINE (we initiated it) was cancelled by the recipient.

        if request.error:
            op.error_msg = _("An error occurred on the remote machine")

        if op.direction == TransferDirection.TO_REMOTE_MACHINE:
            if op.file_send_cancellable != None:
                op.file_send_cancellable.set()
            logging.debug("Server: sender received stop transfer by receiver: %s" % op.error_msg)
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
            logging.debug("Server: receiver received stop transfer by sender: %s" % op.error_msg)
            if op.error_msg == "":
                op.set_status(OpStatus.STOPPED_BY_SENDER)
            else:
                op.set_status(OpStatus.FAILED)

        return void

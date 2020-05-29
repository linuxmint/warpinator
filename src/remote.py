import time
import gettext
import threading
import logging

from gi.repository import GObject, GLib

import grpc
import warp_pb2
import warp_pb2_grpc

import prefs
import util
import transfers
import auth
from ops import SendOp, ReceiveOp
from util import TransferDirection, OpStatus, OpCommand, RemoteStatus

_ = gettext.gettext

#typedef
void = warp_pb2.VoidType()

CHANNEL_RETRY_WAIT_TIME = 30

DUPLEX_MAX_FAILURES = 10
DUPLEX_WAIT_PING_TIME = 1
CONNECTED_PING_TIME = 20

# client
class RemoteMachine(GObject.Object):
    __gsignals__ = {
        'machine-info-changed': (GObject.SignalFlags.RUN_LAST, None, ()),
        'ops-changed': (GObject.SignalFlags.RUN_LAST, None, ()),
        'new-incoming-op': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'new-outgoing-op': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'focus-remote': (GObject.SignalFlags.RUN_LAST, None, ()),
        'remote-status-changed': (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self, ident, hostname, display_hostname, ip, port, local_ident):
        GObject.Object.__init__(self)
        self.ip_address = ip
        self.port = port
        self.ident = ident
        self.local_ident = local_ident
        self.hostname = hostname
        self.display_hostname = display_hostname
        self.user_name = ""
        self.display_name = ""
        self.favorite = prefs.get_is_favorite(self.ident)
        self.recent_time = 0 # Keep monotonic time when visited on the user page

        self.avatar_surface = None
        self.transfer_ops = []

        self.stub = None
        self.connected = False

        self.busy = False # Skip keepalive ping when we're busy.

        self.sort_key = self.hostname

        self.status = RemoteStatus.INIT_CONNECTING

        self.machine_info_changed_source_id = 0
        self.machine_info_changed_lock = threading.Lock()

        self.status_idle_source_id = 0
        self.status_lock = threading.Lock()

        self.ping_timer = threading.Event()

        prefs.prefs_settings.connect("changed::favorites", self.update_favorite_status)

        self.has_zc_presence = False # This is currently unused.

    def start_remote_thread(self):
        remote_thread = threading.Thread(target=self.run, name="remote-thread-%s-%s:%d-%s"
                                             % (self.hostname, self.ip_address, self.port, self.ident))
        # logging.debug("remote-thread-%s-%s:%d-%s"
                          # % (self.hostname, self.ip_address, self.port, self.ident))
        remote_thread.start()

    def run(self):
        self.ping_timer.clear()

        self.emit_machine_info_changed() # Let's make sure the button doesn't have junk in it if we fail to connect.

        logging.debug("== Attempting to connect to %s (%s)" % (self.display_hostname, self.ip_address))

        self.set_remote_status(RemoteStatus.INIT_CONNECTING)

        def run_secure_loop():
            logging.debug("Starting a new connection loop for %s (%s:%d)"
                              % (self.display_hostname, self.ip_address, self.port))

            cert = auth.get_singleton().load_cert(self.hostname, self.ip_address)
            creds = grpc.ssl_channel_credentials(cert)

            with grpc.secure_channel("%s:%d" % (self.ip_address, self.port), creds) as channel:
                future = grpc.channel_ready_future(channel)

                try:
                    future.result(timeout=4)
                    self.stub = warp_pb2_grpc.WarpStub(channel)
                    self.connected = True
                except grpc.FutureTimeoutError:
                    self.set_remote_status(RemoteStatus.UNREACHABLE)
                    future.cancel()

                    if not self.ping_timer.is_set():
                        logging.debug("Unable to establish secure connection with %s (%s:%d). Trying again in %ds"
                                          % (self.display_hostname, self.ip_address, self.port, CHANNEL_RETRY_WAIT_TIME))
                        self.ping_timer.wait(CHANNEL_RETRY_WAIT_TIME)
                        return True # run_secure_loop()

                    return False # run_secure_loop()

                duplex_fail_counter = 0
                one_ping = False # A successful duplex response lets us finish setting things up.

                while not self.ping_timer.is_set():

                    if self.busy:
                        logging.debug("Skipping keepalive ping to %s (%s:%d) (busy)"
                                          % (self.display_hostname, self.ip_address, self.port))
                        self.busy = False
                    else:
                        try:
                            logging.debug("Sending keepalive ping to %s (%s:%d)"
                                          % (self.display_hostname, self.ip_address, self.port))
                            self.stub.Ping(warp_pb2.LookupName(id=self.local_ident,
                                                               readable_name=util.get_hostname()),
                                           timeout=5)
                            if not one_ping:
                                self.set_remote_status(RemoteStatus.AWAITING_DUPLEX)
                                if self.check_duplex_connection():
                                    logging.debug("++ Connected to %s (%s:%d)"
                                                      % (self.display_hostname, self.ip_address, self.port))

                                    self.set_remote_status(RemoteStatus.ONLINE)

                                    self.rpc_call(self.update_remote_machine_info)
                                    self.rpc_call(self.update_remote_machine_avatar)
                                    one_ping = True
                                else:
                                    duplex_fail_counter += 1
                                    if duplex_fail_counter > DUPLEX_MAX_FAILURES:
                                        logging.debug("CheckDuplexConnection to %s (%s:%d) failed too many times"
                                                          % (self.display_hostname, self.ip_address, self.port))
                                        self.ping_timer.wait(CHANNEL_RETRY_WAIT_TIME)
                                        return True
                        except grpc.RpcError as e:
                            logging.debug("Ping failed, shutting down %s (%s:%d)"
                                              % (self.display_hostname, self.ip_address, self.port))
                            break

                    self.ping_timer.wait(CONNECTED_PING_TIME if self.status == RemoteStatus.ONLINE else DUPLEX_WAIT_PING_TIME)

                # This is reached by the RpcError break above.  If the remote is still discoverable, start
                # the secure loop over.  This could have happened as a result of a quick disco/reconnect,
                # And we don't notice until it has already come back. In this case, try a new connection.
                if self.has_zc_presence and not self.ping_timer.is_set():
                    return True # run_secure_loop()

                # The ping timer has been triggered, this is an orderly shutdown.
                return False # run_secure_loop()

        try:
            while run_secure_loop():
                continue
        except Exception as e:
            logging.critical("!! Major problem starting connection loop for %s (%s:%d): %s"
                                 % (self.display_hostname, self.ip_address, self.port, e))

        self.set_remote_status(RemoteStatus.OFFLINE)
        self.connected = False

    def shutdown(self):
        self.ping_timer.set()
        while self.connected:
            time.sleep(0.1)

    def update_favorite_status(self, pspec, data=None):
        old_favorite = self.favorite
        self.favorite = prefs.get_is_favorite(self.ident)

        if old_favorite != self.favorite:
            self.emit_machine_info_changed()

    def stamp_recent_time(self):
        self.recent_time = GLib.get_monotonic_time()
        self.emit_machine_info_changed()

    def set_remote_status(self, status):
        with self.status_lock:
            if self.status_idle_source_id > 0:
                GLib.source_remove(self.status_idle_source_id)

            self.status_idle_source_id = GLib.idle_add(self.set_status_cb, status)

    def set_status_cb(self, status):
        with self.status_lock:
            self.status_idle_source_id = 0

            if status == self.status:
                return GLib.SOURCE_REMOVE

            self.status = status
            self.cancel_ops_if_offline()

            logging.debug("** %s is now %s" % (self.hostname, self.status))
            self.emit("remote-status-changed")

        return GLib.SOURCE_REMOVE

    def emit_machine_info_changed(self):
        with self.machine_info_changed_lock:
            if self.machine_info_changed_source_id > 0:
                GLib.source_remove(self.machine_info_changed_source_id)

            self.machine_info_changed_source_id = GLib.idle_add(self.emit_machine_info_changed_cb)

    def emit_machine_info_changed_cb(self):
        with self.machine_info_changed_lock:
            self.machine_info_changed_source_id = 0
            self.emit("machine-info-changed")

        return GLib.SOURCE_REMOVE

    def rpc_call(self, func, *args, **kargs):
        try:
            util.global_rpc_threadpool.submit(func, *args, **kargs)
        except Exception as e:
            # exception concurrent.futures.thread.BrokenThreadPool is not available in bionic/python3 < 3.7
            logging.critical("!! RPC threadpool failure while submitting call to %s (%s:%d): %s"
                                 % (self.display_hostname, self.ip_address, self.port, e))

    # Not added to thread pool
    def check_duplex_connection(self):
        logging.debug("Checking duplex with '%s'" % self.display_hostname)

        ret = self.stub.CheckDuplexConnection(warp_pb2.LookupName(id=self.local_ident,
                                                                  readable_name=util.get_hostname()))

        return ret.response

    # Run in thread pool
    def update_remote_machine_info(self):
        logging.debug("Calling GetRemoteMachineInfo on '%s'" % self.display_hostname)
        def get_info_finished(future):
            info = future.result()
            self.display_name = info.display_name
            self.user_name = info.user_name
            self.favorite = prefs.get_is_favorite(self.ident)

            valid = GLib.utf8_make_valid(self.display_name, -1)
            self.sort_key = GLib.utf8_collate_key(valid.lower(), -1)

            self.emit_machine_info_changed()
            self.set_remote_status(RemoteStatus.ONLINE)
        
        future = self.stub.GetRemoteMachineInfo.future(warp_pb2.LookupName(id=self.local_ident,
                                                                           readable_name=util.get_hostname()))
        future.add_done_callback(get_info_finished)

    # Run in thread pool
    def update_remote_machine_avatar(self):
        logging.debug("Calling GetRemoteMachineAvatar on '%s'" % self.display_hostname)
        iterator = self.stub.GetRemoteMachineAvatar(warp_pb2.LookupName(id=self.local_ident,
                                                                        readable_name=util.get_hostname()))
        loader = None
        try:
            for info in iterator:
                if loader == None:
                    loader = util.CairoSurfaceLoader()
                loader.add_bytes(info.avatar_chunk)
        except grpc.RpcError as e:
            logging.debug("Could not fetch remote avatar, using a generic one. (%s, %s)" % (e.code(), e.details()))

        self.get_avatar_surface(loader)

    @util._idle
    def get_avatar_surface(self, loader=None):
        # This needs to be on the main loop, or else we get an x error
        if loader:
            self.avatar_surface = loader.get_surface()
        else:
            self.avatar_surface = None

        self.emit_machine_info_changed()

    # Run in thread pool
    def send_transfer_op_request(self, op):
        if not self.stub: # short circuit for testing widgets
            return

        logging.debug("Calling TransferOpRequest on '%s'" % (self.display_hostname))

        transfer_op = warp_pb2.TransferOpRequest(info=warp_pb2.OpInfo(ident=op.sender,
                                                                      timestamp=op.start_time,
                                                                      readable_name=util.get_hostname()),
                                                 sender_name=op.sender_name,
                                                 receiver=self.ident,
                                                 size=op.total_size,
                                                 count=op.total_count,
                                                 name_if_single=op.description,
                                                 mime_if_single=op.mime_if_single,
                                                 top_dir_basenames=op.top_dir_basenames)
        self.stub.ProcessTransferOpRequest(transfer_op)

    # Run in thread pool
    def cancel_transfer_op_request(self, op, by_sender=False):
        logging.debug("Calling CancelTransferOpRequest on '%s'" % (self.display_hostname))

        if op.direction == TransferDirection.TO_REMOTE_MACHINE:
            name = op.sender
        else:
            name = self.local_ident
        self.stub.CancelTransferOpRequest(warp_pb2.OpInfo(timestamp=op.start_time,
                                                          ident=name,
                                                          readable_name=util.get_hostname()))
        op.set_status(OpStatus.CANCELLED_PERMISSION_BY_SENDER if by_sender else OpStatus.CANCELLED_PERMISSION_BY_RECEIVER)

    # Run in thread pool
    def start_transfer_op(self, op):
        logging.debug("Calling StartTransfer on '%s'" % (self.display_hostname))

        start_time = GLib.get_monotonic_time()

        op.progress_tracker = transfers.OpProgressTracker(op)
        op.current_progress_report = None
        receiver = transfers.FileReceiver(op)
        op.set_status(OpStatus.TRANSFERRING)

        op.file_iterator = self.stub.StartTransfer(warp_pb2.OpInfo(timestamp=op.start_time,
                                                                   ident=self.local_ident,
                                                                   readable_name=util.get_hostname()))

        def report_receive_error(error):
            op.set_error(error)

            try:
                # If we leave an io stream open, it locks the location.  For instance,
                # if this was a mounted location, we wouldn't be able to terminate until
                # we closed warp.
                receiver.current_stream.close()
            except GLib.Error:
                pass

            logging.critical("An error occurred receiving data from %s: %s" % (op.sender, op.error_msg))
            op.set_status(OpStatus.FAILED)
            op.stop_transfer()

        try:
            for data in op.file_iterator:
                receiver.receive_data(data)
        except grpc.RpcError:
            if op.file_iterator.code() == grpc.StatusCode.CANCELLED:
                op.file_iterator = None
                return
            else:
                report_receive_error(op.file_iterator)
                return
        except Exception as e:
            report_receive_error(e)
            return

        op.file_iterator = None
        receiver.receive_finished()

        logging.debug("Receipt of %s files (%s) finished in %s" % \
              (op.total_count, GLib.format_size(op.total_size),\
               util.precise_format_time_span(GLib.get_monotonic_time() - start_time)))

        op.set_status(OpStatus.FINISHED)

    # Run in thread pool
    def stop_transfer_op(self, op, by_sender=False, lost_connection=False):
        logging.debug("Calling StopTransfer on '%s'" % (self.display_hostname))

        if op.direction == TransferDirection.TO_REMOTE_MACHINE:
            name = op.sender
        else:
            name = self.local_ident

        if by_sender:
            op.file_send_cancellable.set()
            # If we stopped due to connection error, we don't want the message to be 'stopped by xx',
            # but just failed.
            if not lost_connection:
                logging.debug("stop transfer initiated by sender")
                if op.error_msg == "":
                    op.set_status(OpStatus.STOPPED_BY_SENDER)
                else:
                    op.set_status(OpStatus.FAILED)
        else:
            if op.file_iterator:
                op.file_iterator.cancel()
            if not lost_connection:
                logging.debug("stop transfer initiated by receiver")
                if op.error_msg == "":
                    op.set_status(OpStatus.STOPPED_BY_RECEIVER)
                else:
                    op.set_status(OpStatus.FAILED)

        if not lost_connection:
            # We don't need to send this if it's a connection loss, the other end will handle
            # its own cleanup.
            opinfo = warp_pb2.OpInfo(timestamp=op.start_time,
                                     ident=name,
                                     readable_name=util.get_hostname())
            self.stub.StopTransfer(warp_pb2.StopInfo(info=opinfo, error=op.error_msg != ""))

    # Op handling (run in thread pool)
    def send_files(self, uri_list):
        def _send_files(uri_list):
            op = SendOp(self.local_ident,
                        self.ident,
                        self.display_name,
                        uri_list)
            self.add_op(op)
            op.prepare_send_info()

        self.rpc_call(_send_files, uri_list)

    @util._idle
    def add_op(self, op):
        if op not in self.transfer_ops:
            self.transfer_ops.append(op)
            op.connect("status-changed", self.emit_ops_changed)
            op.connect("op-command", self.op_command_issued)
            op.connect("focus", self.op_focus)
            if isinstance(op, SendOp):
                op.connect("initial-setup-complete", self.notify_remote_machine_of_new_op)
                self.emit("new-outgoing-op", op)
            if isinstance(op, ReceiveOp):
                self.emit("new-incoming-op", op)

        def set_busy():
            self.busy = True

        op.connect("active", lambda op: set_busy())

        self.emit_ops_changed()
        self.check_for_autostart(op)

    @util._idle
    def notify_remote_machine_of_new_op(self, op):
        if op.status == OpStatus.WAITING_PERMISSION:
            if op.direction == TransferDirection.TO_REMOTE_MACHINE:
                self.rpc_call(self.send_transfer_op_request, op)

    @util._idle
    def check_for_autostart(self, op):
        if op.status == OpStatus.WAITING_PERMISSION:
            if isinstance(op, ReceiveOp) and \
              op.have_space  and not op.existing and (not prefs.require_permission_for_transfer()):
                op.accept_transfer()

    def remove_op(self, op):
        self.transfer_ops.remove(op)
        self.emit_ops_changed()

    @util._idle
    def emit_ops_changed(self, op=None):
        self.emit("ops-changed")

    def cancel_ops_if_offline(self):
        if self.status in (RemoteStatus.OFFLINE, RemoteStatus.UNREACHABLE):
            for op in self.transfer_ops:
                if op.status == OpStatus.TRANSFERRING:
                    op.error_msg = _("Connection has been lost")
                    self.rpc_call(self.stop_transfer_op, op, isinstance(op, SendOp), lost_connection=True)
                    op.set_status(OpStatus.FAILED)
                elif op.status in (OpStatus.WAITING_PERMISSION, OpStatus.CALCULATING, OpStatus.PAUSED):
                    op.error_msg = _("Connection has been lost")
                    op.set_status(OpStatus.FAILED_UNRECOVERABLE)

    @util._idle
    def op_command_issued(self, op, command):
        # send
        if command == OpCommand.CANCEL_PERMISSION_BY_SENDER:
            self.rpc_call(self.cancel_transfer_op_request, op, by_sender=True)
        # elif command == OpCommand.PAUSE_TRANSFER:
            # self.rpc_call(self.pause_transfer_op, op)
        elif command == OpCommand.STOP_TRANSFER_BY_SENDER:
            self.rpc_call(self.stop_transfer_op, op, by_sender=True)
        elif command == OpCommand.RETRY_TRANSFER:
            op.set_status(OpStatus.WAITING_PERMISSION)
            self.rpc_call(self.send_transfer_op_request, op)
        elif command == OpCommand.REMOVE_TRANSFER:
            self.remove_op(op)
        # receive
        elif command == OpCommand.START_TRANSFER:
            self.rpc_call(self.start_transfer_op, op)
        elif command == OpCommand.CANCEL_PERMISSION_BY_RECEIVER:
            self.rpc_call(self.cancel_transfer_op_request, op, by_sender=False)
        elif command == OpCommand.STOP_TRANSFER_BY_RECEIVER:
            self.rpc_call(self.stop_transfer_op, op, by_sender=False)

    @util._idle
    def op_focus(self, op):
        self.emit("focus-remote")

    def lookup_op(self, timestamp):
        for op in self.transfer_ops:
            if op.start_time == timestamp:
                return op

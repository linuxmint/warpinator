#!/usr/bin/python3

import time
import gettext
import threading
import logging
import socket

from gi.repository import GObject, GLib

import grpc
import warp_pb2
import warp_pb2_grpc

import interceptors
import prefs
import util
import misc
import transfers
import auth
from ops import SendOp, ReceiveOp, TextMessageOp
from util import TransferDirection, OpStatus, OpCommand, RemoteStatus, ReceiveError, RemoteFeatures

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

    def __init__(self, ident, hostname, display_hostname, ip_info, port, local_ident, api_version):
        GObject.Object.__init__(self)
        self.ip_info = ip_info
        self.port = port
        self.ident = ident
        self.local_ident = local_ident
        self.api_version = api_version
        self.hostname = hostname
        self.display_hostname = display_hostname
        self.user_name = ""
        self.display_name = ""
        self.favorite = prefs.get_is_favorite(self.ident)
        self.recent_time = 0 # Keep monotonic time when visited on the user page
        self.supports_messages = False

        self.avatar_surface = None
        self.transfer_ops = []

        self.sort_key = self.hostname
        self.status = RemoteStatus.INIT_CONNECTING

        self.machine_info_changed_source_id = 0
        self.machine_info_changed_lock = threading.Lock()

        self.status_idle_source_id = 0
        self.status_lock = threading.Lock()

        self.stub = None

        self.busy = False # Skip keepalive ping when we're busy.
        self.ping_timer = threading.Event()

        self.channel_keepalive = threading.Event()

        prefs.prefs_settings.connect("changed::favorites", self.update_favorite_status)

        self.has_zc_presence = False # This is currently unused.

        self.last_register = 0

    def start_remote_thread(self):
        # func = lambda: return

        if self.api_version == "1":
            func = self.remote_thread_v1
        elif self.api_version == "2":
            func = self.remote_thread_v2

        self.remote_thread = threading.Thread(target=func, name="remote-main-thread-v%s-%s-%s:%d-%s"
                                              % (self.api_version, self.hostname, self.ip_info.ip4_address, self.port, self.ident))
        # logging.debug("remote-thread-%s-%s:%d-%s"
                          # % (self.hostname, self.ip_info.ip4_address, self.port, self.ident))
        self.remote_thread.start()

    def remote_thread_v1(self):
        self.ping_timer.clear()

        self.emit_machine_info_changed() # Let's make sure the button doesn't have junk in it if we fail to connect.

        logging.debug("Remote: Attempting to connect to %s (%s) - api version 1" % (self.display_hostname, self.ip_info.ip4_address))

        self.set_remote_status(RemoteStatus.INIT_CONNECTING)

        def run_secure_loop():
            logging.debug("Remote: Starting a new connection loop for %s (%s:%d)"
                              % (self.display_hostname, self.ip_info, self.port))

            cert = auth.get_singleton().get_cached_cert(self.hostname, self.ip_info)
            creds = grpc.ssl_channel_credentials(cert)

            with grpc.secure_channel("%s:%d" % (self.ip_info.ip4_address, self.port), creds) as channel:
                future = grpc.channel_ready_future(channel)

                try:
                    future.result(timeout=4)
                    self.stub = warp_pb2_grpc.WarpStub(channel)
                except grpc.FutureTimeoutError:
                    self.set_remote_status(RemoteStatus.UNREACHABLE)
                    future.cancel()

                    if not self.ping_timer.is_set():
                        logging.debug("Remote: Unable to establish secure connection with %s (%s:%d). Trying again in %ds"
                                          % (self.display_hostname, self.ip_info, self.port, CHANNEL_RETRY_WAIT_TIME))
                        self.ping_timer.wait(CHANNEL_RETRY_WAIT_TIME)
                        return True # run_secure_loop()

                    return False # run_secure_loop()

                duplex_fail_counter = 0
                one_ping = False # A successful duplex response lets us finish setting things up.

                while not self.ping_timer.is_set():

                    if self.busy:
                        logging.debug("Remote Ping: Skipping keepalive ping to %s (%s:%d) (busy)"
                                          % (self.display_hostname, self.ip_info, self.port))
                        self.busy = False
                    else:
                        try:
                            # t = GLib.get_monotonic_time()
                            logging.debug("Remote Ping: to   %s (%s:%d)"
                                          % (self.display_hostname, self.ip_info, self.port))
                            self.stub.Ping(warp_pb2.LookupName(id=self.local_ident,
                                                               readable_name=util.get_hostname()),
                                           timeout=5)
                            # logging.debug("Latency: %s (%s)"
                                          # % (util.precise_format_time_span(GLib.get_monotonic_time() - t), self.display_hostname))
                            if not one_ping:
                                self.set_remote_status(RemoteStatus.AWAITING_DUPLEX)
                                if self.check_duplex_connection():
                                    logging.debug("Remote: Connected to %s (%s:%d)"
                                                      % (self.display_hostname, self.ip_info, self.port))

                                    self.set_remote_status(RemoteStatus.ONLINE)

                                    self.rpc_call(self.update_remote_machine_info)
                                    self.rpc_call(self.update_remote_machine_avatar)
                                    one_ping = True
                                else:
                                    duplex_fail_counter += 1
                                    if duplex_fail_counter > DUPLEX_MAX_FAILURES:
                                        logging.debug("Remote: CheckDuplexConnection to %s (%s:%d) failed too many times"
                                                          % (self.display_hostname, self.ip_info, self.port))
                                        self.ping_timer.wait(CHANNEL_RETRY_WAIT_TIME)
                                        return True
                        except grpc.RpcError as e:
                            logging.debug("Remote: Ping failed, shutting down %s (%s:%d)"
                                              % (self.display_hostname, self.ip_info, self.port))
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
                                 % (self.display_hostname, self.ip_info, self.port, e))

        self.set_remote_status(RemoteStatus.OFFLINE)
        self.run_thread_alive = False

    def remote_thread_v2(self):
        self.channel_keepalive.clear()

        self.emit_machine_info_changed() # Let's make sure the button doesn't have junk in it if we fail to connect.

        remote_ip, _, ip_version = self.ip_info.get_usable_ip()
        logging.debug("Remote: Attempting to connect to %s (%s) - api version 2" % (self.display_hostname, remote_ip))
        remote_ip = remote_ip if ip_version == socket.AF_INET else "[%s]" % (remote_ip,)

        self.set_remote_status(RemoteStatus.INIT_CONNECTING)

        cert = auth.get_singleton().get_cached_cert(self.hostname, self.ip_info)
        creds = grpc.ssl_channel_credentials(cert)

        def run_secure_loop():
            opts = (
                ('grpc.keepalive_time_ms', 10000),
                ('grpc.keepalive_timeout_ms', 5000),
                ('grpc.keepalive_permit_without_calls', True),
                ('grpc.http2.max_pings_without_data', 0),
                ('grpc.http2.min_time_between_pings_ms', 10000),
                ('grpc.http2.min_ping_interval_without_data_ms', 5000)
            )

            with grpc.secure_channel("%s:%d" % (remote_ip, self.port), creds, options=opts) as channel:

                def channel_state_changed(state):
                    if state != grpc.ChannelConnectivity.READY:
                        # The server may have already called shutdown
                        try:
                            self.shutdown()
                        except:
                            pass

                intercepted_channel = grpc.intercept_channel(channel,
                                                             interceptors.ChunkDecompressor())

                future = grpc.channel_ready_future(intercepted_channel)

                try:
                    future.result(timeout=4)
                    channel.subscribe(channel_state_changed)
                    self.stub = warp_pb2_grpc.WarpStub(intercepted_channel)

                    self.set_remote_status(RemoteStatus.AWAITING_DUPLEX)

                    duplex = self.wait_for_duplex()
                    duplex.result(timeout=10)

                    self.set_remote_status(RemoteStatus.ONLINE)

                    self.rpc_call(self.update_remote_machine_info)
                    self.rpc_call(self.update_remote_machine_avatar)

                    # Online loop
                    logging.info("Connected to %s" % self.display_hostname)
                    while not self.channel_keepalive.is_set():
                        self.channel_keepalive.wait(.5)
                    ##

                except Exception as e:
                    self.set_remote_status(RemoteStatus.UNREACHABLE)

                    if isinstance(e, grpc.FutureTimeoutError):
                        future.cancel()
                        logging.critical("Problem while waiting for channel - api version 2: %s" % e)
                    elif isinstance(e, grpc.RpcError):
                        logging.critical("Problem while awaiting duplex response - api version 2: %s - %s" % (e.code(), e.details()))
                    else:
                        logging.critical("General error with remote channel connection - api version 2: %s" % e)

                    self.channel_keepalive.wait(10)
                finally:
                    channel.unsubscribe(channel_state_changed)

        while not self.channel_keepalive.is_set():
            run_secure_loop()

        self.set_remote_status(RemoteStatus.OFFLINE)

    def shutdown(self):
        if self.api_version == "1":
            self.ping_timer.set()
        else:
            self.channel_keepalive.set()
        # This is called by server just before running start_remote_thread, so the first time
        # self.remote_thread will be None.
        try:
            self.remote_thread.join(10)
        except AttributeError:
            pass

        self.remote_thread = None

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

            logging.debug("Remote: %s is now %s ****" % (self.hostname, RemoteStatus(self.status).name))
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
                                 % (self.display_hostname, self.ip_info, self.port, e))

    # Not added to thread pool
    def check_duplex_connection(self):
        logging.debug("Remote: checking duplex with '%s'" % self.display_hostname)

        ret = self.stub.CheckDuplexConnection(warp_pb2.LookupName(id=self.local_ident,
                                                                  readable_name=util.get_hostname()))

        return ret.response

    def wait_for_duplex(self):
        logging.debug("Remote: waiting for duplex from '%s'" % self.display_hostname)

        future = self.stub.WaitingForDuplex.future(warp_pb2.LookupName(id=self.local_ident,
                                                                       readable_name=util.get_hostname()))

        return future

    # Run in thread pool
    def update_remote_machine_info(self):
        logging.debug("Remote RPC: calling GetRemoteMachineInfo on '%s'" % self.display_hostname)
        def get_info_finished(future):
            info = future.result()
            self.display_name = info.display_name
            self.user_name = info.user_name
            feature_flags = RemoteFeatures(info.feature_flags)
            self.supports_messages = RemoteFeatures.TEXT_MESSAGES in feature_flags
            self.favorite = prefs.get_is_favorite(self.ident)

            valid = GLib.utf8_make_valid(self.display_name, -1)
            self.sort_key = GLib.utf8_collate_key(valid.lower(), -1)

            self.emit_machine_info_changed()
            self.set_remote_status(RemoteStatus.ONLINE)
        
        future = self.stub.GetRemoteMachineInfo.future(
            warp_pb2.LookupName(
                id=self.local_ident,
                readable_name=util.get_hostname()
            )
        )
        future.add_done_callback(get_info_finished)

    # Run in thread pool
    def update_remote_machine_avatar(self):
        logging.debug("Remote RPC: calling GetRemoteMachineAvatar on '%s'" % self.display_hostname)
        iterator = self.stub.GetRemoteMachineAvatar(
            warp_pb2.LookupName(
                id=self.local_ident,
                readable_name=util.get_hostname()
            )
        )
        loader = None
        try:
            for info in iterator:
                if loader is None:
                    loader = util.CairoSurfaceLoader()
                loader.add_bytes(info.avatar_chunk)
        except grpc.RpcError as e:
            logging.debug("Remote RPC: could not fetch remote avatar, using a generic one. (%s, %s)" % (e.code(), e.details()))

        self.get_avatar_surface(loader)

    @misc._idle
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

        logging.debug("Remote RPC: calling TransferOpRequest on '%s'" % (self.display_hostname))

        transfer_op = warp_pb2.TransferOpRequest(
            info=warp_pb2.OpInfo(
                ident=op.sender,
                timestamp=op.start_time,
                readable_name=util.get_hostname(),
                use_compression=prefs.use_compression(),
            ),
            sender_name=op.sender_name,
            receiver=self.ident,
            size=op.total_size,
            count=op.total_count,
            name_if_single=op.description,
            mime_if_single=op.mime_if_single,
            top_dir_basenames=op.top_dir_basenames
        )

        self.stub.ProcessTransferOpRequest(transfer_op)

    # Run in thread pool
    def cancel_transfer_op_request(self, op, by_sender=False):
        logging.debug("Remote RPC: calling CancelTransferOpRequest on '%s'" % (self.display_hostname))

        if op.direction == TransferDirection.TO_REMOTE_MACHINE:
            name = op.sender
        else:
            name = self.local_ident
        self.stub.CancelTransferOpRequest(
            warp_pb2.OpInfo(
                timestamp=op.start_time,
                ident=name,
                readable_name=util.get_hostname()
            )
        )
        op.set_status(OpStatus.CANCELLED_PERMISSION_BY_SENDER if by_sender else OpStatus.CANCELLED_PERMISSION_BY_RECEIVER)

    # Run in thread pool
    def start_transfer_op(self, op):
        logging.debug("Remote RPC: calling StartTransfer on '%s'" % (self.display_hostname))

        start_time = GLib.get_monotonic_time()

        op.progress_tracker = transfers.OpProgressTracker(op)
        op.current_progress_report = None
        receiver = transfers.FileReceiver(op)
        op.set_status(OpStatus.TRANSFERRING)

        # This is ugly because StartTransfer only returns file_iterator. The
        # interceptor returns the cancellable with it, because file_iterator
        # is not a future if compression is active, it's just a generator.
        op.file_iterator = self.stub.StartTransfer(
            warp_pb2.OpInfo(
                timestamp=op.start_time,
                ident=self.local_ident,
                readable_name=util.get_hostname(),
                use_compression=op.use_compression and prefs.use_compression()
            )
        )

        def report_receive_error(error):
            op.file_iterator = None

            # Get rid of any toplevel file/folder if the transfer stops prematurely,
            # so it or its children 
            receiver.clean_current_top_dir_file()

            if error is None:
                return

            op.set_error(error)

            try:
                # If we leave an io stream open, it locks the location.  For instance,
                # if this was a mounted location, we wouldn't be able to terminate until
                # we closed warp.
                if receiver.current_stream is not None:
                    receiver.current_stream.close()
            except GLib.Error:
                pass

            logging.critical("An error occurred receiving data from %s: %s" % (op.sender, op.error_msg))
            op.set_status(OpStatus.FAILED)
            op.stop_transfer()

        try:
            receiver.clean_existing_files()

            for data in op.file_iterator:
                receiver.receive_data(data)

            op.file_iterator = None
            receiver.receive_finished()

            logging.debug("Remote: receipt of %s files (%s) finished in %s" % \
                          (op.total_count, GLib.format_size(op.total_size),\
                           util.precise_format_time_span(GLib.get_monotonic_time() - start_time)))

            if op.remaining_count > 0:
                raise ReceiveError("Transfer completed, but the number of files received is less than the original request size (expected %d, received %d)"
                                       % (op.total_count, op.total_count - op.remaining_count),
                                   fatal=False)
            op.set_status(OpStatus.FINISHED)
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.CANCELLED:
                report_receive_error(None)
            else:
                report_receive_error(e)
        except ReceiveError as e:
            if e.fatal:
                report_receive_error(e)
            else:
                logging.critical(str(e))
                op.set_error(e)
                op.set_status(OpStatus.FINISHED_WARNING)
        except Exception as e:
            report_receive_error(e)

    # Run in thread pool
    def stop_transfer_op(self, op, by_sender=False, lost_connection=False):
        logging.debug("Remote RPC: Calling StopTransfer on '%s'" % (self.display_hostname))

        if op.direction == TransferDirection.TO_REMOTE_MACHINE:
            name = op.sender
        else:
            name = self.local_ident

        if by_sender:
            op.file_send_cancellable.set()
            # If we stopped due to connection error, we don't want the message to be 'stopped by xx',
            # but just failed.
            if not lost_connection:
                logging.debug("Remote: stop transfer initiated by sender")
                if op.error_msg == "":
                    op.set_status(OpStatus.STOPPED_BY_SENDER)
                else:
                    op.set_status(OpStatus.FAILED)
        else:
            if op.file_iterator:
                op.file_iterator.cancel()
            if not lost_connection:
                logging.debug("Remote: stop transfer initiated by receiver")
                if op.error_msg == "":
                    op.set_status(OpStatus.STOPPED_BY_RECEIVER)
                else:
                    op.set_status(OpStatus.FAILED)

        if not lost_connection:
            # We don't need to send this if it's a connection loss, the other end will handle
            # its own cleanup.
            opinfo = warp_pb2.OpInfo(
                timestamp=op.start_time,
                ident=name,
                readable_name=util.get_hostname()
            )
            self.stub.StopTransfer(warp_pb2.StopInfo(info=opinfo, error=op.error_msg != ""))

    # Op handling (run in thread pool)
    def send_files(self, uri_list, dbus_sent=False):
        def _send_files(uri_list):
            op = SendOp(
                self.local_ident,
                self.ident,
                self.display_name,
                uri_list
            )
            op.dbus_op = dbus_sent
            self.add_op(op)
            op.prepare_send_info()

        util.add_to_recents_if_single_selection(uri_list)
        self.rpc_call(_send_files, uri_list)

    def send_text_message(self, message):
        op = TextMessageOp(TransferDirection.TO_REMOTE_MACHINE, self.local_ident)
        op.message = message
        op.status = OpStatus.FINISHED
        self.add_op(op)
        self.rpc_call(self.do_send_text_message, op)

    def do_send_text_message(self, op):
        try:
            self.stub.SendTextMessage(warp_pb2.TextMessage(ident=self.local_ident, timestamp=op.start_time, message=op.message))
        except Exception as e:
            logging.error("Sending message failed: %s" % e)
            op.status = OpStatus.FAILED
            op.emit_status_changed()

    @misc._idle
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

        # For now, only bad base filenames cause this (failed util.test_resolved_path_safety())
        # We let it get this far so the UI has something to show the user.
        if op.status == OpStatus.FAILED_UNRECOVERABLE:
            op.decline_transfer_request()
            return

        self.check_for_autostart(op)

    @misc._idle
    def notify_remote_machine_of_new_op(self, op):
        if op.status == OpStatus.WAITING_PERMISSION:
            if op.direction == TransferDirection.TO_REMOTE_MACHINE:
                self.rpc_call(self.send_transfer_op_request, op)

    @misc._idle
    def check_for_autostart(self, op):
        if op.status == OpStatus.WAITING_PERMISSION:
            if isinstance(op, ReceiveOp) and \
              op.have_space and \
              (not (op.existing and prefs.prevent_overwriting())) and \
              (not prefs.require_permission_for_transfer()):
                op.accept_transfer()

    def remove_op(self, op):
        self.transfer_ops.remove(op)
        self.emit_ops_changed()

    @misc._idle
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

    @misc._idle
    def op_command_issued(self, op, command):
        # send
        if command == OpCommand.CANCEL_PERMISSION_BY_SENDER:
            self.rpc_call(self.cancel_transfer_op_request, op, by_sender=True)
        # elif command == OpCommand.PAUSE_TRANSFER:
            # self.rpc_call(self.pause_transfer_op, op)
        elif command == OpCommand.STOP_TRANSFER_BY_SENDER:
            self.rpc_call(self.stop_transfer_op, op, by_sender=True)
        elif command == OpCommand.RETRY_TRANSFER:
            if isinstance(op, TextMessageOp):
                op.status = OpStatus.FINISHED
                op.emit_status_changed()
                self.rpc_call(self.do_send_text_message, op)
            else:
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

    @misc._idle
    def op_focus(self, op):
        self.emit("focus-remote")

    def lookup_op(self, timestamp):
        for op in self.transfer_ops:
            if op.start_time == timestamp:
                return op

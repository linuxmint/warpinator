#!/usr/bin/python3

import logging
import threading
import socket
from concurrent import futures

import grpc
import warp_pb2_grpc
import warp_pb2

import auth
import util
import prefs
import config

class RegRequest():
    def __init__(self, ident, hostname, ip_info, port, auth_port, api_version):
        self.api_version = api_version
        self.ident = ident
        self.hostname = hostname
        self.ip_info = ip_info
        self.port = port

        #v2 only
        self.auth_port = auth_port
        self.locked_cert = None

        self.cancelled = False

    def cancel(self):
        self.cancelled = True

class Registrar():
    def __init__(self, ip_info, port, auth_port):
        self.reg_server_v2 = None
        self.active_registrations = {}
        self.reg_lock = threading.Lock()

        self.ip_info = ip_info
        self.port = port
        self.auth_port = auth_port

        self.start_registration_servers()

    def start_registration_servers(self):
        if self.reg_server_v2 is not None:
            self.reg_server_v2.stop(grace=2).wait()
            self.reg_server_v2 = None

        logging.debug("Starting v2 registration server (%s) with auth port %d" % (self.ip_info, self.auth_port))
        self.reg_server_v2 = RegistrationServer_v2(self.ip_info, self.auth_port)

    def shutdown_registration_servers(self):
        with self.reg_lock:
            for key in self.active_registrations.keys():
                self.active_registrations[key].cancel()
            self.active_registrations = {}

        if self.reg_server_v2:
            logging.debug("Stopping v2 registration server.")
            self.reg_server_v2.stop()
            self.reg_server_v2 = None

    def register(self, ident, hostname, ip_info, port, auth_port, api_version):
        details = RegRequest(ident, hostname, ip_info, port, auth_port, api_version)
        with self.reg_lock:
            self.active_registrations[ident] = details

        # api v2
        ret = register_v2(details)

        with self.reg_lock:
            # shutdown_registration_servers may have been called on a different thread.
            try:
                del self.active_registrations[ident]
            except KeyError:
                pass

        return ret


####################### api v2


def register_v2(details):
    # This will block if the remote's warp udp port is closed, until either the port is unblocked
    # or we tell the auth object to shutdown, in which case the request timer will cancel and return
    # here immediately (with None)
    logging.debug("Registering with %s (%s:%d) - api version 2" % (details.hostname, details.ip_info, details.auth_port))

    success = None

    remote_thread = threading.Thread(target=register_with_remote_thread, args=(details,), name="remote-auth-thread-%s" % id)
    logging.debug("remote-registration-thread-%s-%s:%d-%s" % (details.hostname, details.ip_info, details.auth_port, details.ident))
    remote_thread.start()
    remote_thread.join()

    if details.locked_cert is not None and not details.cancelled:
        success = auth.get_singleton().process_remote_cert(details.hostname,
                                                           details.ip_info,
                                                           details.locked_cert)

    if success == util.CertProcessingResult.FAILURE:
        logging.debug("Unable to register with %s (%s:%d) - api version 2"
                             % (details.hostname, details.ip_info, details.auth_port))
    elif success == util.CertProcessingResult.CERT_INSERTED:
        logging.debug("Successfully registered with %s (%s:%d) - api version 2"
                             % (details.hostname, details.ip_info, details.auth_port))
    elif success == util.CertProcessingResult.CERT_UPDATED:
        logging.debug("Successfully updated registration with %s (%s:%d) - api version 2"
                             % (details.hostname, details.ip_info, details.auth_port))
    elif success == util.CertProcessingResult.CERT_UP_TO_DATE:
        logging.debug("Certificate already up to date, nothing to do for %s (%s:%d) - api version 2"
                             % (details.hostname, details.ip_info, details.auth_port))
    return success

def register_with_remote_thread(details):
    logging.debug("Remote: Attempting to register %s (%s)" % (details.hostname, details.ip_info))

    remote_ip, local_ip, ip_version = details.ip_info.get_usable_ip()
    remote_ip = remote_ip if ip_version == socket.AF_INET else "[%s]" % (remote_ip,)

    with grpc.insecure_channel("%s:%d" % (remote_ip, details.auth_port)) as channel:
        future = grpc.channel_ready_future(channel)

        try:
            # future.result(timeout=5)
            stub = warp_pb2_grpc.WarpRegistrationStub(channel)

            ret = stub.RequestCertificate(warp_pb2.RegRequest(ip=remote_ip, hostname=util.get_hostname()),
                                          timeout=5)
            details.locked_cert = ret.locked_cert.encode("utf-8")
        except Exception as e:
            future.cancel()
            logging.critical("Problem with remote registration thread: %s (%s:%d) - api version 2: %s"
                     % (details.hostname, details.ip_info, details.auth_port, e))

class RegistrationServer_v2():
    def __init__(self, ip_info, auth_port):
        self.exit = False
        self.ip_info = ip_info
        self.auth_port = auth_port

        self.server = None
        self.server_thread_keepalive = threading.Event()

        self.thread = threading.Thread(target=self.serve_cert_thread)
        self.thread.start()

    def serve_cert_thread(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        warp_pb2_grpc.add_WarpRegistrationServicer_to_server(self, self.server)

        if self.ip_info.ip4_address is not None:
            self.server.add_insecure_port('%s:%d' % (self.ip_info.ip4_address, self.auth_port))
        if self.ip_info.ip6_address is not None:
            self.server.add_insecure_port('[%s]:%d' % (self.ip_info.ip6_address, self.auth_port))
        self.server.start()

        while not self.server_thread_keepalive.is_set():
            self.server_thread_keepalive.wait(10)

        logging.debug("Registration Server v2 stopping")
        self.server.stop(grace=2).wait()
        logging.debug("Registration Server v2 stopped")

    def stop(self):
        self.server_thread_keepalive.set()
        self.thread.join()

    def RequestCertificate(self, request, context):
        logging.debug("Registration Server RPC: RequestCertificate from %s '%s'" % (request.hostname, request.ip))

        return warp_pb2.RegResponse(locked_cert=auth.get_singleton().get_encoded_local_cert())
    
    def RegisterService(self, reg:warp_pb2.ServiceRegistration, context):
        logging.debug("Received manual registration from " + reg.service_id)
        self.service_registration_handler(reg)
        return warp_pb2.ServiceRegistration(service_id=prefs.get_connect_id(),
                                            ip=self.ip_info.ip4_address,
                                            port=prefs.get_port(),
                                            hostname=util.get_hostname(),
                                            api_version=int(config.RPC_API_VERSION),
                                            auth_port=self.auth_port,
                                            ipv6=self.ip_info.ip6_address)








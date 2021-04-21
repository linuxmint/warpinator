#!/usr/bin/python3

import logging
import threading
import socket
from concurrent import futures

import grpc
import warp_pb2_grpc
import warp_pb2

import auth

class RegRequest():
    def __init__(self, ident, hostname, ips, port, auth_port, api_version):
        self.api_version = api_version
        self.ident = ident
        self.hostname = hostname
        self.ips = ips
        self.port = port

        #v1 only
        self.request_loop = None

        #v2 only
        self.auth_port = auth_port
        self.locked_cert = None
        self.retry_keepalive = threading.Event()

    def cancel(self):
        if self.api_version == "1":
            self.request_loop.cancel()
        else:
            self.retry_keepalive.set()

class Registrar():
    def __init__(self, ips, port, auth_port):
        self.reg_server_v1 = None
        self.reg_server_v2 = None
        self.active_registrations = {}
        self.reg_lock = threading.Lock()

        self.ips = ips
        self.port = port
        self.auth_port = auth_port

        self.start_registration_servers()

    def start_registration_servers(self):
        if self.reg_server_v1 != None:
            self.reg_server_v1.stop()

        if self.reg_server_v2 != None:
            self.reg_server_v2.stop(grace=2).wait()
            self.reg_server_v2 = None

        logging.debug("Starting v1 registration server (%s) with port %d" % (self.ips, self.port))
        self.reg_server_v1 = RegistrationServer_v1(self.ips, self.port)
        logging.debug("Starting v2 registration server (%s) with auth port %d" % (self.ips, self.auth_port))
        self.reg_server_v2 = RegistrationServer_v2(self.ips, self.auth_port)

    def shutdown_registration_servers(self):
        with self.reg_lock:
            for key in self.active_registrations.keys():
                self.active_registrations[key].cancel()
            self.active_registrations = {}

        if self.reg_server_v1 != None:
            logging.debug("Stopping v1 registration server.")
            self.reg_server_v1.stop()
            self.reg_server_v1 = None

        if self.reg_server_v2:
            logging.debug("Stopping v2 registration server.")
            self.reg_server_v2.stop()
            self.reg_server_v2 = None

    def register(self, ident, hostname, ips, port, auth_port, api_version):
        details = RegRequest(ident, hostname, ips, port, auth_port, api_version)

        with self.reg_lock:
            self.active_registrations[ident] = details

        ret = False

        if api_version == "1":
            ret = register_v1(details)
        elif api_version == "2":
            ret = register_v2(details)

        del self.active_registrations[ident]

        return ret

    def cancel_registration(self, ident):
        with self.reg_lock:
            try:
                details = self.active_registrations[ident]
            except KeyError:
                return

            details.cancel()

            details = None
            del self.active_registrations[ident]

####################### api v1

def register_v1(details):
    # This will block if the remote's warp udp port is closed, until either the port is unblocked
    # or we tell the auth object to shutdown, in which case the request timer will cancel and return
    # here immediately (with None)

    logging.info("Authenticating with %s (%s:%d) - api version 1" % (details.hostname, details.ips, details.port))

    success = retrieve_remote_cert(details)

    if not success:
        logging.critical("Unable to authenticate with %s (%s:%d) - api version 1"
                             % (details.hostname, details.ips, details.port))
        return False

    return True

def retrieve_remote_cert(details):
    logging.debug("Auth: Starting a new RequestLoop for '%s' (%s:%d)" % (details.hostname, details.ips, details.port))

    details.request_loop = RequestLoop(details.ips, details.port)
    data = details.request_loop.request()

    if data == None:
        return False

    return auth.get_singleton().process_remote_cert(details.hostname,
                                                    details.ips,
                                                    data)

REQUEST = b"REQUEST"

#v1 client
class RequestLoop():
    def __init__(self, ips, port):
        self.ips = ips
        self.port = port

        self.timer = threading.Event()

    def request(self):
        while not self.timer.is_set():
            logging.debug("Auth: Requesting cert from remote (%s:%d)" % (self.ips, self.port))
            try_count = 0

            while try_count < 3:
                try:
                    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    server_sock.settimeout(1.0)
                    server_sock.sendto(REQUEST, (self.ips.ip4, self.port))

                    reply, addr = server_sock.recvfrom(2000)

                    if self.timer.is_set():
                        return None

                    if addr == (self.ips.ip4, self.port):
                        return reply
                except socket.timeout:
                    try_count += 1
                    continue
                except socket.error as e:
                    logging.critical("Something wrong with cert request (%s:%s): " % (self.ips, self.port, e))
                    break

            logging.debug("Auth: Cert request failed from remote (%s:%d), waiting 30s to try again. (Is their udp port blocked?"
                              % (self.ip, self.port))
            self.timer.wait(30)

        logging.debug("Auth: RequestLoop canceled (event set) for (%s:%s)" % (self.ips, self.port))
        return None

    def cancel(self):
        self.timer.set()

# v1 server
class RegistrationServer_v1():
    def __init__(self, ips, port):
        self.exit = False
        self.ips = ips
        self.port = port

        self.thread = threading.Thread(target=self.serve_cert_thread)
        self.thread.start()

    def serve_cert_thread(self):
        try:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # server_sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            server_sock.settimeout(1.0)
            server_sock.bind((self.ips.ip4, self.port))
        except socket.error as e:
            logging.critical("Could not create udp socket for cert requests: %s" % str(e))
            return

        while True:
            try:
                data, address = server_sock.recvfrom(2000)

                if data == REQUEST:
                    cert_data = auth.get_singleton().get_encoded_local_cert()
                    server_sock.sendto(cert_data, address)
            except socket.timeout as e:
                if self.exit:
                    server_sock.close()
                    break

    def stop(self):
        self.exit = True
        self.thread.join()


####################### api v2


def register_v2(details):
    # This will block if the remote's warp udp port is closed, until either the port is unblocked
    # or we tell the auth object to shutdown, in which case the request timer will cancel and return
    # here immediately (with None)

    logging.info("Authenticating with %s (%s:%d) - api version 2" % (details.hostname, details.ips, details.auth_port))

    success = False

    while not details.retry_keepalive.is_set():
        remote_thread = threading.Thread(target=register_with_remote_thread, args=(details,), name="remote-auth-thread-%s" % id)
        logging.debug("remote-registration-thread-%s-%s:%d-%s" % (details.hostname, details.ips, details.auth_port, details.ident))
        remote_thread.start()
        remote_thread.join()

        if details.locked_cert != None:
            success = auth.get_singleton().process_remote_cert(details.hostname,
                                                               details.ips,
                                                               details.locked_cert)

        if not success:
            logging.critical("Unable to authenticate with %s (%s:%d) - api version 2"
                                 % (details.hostname, details.ips, details.auth_port))
            details.retry_keepalive.wait(10)
        else:
            details.retry_keepalive.set()
    return True

def register_with_remote_thread(details):
    logging.debug("Remote: Attempting to authenticate %s (%s)" % (details.hostname, details.ips))

    with grpc.insecure_channel("%s:%d" % (details.ips.ip4, details.auth_port)) as channel:
        future = grpc.channel_ready_future(channel)

        try:
            future.result(timeout=5)
            stub = warp_pb2_grpc.WarpRegistrationStub(channel)

            ret = stub.RequestCertificate(warp_pb2.RegRequest(ip=details.ips.ip4, hostname=details.hostname),
                                          timeout=5)

            details.locked_cert = ret.locked_cert.encode("utf-8")
        except Exception as e:
            future.cancel()
            logging.critical("Problem with remote registration thread: %s (%s:%d) - api version 2: %s"
                     % (details.hostname, details.ips, details.auth_port, e))

class RegistrationServer_v2():
    def __init__(self, ips, auth_port):
        self.exit = False
        self.ips = ips
        self.auth_port = auth_port

        self.server = None
        self.server_thread_keepalive = threading.Event()

        self.thread = threading.Thread(target=self.serve_cert_thread)
        self.thread.start()

    def serve_cert_thread(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        warp_pb2_grpc.add_WarpRegistrationServicer_to_server(self, self.server)

        self.server.add_insecure_port('%s:%d' % (self.ips.ip4, self.auth_port))
        self.server.start()

        while not self.server_thread_keepalive.is_set():
            self.server_thread_keepalive.wait(10)

        self.server.stop(grace=2).wait()

    def stop(self):
        self.server_thread_keepalive.set()
        self.thread.join()

    def RequestCertificate(self, request, context):
        logging.debug("Registration Server RPC: RequestCertificate from %s '%s'" % (request.hostname, request.ip))

        return warp_pb2.RegResponse(locked_cert=auth.get_singleton().get_encoded_local_cert())








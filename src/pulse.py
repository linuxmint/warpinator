#!/usr/bin/python3

import threading
import time
import socket

from gi.repository import GLib, GObject

import util

debugging = False

def debug(*args):
    if debugging:
        print(args)

class Pulse(threading.Thread, GObject.Object):
    __gsignals__ = {
        'state-changed': (GObject.SignalFlags.RUN_LAST, None, (bool, object, str))
    }

    max_fails = 2 # normal operation
    initial_max_fails = 5 # startup operation

    def __init__(self, proxy, ip, port):
        super(Pulse, self).__init__()
        GObject.Object.__init__(self)
        self.online = False
        self.destroyed = False
        self.proxy = proxy
        self.proxy_ip = ip
        self.proxy_port = port

    def run(self):
        fail_count = 0
        initial_connect = True

        debug("client heartbeat: %s:%d" % (self.proxy_ip, self.proxy_port))

        while (True):
            new_online = False
            error = None

            if self.destroyed:
                break

            old_online = self.online

            try:
                with self.proxy.lock:
                    socket.setdefaulttimeout(5)
                    pong = self.proxy.ping()
                    socket.setdefaulttimeout(10)

                new_online = True

                initial_connect = False
                fail_count = 0

                debug("%s is alive" % (self.proxy_ip,))
            except Exception as e:
                error = e

                new_online = False
                fail_count += 1

                debug("%s is not responding: %s" % (self.proxy_ip, str(e)))

            if initial_connect and not new_online:
                if fail_count < self.initial_max_fails:
                    time.sleep(1)
                else:
                    initial_connect = False
                    self.emit_state_changed(error=error)
                continue

            if new_online != old_online:
                if not new_online and fail_count < self.max_fails:
                    time.sleep(5)
                    continue

                nick = None

                if new_online:
                    with self.proxy.lock:
                        nick = self.proxy.get_nick()

                self.online = new_online

                debug("Proxy connection to server changed: Online=%s" % self.online)
                self.emit_state_changed(error=error, nick=nick)

            time.sleep (10 if self.online else 4)

    @util._async
    def emit_state_changed(self, error=None, nick=None):
        self.emit("state-changed", self.online, error, nick)

    def destroy(self):
        self.destroyed = True



#!/usr/bin/python3
import random
import socket
import time
import xmlrpc.server
from zeroconf import ServiceInfo, Zeroconf
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject

import socket
import sys
import xmlrpc.client
from time import sleep
import getpass
import os

from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf


# Used as a decorator to run things in the background
def async(func):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread
    return wrapper

# Used as a decorator to run things in the main loop, from another thread
def idle(func):
    def wrapper(*args, **kwargs):
        GObject.idle_add(func, *args, **kwargs)
    return wrapper

def getmyip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ans = s.getsockname()[0]
    s.close()
    return ans

class WarpServer(object):
    def __init__(self):
        self.port = 8080

    def register_zeroconf(self):
        desc = {}
        self.info = ServiceInfo("_http._tcp.local.",
                                "warp.%s._http._tcp.local." % getmyip,
                                socket.inet_aton(getmyip()), self.port, 0, 0,
                                desc, "somehost.local.")
        self.zc = Zeroconf()
        self.zc.register_service(self.info)

    @async
    def serve_forever(self):
        self.register_zeroconf()
        addr = ("0.0.0.0", self.port)
        server = xmlrpc.server.SimpleXMLRPCServer(addr)
        print("Listening on", addr)
        server.register_function(self.get_name, "get_name")
        server.register_function(self.click, "click")
        server.serve_forever()

    def get_name(self):
        return "%s@%s" % (getpass.getuser(), socket.gethostname())

    def click(self, ip):
        os.system("notify-send 'clicked by %s'" % ip)
        return "OK"

    def close(self):
        self.zc.unregister_service(self.info)
        self.zc.close()

class WarpWindow():

    def __init__(self):

        self.window = Gtk.Window()
        self.window.connect("destroy", Gtk.main_quit)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.add(self.box)
        self.window.show_all()

        self.my_name = "%s@%s" % (getpass.getuser(), socket.gethostname())
        self.my_ip = getmyip()

        zeroconf = Zeroconf()
        print("\nSearching for others...\n")
        browser = ServiceBrowser(zeroconf, "_http._tcp.local.", handlers=[self.on_service_state_change])

    def on_service_state_change(self, zeroconf, service_type, name, state_change):
        # print("Service %s of type %s state changed: %s" % (name, service_type, state_change))
        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            # connect to the server
            if info and name.count("warp"):
                addrstr = "http://{}:{}".format(socket.inet_ntoa(info.address), info.port)
                proxy = xmlrpc.client.ServerProxy(addrstr)
                name = None
                while name is None:
                    time.sleep(1)
                    name = proxy.get_name()
                print(name, "on %s" % socket.inet_ntoa(info.address))
                self.add_button(name, proxy)

    @idle
    def add_button(self, name, proxy):
        button = Gtk.Button(name)
        button.show()
        button.connect("clicked", self.on_button_clicked, proxy)
        self.box.pack_start(button, False, False, 6)

    def on_button_clicked(self, widget, proxy):
        proxy.click("%s (%s)" % (self.my_name, self.my_ip))


if __name__ == "__main__":
    s = WarpServer()
    s.serve_forever()

    w = WarpWindow()
    Gtk.main()
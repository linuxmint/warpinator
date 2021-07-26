#!/usr/bin/python3

import threading
import logging
import netifaces
import ipaddress

import gi
from gi.repository import GLib, GObject

import prefs
import util

network_monitor = None

def get_network_monitor():
    global network_monitor

    if network_monitor == None:
        network_monitor = NetworkMonitor()

    return network_monitor

class NetworkMonitor(GObject.Object):
    __gsignals__ = {
        "ready": (GObject.SignalFlags.RUN_LAST, None, ()),
        "state-changed": (GObject.SignalFlags.RUN_LAST, None, (bool,)),
        "details-changed": (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self):
        GObject.Object.__init__(self)
        logging.debug("Starting network monitor")
        self.device = None
        self.online = True

        self.details_idle_id = 0

        self.reload_state()

        prefs.prefs_settings.connect("changed", self.on_prefs_changed)

        self.emit("ready")

    def ready(self):
        return True

    def on_prefs_changed(self, settings, key, data=None):
        new_main_port = prefs.get_port()
        new_auth_port = prefs.get_auth_port()
        new_iface = prefs.get_preferred_iface()

        emit = False

        if self.device != new_iface:
            self.reload_state()
            return

        if self.main_port != new_main_port:
            self.main_port = new_main_port
            emit = True
        if self.auth_port != new_auth_port:
            self.auth_port = new_auth_port
            emit = True

        if emit:
            self.emit_details_changed()

    def reload_state(self):
        new_device = self.get_preferred_or_default_iface()

        need_restart = False

        if new_device == None or new_device != self.device:
            self.device = new_device
            need_restart = True

        self.main_port = prefs.get_port()
        self.auth_port = prefs.get_auth_port()

        if need_restart:
            self.emit_state_changed()
            logging.debug("Current network changed (%s), connectivity: %s" % (prefs.get_preferred_iface(), str(self.online)))

    def stop(self):
        logging.debug("Stopping network monitor")

    def get_ips(self):
        return util.IPAddresses(self.get_ipv4(), self.get_ipv6())

    def get_ipv4(self):
        if self.device != None:
            interface_addresses = netifaces.interfaces()
            if not self.device in netifaces.interfaces():
                return None
            interface_addresses = netifaces.ifaddresses(self.device)
            if not netifaces.AF_INET in interface_addresses:
                return None
            return interface_addresses[netifaces.AF_INET][0]['addr']

        return "0.0.0.0"

    def get_ipv6(self):
        # We don't actually support ipv6 currently.
        return None

        if self.device != None:
            interface_addresses = netifaces.interfaces()
            if not self.device in netifaces.interfaces():
                return None
            interface_addresses = netifaces.ifaddresses(self.device)
            if not netifaces.AF_INET6 in interface_addresses:
                return None
            return interface_addresses[netifaces.AF_INET6][0]['addr']

        return None

    def get_preferred_or_default_iface(self):
        iface = prefs.get_preferred_iface()
        def_iface = self.get_default_interface()

        if iface == "auto" or iface == "":
            logging.debug("Automatic interface selection: %s" % def_iface)
            return def_iface

        if iface != "auto":
            for dev in self.get_devices():
                if dev == iface:
                    return iface

        logging.warning("Preferred interface (%s) not available.")
        return None

    def get_current_iface(self):
        return self.device

    def get_default_interface(self):
        return self.get_devices()[0]

    def get_devices(self):
        devices = []

        for device in netifaces.interfaces():
            if device == "lo0":
                continue
            addrs = netifaces.ifaddresses(device)
            if netifaces.AF_LINK not in addrs:
                continue
            if netifaces.AF_INET in addrs or netifaces.AF_INET6 in addrs:
                devices.append(device)

        return devices

    def same_subnet(self, other_ips):
        net = netifaces.ifaddresses(self.device)

        addresses = net[netifaces.AF_INET]
        for address in addresses:
            if address["addr"] == self.get_ipv4():
                iface = ipaddress.IPv4Interface("%s/%s" % (address["addr"], address["netmask"]))

        my_net = iface.network

        if my_net == None:
            # We're more likely to have failed here than to have found something on a different subnet.
            return True

        if my_net.netmask.exploded == "255.255.255.255":
            logging.warning("Discovery: netmask is 255.255.255.255 - are you on a vpn?")
            return False

        for addr in list(my_net.hosts()):
            if other_ips.ip4 == addr.exploded:
                return True

        return False

    @util._idle
    def emit_state_changed(self):
        logging.debug("Network state changed: online = %s" % str(self.online))
        self.emit("state-changed", self.online)

    def emit_details_changed(self):
        def cb(data=None):
            if self.device != None:
                iface = self.device
            else:
                iface = "none"

            logging.debug("Network details changed: iface: %s, mp: %d, ap: %s" % (iface, self.main_port, self.auth_port))
            self.emit("details-changed")

        if self.details_idle_id > 0:
            GLib.source_remove(self.details_idle_id)

        self.details_idle_id = GLib.timeout_add(50, cb)


#!/usr/bin/python3

import threading
import logging
import netifaces
import ipaddress
import socket

import gi
from gi.repository import GLib, Gio, GObject

import prefs
import util

network_monitor = None

def get_network_monitor():
    global network_monitor

    if network_monitor is None:
        network_monitor = NetworkMonitor()

    return network_monitor

class NetworkMonitor(GObject.Object):
    __gsignals__ = {
        "state-changed": (GObject.SignalFlags.RUN_LAST, None, (bool,))
    }

    def __init__(self):
        GObject.Object.__init__(self)
        self.online = False

        self.current_ip = None
        self.current_iface_setting = None
        self.current_ip_info = None

        self.timer_id = 0

        prefs.prefs_settings.connect("changed", self.on_prefs_changed)

    def on_prefs_changed(self, settings, key, data=None):
        if key not in ("preferred-network-iface",
                       "port",
                       "reg-port"):
            return

        self.stop()
        self.start()

    def start(self):
        logging.debug("Starting network monitor")

        self._update_online()
        self.timer_id = GLib.timeout_add_seconds(4, self._check_status)

    def stop(self):
        logging.debug("Stopping network monitor")
        if self.timer_id > 0:
            GLib.source_remove(self.timer_id)
            self.timer_id = 0

    def get_current_ip_info(self):
        return self.current_ip_info

    def _check_status(self, data=None):
        self._update_online()

        return GLib.SOURCE_CONTINUE

    def _update_online(self):
        new_iface_setting = prefs.get_preferred_iface()
        new_ip_info = None
        new_online = False

        available = self.get_valid_interface_infos()

        if new_iface_setting == "auto" and len(available) > 0:
            new_ip_info = self.get_default_interface_info()
            new_online = True
        for info in available:
            if info.iface == new_iface_setting:
                new_ip_info = info
                new_online = True

        if new_ip_info is None:
            new_ip_info = util.InterfaceInfo({ "addr": "0.0.0.0" }, { "addr": "[::]" }, new_iface_setting)

        if new_online != self.online or self.current_ip_info != new_ip_info or self.current_iface_setting != new_iface_setting:
            self.current_ip_info = new_ip_info
            self.online = new_online
            self.current_iface_setting = new_iface_setting
            self.emit_state_changed()

    def get_valid_interface_infos(self):
        valid = []
        for iname in netifaces.interfaces():
            if iname == "lo":
                continue

            iface = netifaces.ifaddresses(iname)

            try:
                ip4 = iface[netifaces.AF_INET][0]
            except KeyError:
                ip4 = None
            try:
                ip6 = iface[netifaces.AF_INET6][0]
            except KeyError:
                ip6 = None

            if ip4 is not None or ip6 is not None:
                info = util.InterfaceInfo(ip4, ip6, iname)
                valid.append(info)

        return valid

    def get_default_interface_info(self):
        ip4 = self.get_default_ip4()
        ip6 = self.get_default_ip6()
        fallback_info = None

        for info in self.get_valid_interface_infos():
            if fallback_info is None:
                fallback_info = info
            try:
                if ip4 == info.ip4["addr"]:
                    return info
            except:
                pass
            try:
                if ip6 == info.ip6["addr"]:
                    return info
            except:
                pass

        return fallback_info

    def get_default_ip(self, ip_version):
        with socket.socket(ip_version, socket.SOCK_DGRAM) as s:
            if ip_version == socket.AF_INET:
                try:
                    s.connect(("8.8.8.8", 80))
                except OSError as e:
                    # print("Unable to retrieve IP address: %s" % str(e))
                    return "0.0.0.0"
            else:
                try:
                    s.connect(("2001:4860:4860::8888", 80))
                except OSError as e:
                    # print("Unable to retrieve IP address: %s" % str(e))
                    return "[::]"
            ans = s.getsockname()[0]
            return ans

    def get_default_ip4(self):
        return self.get_default_ip(socket.AF_INET)

    def get_default_ip6(self):
        return self.get_default_ip(socket.AF_INET6)

    def emit_state_changed(self):
        logging.debug("Network state changed: online = %s" % str(self.online))
        self.emit("state-changed", self.online)

    # TODO: Do this with libnm
    def same_subnet(self, other_ip_info):
        if self.current_ip_info.ip4_address is not None and other_ip_info.ip4_address is not None:
            iface = ipaddress.IPv4Interface("%s/%s" % (self.current_ip_info.ip4_address,
                                                    self.current_ip_info.ip4["netmask"]))

            my_net = iface.network

            if my_net is None:
                # We're more likely to have failed here than to have found something on a different subnet.
                return True

            if my_net.netmask.exploded == "255.255.255.255":
                logging.warning("Discovery: netmask is 255.255.255.255 - are you on a vpn?")
                return False

            for addr in list(my_net.hosts()):
                if other_ip_info.ip4_address == addr.exploded:
                    return True

            return False
        if self.current_ip_info.ip6_address is not None and other_ip_info.ip6_address is not None:
            return True # TODO: Verify that this is actually true
        logging.debug("No IP address found: %s" % (self))
        return False
